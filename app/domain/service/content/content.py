# backend/domain/service/content/content.py
import asyncio
import mimetypes
from urllib.parse import quote, unquote
from typing import List
from datetime import datetime, timezone
from fastapi import (
    File,
    Form,
    HTTPException,
    APIRouter,
    Depends,
    Body,
    Request,
    UploadFile,
)
from botocore.exceptions import (
    ConnectTimeoutError,
    ReadTimeoutError,
    EndpointConnectionError,
)
from app.utils.s3_client import s3_client
from app.config.connection import (
    S3_REGION,
    S3_BUCKET_NAME,
)
from app.utils import verify_access_token, Logger
from app.config.connection import get_session
from .request import (
    GetStickersRequest,
    DeleteStickerRequest,
    GetPostsRequest,
    ModifyMyPostRequest,
    DeleteMyPostRequest,
    SendCastRequest,
    GetNeighborsWithStickerRequest,
    ReadStickerRequest,
    ReplyCastRequest,
)
from .response import (
    CreateStickerResponse,
    GetStickersResponse,
    GetMyStickersResponse,
    DeleteStickerResponse,
    CreatePostResponse,
    GetPostsResponse,
    DeleteMyPostResponse,
    SendCastResponse,
    GetContentsResponse,
    GetNewContentsResponse,
    GetNeighborsWithStickerResponse,
    ReplyCastResponse,
)

logger = Logger(__file__)
router = APIRouter()
ACCESS_TOKEN = "access_token"


@router.post("/sticker/create")
async def create_sticker(
    request: Request,
    content: str = Form(""),
    images: List[UploadFile] = File([]),
    session=Depends(get_session),
):
    uploaded_image_urls = []
    logger.info("create_sticker")
    token = request.cookies.get(ACCESS_TOKEN)
    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")
    user_node_id = verify_access_token(token)["user_node_id"]
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        for index, image in enumerate(images):
            s3_key = f"{user_node_id}/sticker/{datetimenow}/{index}_{image.filename}"
            encoded_s3_key = quote(s3_key)
            image_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{encoded_s3_key}"

            mime_type, _ = mimetypes.guess_type(image.filename)
            extra_args = {"ContentType": mime_type, "ACL": "public-read"}
            try:
                s3_client.upload_fileobj(
                    image.file,
                    S3_BUCKET_NAME,
                    s3_key,
                    ExtraArgs=extra_args,
                )
                uploaded_image_urls.append(image_url)
            except s3_client.exceptions.ClientError as e:
                logger.error(f"Failed to upload {image.filename} to S3: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to upload {image.filename} to S3"
                ) from e

        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        CREATE (s:Sticker {{
                content : '{content}',
                image_url : {uploaded_image_urls},
                created_at : '{datetimenow}',
                deleted_at : '',
                node_id : randomUUID()
            }})
        CREATE (s)-[creator:creator_of_sticker {{edge_id : randomUUID()}}]->(u)
        RETURN creator
        """
        result = session.run(query)
        record = result.single()
        logger.info(f"""create_sticker success {record}""")

        if not record:
            raise HTTPException(status_code=404, detail=f"no such user {user_node_id}")

        return CreateStickerResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload fails: {str(e)}")

    finally:
        session.close()


@router.post("/sticker/get-members", response_model=List[GetStickersResponse])
async def get_stickers(
    request: Request,
    session=Depends(get_session),
    get_sticker_request: GetStickersRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        OPTIONAL MATCH (me: User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (friend:User {{node_id: '{get_sticker_request.user_node_id}'}})
        OPTIONAL MATCH (friend)<-[:creator_of_sticker]-(sticker:Sticker)
        WHERE sticker.deleted_at = ""
        WITH friend, me, collect(sticker) AS stickers
        RETURN 
        CASE 
            WHEN me IS NULL THEN "no such node {user_node_id}"
            WHEN friend IS NULL THEN "no such node {get_sticker_request.user_node_id}"
            WHEN EXISTS((me)-[:block]-(friend)) THEN "block exists"
            WHEN EXISTS((me)-[:mute]->(friend)) THEN "mute exists"
            ELSE "get stickers"
        END AS message, stickers
        """

        result = session.run(query)
        record = result.single()
        logger.info(f"""get_stickers success {record}""")

        if record["message"] != "get stickers":
            raise HTTPException(status_code=404, detail=record["message"])

        return [
            GetStickersResponse.from_data(dict(sticker))
            for sticker in record["stickers"]
        ]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/sticker/get-my-contents", response_model=List[GetMyStickersResponse])
async def get_my_stickers(request: Request, session=Depends(get_session)):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (me: User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (me)<-[:creator_of_sticker]-(sticker:Sticker)
        WHERE sticker.deleted_at = "" 
        RETURN collect(sticker) AS stickers
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(status_code=404, detail=f"no such user {user_node_id}")

        return [
            GetMyStickersResponse.from_data(dict(sticker))
            for sticker in record["stickers"]
        ]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.put("/sticker/read")
async def put_receiver_of_sticker_as_read(
    request: Request,
    session=Depends(get_session),
    read_sticker_request: ReadStickerRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    try:
        query = f"""
        MATCH (me:User {{node_id:'{user_node_id}'}})<-[receiver_of_sticker_edge:receiver_of_sticker]-(sticker:Sticker {{node_id:'{read_sticker_request.sticker_id}'}})
        SET receiver_of_sticker_edge.read = true
        RETURN receiver_of_sticker_edge
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=500,
                detail=f"""invalid receiver_of_sticker_edge between {user_node_id},{read_sticker_request.sticker_id}""",
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/sticker/delete", response_model=DeleteStickerResponse)
async def delete_sticker(
    request: Request,
    session=Depends(get_session),
    delete_sticker_request: DeleteStickerRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        if len(delete_sticker_request.sticker_image_urls) != 0:
            for image_url in delete_sticker_request.sticker_image_urls:
                file_name = "/".join(image_url.split("/")[3:])
                file_name = unquote(file_name)
                try:
                    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=file_name)
                except ConnectTimeoutError:
                    logger.error("스티커 삭제 S3 연결 시간 초과 - 재시도 필요")
                except ReadTimeoutError:
                    logger.error("스티커 삭제 S3 응답 대기 시간 초과 - 재시도 필요")
                except EndpointConnectionError:
                    logger.error("스티커 삭제 S3 엔드포인트 연결 실패 - URL 확인 필요")
        query = f"""
        OPTIONAL MATCH (me:User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (sticker:Sticker {{node_id: '{delete_sticker_request.sticker_node_id}'}})
        OPTIONAL MATCH (sticker)-[r:creator_of_sticker]->(me)
        WITH me, sticker, r
        CALL apoc.do.case(
        [
            me IS NULL, 'RETURN "User does not exist" AS message',
            sticker IS NULL, 'RETURN "Sticker does not exist" AS message',
            r IS NULL, 'RETURN "Relationship does not exist" AS message'
        ],
        'SET sticker.deleted_at = "{datetimenow}"  RETURN "Sticker and relationship deleted" AS message',
        {{sticker: sticker}}
        ) YIELD value
        RETURN value.message AS message
        """

        result = session.run(query)
        record = result.single()

        if record["message"] != "Sticker and relationship deleted":
            logger.error(f"delete_sticker error: {record['message']}")
            raise HTTPException(status_code=500, detail=record["message"])
        return DeleteStickerResponse(message=record["message"])

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


async def delete_old_stickers():
    session = get_session()
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        query = f"""
        MATCH (s:Sticker)
        WHERE datetime(s.created_at) <= datetime() - duration({{hours: 24}})
        SET s.deleted_at = '{datetimenow}'
        RETURN s
        """

        result = session.run(query)
        record = result.single()

    except Exception as e:
        raise e
    finally:
        session.close()


@router.post("/post/create", response_model=CreatePostResponse)
async def create_post(
    request: Request,
    content: str = Form(...),
    images: List[UploadFile] = File([]),
    is_public: bool = True,
    title: str = Form(...),
    tags: List[str] = Form([""]),
    session=Depends(get_session),
):
    uploaded_image_urls = []
    logger.info("create_post")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        for index, image in enumerate(images):
            s3_key = f"{user_node_id}/post/{datetimenow}/{index}_{image.filename}"
            encoded_s3_key = quote(s3_key)
            image_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{encoded_s3_key}"

            mime_type, _ = mimetypes.guess_type(image.filename)
            extra_args = {"ContentType": mime_type, "ACL": "public-read"}
            try:
                s3_client.upload_fileobj(
                    image.file,
                    S3_BUCKET_NAME,
                    s3_key,
                    ExtraArgs=extra_args,
                )
                uploaded_image_urls.append(image_url)
            except s3_client.exceptions.ClientError as e:
                logger.error(f"Failed to upload {image.filename} to S3: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to upload {image.filename} to S3"
                ) from e

        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        CREATE (p:Post {{
                content : '{content}',
                image_url : {uploaded_image_urls},
                is_public : {is_public},
                title : '{title}',
                tags : {tags[0]},
                created_at : '{datetimenow}',
                node_id : randomUUID()
            }})
        CREATE (p)-[is_post:is_post {{edge_id : randomUUID()}}]->(u)
        RETURN is_post
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(status_code=404, detail=f"no such user {user_node_id}")

        return CreatePostResponse

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/post/get-contents", response_model=List[GetPostsResponse])
async def get_posts(
    request: Request,
    session=Depends(get_session),
    get_post_request: GetPostsRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        OPTIONAL MATCH (me: User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (friend:User {{node_id: '{get_post_request.user_node_id}'}})
        OPTIONAL MATCH (me)<-[b:block]-(friend)
        OPTIONAL MATCH (me)-[m:mute]->(friend)
        OPTIONAL MATCH (friend)<-[:is_post]-(post:Post {{is_public : true}})
        WITH friend, me, b, m, collect(post) AS posts
        RETURN 
        CASE 
            WHEN me IS NULL THEN "no such user {user_node_id}"
            WHEN friend IS NULL THEN "no such friend {get_post_request.user_node_id}"
            WHEN b IS NOT NULL THEN "is_blocked exists"
            WHEN m IS NOT NULL THEN "mute exists"
            ELSE "get posts"
        END AS message, 
        posts
        """

        result = session.run(query)
        record = result.single()

        if record["message"] != "get posts":
            raise HTTPException(status_code=404, detail=record["message"])

        return [GetPostsResponse.from_data(dict(post)) for post in record["posts"]]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/post/get-my-contents", response_model=List[GetPostsResponse])
async def get_my_posts(
    request: Request,
    session=Depends(get_session),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (me: User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (me)<-[:is_post]-(post:Post)
        RETURN collect(post) AS posts
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=404, detail=f"invalid user_node_id {user_node_id}"
            )

        return [GetPostsResponse.from_data(dict(post)) for post in record["posts"]]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/post/modify-my-content", response_model=GetPostsResponse)
async def modify_my_post(
    request: Request,
    session=Depends(get_session),
    modify_my_post_request: ModifyMyPostRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    post_node_id = modify_my_post_request.post_node_id
    new_content = modify_my_post_request.new_content
    new_image_url = modify_my_post_request.new_image_url
    new_is_public = modify_my_post_request.new_is_public
    new_title = modify_my_post_request.new_title
    new_tag = modify_my_post_request.new_tag

    try:
        query = f"""
        OPTIONAL MATCH (me:User {{node_id : '{user_node_id}'}})
        OPTIONAL MATCH (p:Post {{node_id : '{post_node_id}'}})
        OPTIONAL MATCH (me)<-[is_post:is_post]-(p)
        WITH me,p,is_post

        CALL apoc.do.case(
        [
            me is NULL, 'RETURN "no such user" As result',
            p IS NULL, 'RETURN "no such post" AS result',
            is_post IS NULL, 'RETURN "the user is not owner of the post" AS result'
        ],
        'SET 
            p.content = $new_content,
            p.image_url = $new_image_url,
            p.is_public = $new_is_public,
            p.title = $new_title,
            p.tag = $new_tag
        RETURN p AS result',
        {{
            p:p,
            new_content: '{new_content}',
            new_image_url: {new_image_url}, 
            new_is_public: {new_is_public}, 
            new_title: '{new_title}', 
            new_tag: {new_tag}
        }}
        ) YIELD value
        RETURN value.result AS result
        """

        result = session.run(query)
        record = result.single()

        if type(record["result"]) == str:
            raise HTTPException(status_code=404, detail=record["result"])

        return GetPostsResponse.from_data(dict(record["result"]))

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/post/delete-my-content", response_model=DeleteMyPostResponse)
async def delete_my_post(
    request: Request,
    session=Depends(get_session),
    delete_my_post_request: DeleteMyPostRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        if len(delete_my_post_request.post_image_urls) != 0:
            for image_url in delete_my_post_request.post_image_urls:
                file_name = "/".join(image_url.split("/")[3:])
                file_name = unquote(file_name)
                try:
                    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=file_name)
                except ConnectTimeoutError:
                    logger.error("게시물 삭제 S3 연결 시간 초과 - 재시도 필요")
                except ReadTimeoutError:
                    logger.error("게시물 삭제 S3 응답 대기 시간 초과 - 재시도 필요")
                except EndpointConnectionError:
                    logger.error("게시물 삭제 S3 엔드포인트 연결 실패 - URL 확인 필요")
        query = f"""
        OPTIONAL MATCH (me:User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (p:Post {{node_id: '{delete_my_post_request.post_node_id}'}})
        OPTIONAL MATCH (p)-[is_post:is_post]->(me)
        WITH me, p, is_post
        CALL apoc.do.case(
        [
            me IS NULL, 'RETURN "User does not exist" AS message',
            p IS NULL, 'RETURN "Sticker does not exist" AS message',
            is_post IS NULL, 'RETURN "Relationship does not exist" AS message'
        ],
        'DETACH DELETE p RETURN "Sticker and relationship deleted" AS message',
        {{p: p}}
        ) YIELD value
        RETURN value.message AS message
        """

        result = session.run(query)
        record = result.single()

        if record["message"] != "Sticker and relationship deleted":
            raise HTTPException(status_code=500, detail=record["message"])

        return DeleteStickerResponse(message=record["message"])
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/cast/create", response_model=SendCastResponse)
async def create_cast(
    request: Request,
    session=Depends(get_session),
    send_cast_request: SendCastRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        query = f"""
        MATCH (me:User {{node_id: '{user_node_id}'}})
        CREATE (cast_node:Cast {{
            node_id:randomUUID(),
            message:'{send_cast_request.message}',
            reply_visible: True,
            created_at:'{datetimenow}',
            duration:{send_cast_request.duration},
            deleted_at:''}})
        CREATE (me)<-[:creator_of_cast {{edge_id:randomUUID()}}]-(cast_node)
        WITH cast_node,me
        UNWIND {send_cast_request.friends} AS receivers_node_id
        MATCH (receiver:User {{node_id: receivers_node_id}})
        WHERE NOT (receiver)-[:mute]->(me) AND NOT (receiver)-[:block]-(me)
        CREATE (receiver)<-[:receiver_of_cast {{open:true, new:true,edge_id:randomUUID()}}]-(cast_node)
        RETURN cast_node.node_id AS cast_node, collect(receiver.node_id) AS receivers
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"no such user {user_node_id} or no any valid friends",
            )

        # dispatcher.dispatch(dispatcher.NEW_CAST_CREATED,record["cast_node"],record["receivers"])
        return SendCastResponse()

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/cast/reply", response_model=ReplyCastResponse)
async def put_receiver_of_cast_as_read(
    request: Request,
    session=Depends(get_session),
    reply_cast_request: ReplyCastRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    try:
        query = f"""
        MATCH (me:User {{node_id:'{user_node_id}'}})<-[receiver_of_cast:receiver_of_cast]-(case:Cast {{node_id:'{reply_cast_request.cast_id}'}})
        CREATE (me)-[is_reply:is_reply {{message: '{reply_cast_request.message}', edge_id:randomUUID()}}]->(case)
        RETURN is_reply
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=500,
                detail=f"""invalid receiver_of_sticker_edge between {user_node_id},{reply_cast_request.cast_id}""",
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


async def delete_old_casts():
    session = get_session()
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    print("datetimenow : ", datetimenow)

    try:
        query = f"""
        MATCH (cast_node:Cast)
        WHERE datetime(cast_node.created_at)+duration({{minutes:cast_node.duration}}) <= datetime()
        SET cast_node.deleted_at = '{datetimenow}'
        return cast_node
        """
        result = session.run(query)
        record = result.data()


    except Exception as e:
        raise e
    finally:
        session.close()


@router.get("/get-contents")
async def get_contents(
    request: Request,
    session=Depends(get_session),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (me:User {{node_id:'{user_node_id}'}})
        OPTIONAL MATCH (me)<-[r:receiver_of_cast]-(cast:Cast {{deleted_at:''}})-[:creator_of_cast]->(creator_of_cast:User)
            WHERE NOT (me)-[:block]-(creator_of_cast) 
            AND NOT (me)-[:mute]->(creator_of_cast)
        REMOVE r.new
        WITH me,collect({{cast:properties(cast),creator:creator_of_cast.node_id}}) as casts

        OPTIONAL MATCH (me)-[:is_roommate]->(roommate:User)<-[:creator_of_sticker]-(sticker:Sticker {{deleted_at:''}})
            WHERE NOT (me)<-[:receiver_of_sticker {{read: true}}]-(sticker)
            AND NOT (me)-[:block]-(roommate) 
            AND NOT (me)-[:mute]->(roommate)
        WITH me,casts,roommate,sticker
        FOREACH (s IN CASE WHEN sticker IS NOT NULL THEN [sticker] ELSE [] END |
            MERGE (me)<-[:receiver_of_sticker]-(s))
        WITH me,casts,collect(DISTINCT roommate.node_id) AS stickered_roommates
        
        OPTIONAL MATCH (me)-[:is_roommate]->(:User)-[:is_roommate]->(neighbor:User)<-[:creator_of_sticker]-(sticker:Sticker {{deleted_at: ''}})
            WHERE NOT (me)<-[:receiver_of_sticker {{read: true}}]-(sticker) 
            AND neighbor <> me 
            AND NOT (me)-[:is_roommate]->(neighbor)
            AND NOT (me)-[:block]-(neighbor) 
            AND NOT (me)-[:mute]->(neighbor)
        WITH me, casts,stickered_roommates, neighbor, sticker
        FOREACH (s IN CASE WHEN sticker IS NOT NULL THEN [sticker] ELSE [] END |
            MERGE (me)<-[:receiver_of_sticker]-(s))
        RETURN casts,stickered_roommates,collect(DISTINCT neighbor.node_id) AS stickered_neighbors
        """

        result = session.run(query)
        record = result.single()
        logger.info(record)

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"internal server Error",
            )

        # Todo. return with cast_creator node_id
        return GetContentsResponse.from_datas(
            record["casts"],
            record["stickered_roommates"],
            record["stickered_neighbors"],
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/get-new-contents")
async def get_new_contents(
    request: Request,
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    for _ in range(3):
        response = {"new_roommates": [], "stickers_from": [], "casts_received": []}
        session = get_session()
        try:
            query = f"""
            MATCH (me:User {{node_id: '{user_node_id}'}})
            OPTIONAL MATCH (me)<-[new_roommate_edge:is_roommate {{new:true}}]-(new_roommate:User)
            REMOVE new_roommate_edge.new
            WITH me,new_roommate
            OPTIONAL MATCH (new_roommate)-[:is_roommate]->(neighbor:User)
                WHERE neighbor <> me 
                AND NOT (new_roommate)-[:block]->(neighbor)
            WITH me, new_roommate, collect(properties(neighbor)) AS neighbors
            WITH me, collect({{new_roommate:properties(new_roommate),neighbors:neighbors}}) AS new_roommates

            OPTIONAL MATCH (me)<-[r:receiver_of_cast {{new:true}}]-(cast:Cast {{deleted_at:''}})-[:creator_of_cast]->(cast_creator:User)
                WHERE NOT (me)-[:mute]->(cast_creator)
                AND NOT (me)-[:block]-(cast_creator)
            REMOVE r.new
            WITH me,new_roommates,collect({{cast:properties(cast),cast_creator:cast_creator.node_id}}) AS casts_received
            
            OPTIONAL MATCH (me)-[:is_roommate]->(roommate:User)-[:creator_of_sticker]->(sticker:Sticker {{deleted_at:''}})
                WHERE not (me)-[:receiver_of_sticker]->(sticker)
                AND NOT (me)-[:mute]->(roommate)
                AND NOT (me)-[:block]-(roommate)
            FOREACH (s IN CASE WHEN sticker IS NOT NULL THEN [sticker] ELSE [] END |
            MERGE (me)<-[:receiver_of_sticker]-(s))
            return new_roommates,casts_received,collect(DISTINCT(roommate.node_id)) AS stickers_from
            """

            result = session.run(query)
            record = result.single()

            if not record:
                raise HTTPException(
                    status_code=404, detail=f"no such user {user_node_id}"
                )
            response = GetNewContentsResponse.from_datas(
                record["new_roommates"],
                record["casts_received"],
                record["stickers_from"],
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            session.close()

        if not response.is_empty():
            return response
        else:
            await asyncio.sleep(10)

    return response


@router.post("/get_neighbors_with_stickers")
async def get_neighbors_with_stickers(
    request: Request,
    session=Depends(get_session),
    get_neighbors_with_sticker_request: GetNeighborsWithStickerRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""        
        MATCH (me:User {{node_id:'{user_node_id}'}})-[:is_roommate]->(roommate:User {{node_id:'{get_neighbors_with_sticker_request.roommate_node_id}'}})
        OPTIONAL MATCH (roommate)-[:is_roommate]->(neighbor:User)
            WHERE neighbor <> me
            AND NOT (me)-[:block]-(neighbor)
        OPTIONAL MATCH (neighbor)<-[:creator_of_sticker]-(sticker:Sticker {{deleted_at:''}})
            WHERE NOT (me)<-[:receiver_of_sticker {{read: true}}]-(sticker) 
            AND NOT (me)-[:mute]->(neighbor)
        FOREACH (s IN CASE WHEN sticker IS NOT NULL THEN [sticker] ELSE [] END |
            MERGE (me)<-[:receiver_of_sticker]-(s))
        RETURN properties(neighbor) AS neighbor,collect(sticker.node_id) AS stickers
        """

        result = session.run(query)
        records = result.data()
        logger.info(records)

        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"invalid is_roommate {user_node_id},{get_neighbors_with_sticker_request.roommate_node_id}",
            )

        return [
            GetNeighborsWithStickerResponse.from_data(
                record["neighbor"], record["stickers"]
            )
            for record in records
        ]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
