# backend/domain/service/content/content.py
import asyncio
from typing import List
from datetime import datetime, timezone
from fastapi import HTTPException, APIRouter, Depends, Body, Request
from utils import verify_access_token, Logger
from config.connection import get_session
from .request import (
    CreateStickerRequest,
    GetStickersRequest,
    DeleteStickerRequest,
    CreatePostRequest,
    GetPostsRequest,
    ModifyMyPostRequest,
    DeleteMyPostRequest,
    SendCastRequest,
    GetNeighborsWithStickerRequest,
    ReadStickerRequest
)
from .response import (
    CreateStickerResponse,
    GetStickersResponse,
    DeleteStickerResponse,
    CreatePostResponse,
    GetPostsResponse,
    DeleteMyPostResponse,
    SendCastResponse,
    GetContentsResponse,
    GetNewContentsResponse,
    GetNeighborsWithStickerResponse
)

logger = Logger(__file__)
router = APIRouter()
ACCESS_TOKEN = "access_token"


@router.post("/sticker/create", response_model=CreateStickerResponse)
async def create_sticker(
    request: Request,
    session=Depends(get_session),
    create_sticker_request: CreateStickerRequest = Body(...),
):
    logger.info("create_sticker")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        CREATE (s:Sticker {{
                content : '{create_sticker_request.content}',
                image_url : {create_sticker_request.image_url},
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

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/sticker/get-contents", response_model=List[GetStickersResponse])
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
        OPTIONAL MATCH (friend)<-[:creator]-(sticker:Sticker)
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
            raise HTTPException(status_code=500, detail=f"""invalid receiver_of_sticker_edge between {user_node_id},{read_sticker_request.sticker_id}""")

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
        query = f"""
        OPTIONAL MATCH (me:User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (sticker:Sticker {{node_id: '{delete_sticker_request.sticker_node_id}'}})
        OPTIONAL MATCH (sticker)-[r:creator]->(me)
        WITH me, sticker, r
        CALL apoc.do.case(
        [
            me IS NULL, 'RETURN "User does not exist" AS message',
            sticker IS NULL, 'RETURN "Sticker does not exist" AS message',
            r IS NULL, 'RETURN "Relationship does not exist" AS message'
        ],
        'SET s.delete_at = "{datetimenow}"  RETURN "Sticker and relationship deleted" AS message',
        {{sticker: sticker}}
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


async def delete_old_stickers():
    session = get_session()
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        query = f"""
        MATCH (s:Sticker)
        WHERE datetime(s.created_at) <= datetime() - duration({{hours: 24}})
        SET s.delete_at = '{datetimenow}'
        RETURN s
        """

        result = session.run(query)
        record = result.single()
        logger.info(f"delete_old_stickers : {record}")

    except Exception as e:
        raise e
    finally:
        session.close()


@router.post("/post/create", response_model=CreatePostResponse)
async def create_post(
    request: Request,
    session=Depends(get_session),
    create_post_request: CreatePostRequest = Body(...),
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        CREATE (p:Post {{
                content : '{create_post_request.content}',
                image_url : {create_post_request.image_url},
                is_public : {create_post_request.is_public},
                title : '{create_post_request.title}',
                tag : {create_post_request.tag},
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


async def delete_old_casts():
    session = get_session()
    datetimenow = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    print("datetimenow : ", datetimenow)

    try:
        query = f"""
        MATCH (cast_node:Cast)
        WHERE datetime(cast_node.created_at)+duration({{hours:cast_node.duration}}) <= datetime()
        SET cast_node.deleted_at = '{datetimenow}'
        return cast_node
        """
        result = session.run(query)
        record = result.data()

        logger.info(f"delete_old_casts : {record}")

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
        WITH me,collect({{cast:properties(cast),creator:cast.node_id}}) as casts

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
        
        return GetContentsResponse.from_datas(record["casts"],record["stickered_roommates"],record["stickered_neighbors"])

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
        response = {
            "new_roommates": [],
            "stickers_from": [],
            "casts_received": []
        }
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

            OPTIONAL MATCH (me)<-[r:receiver_of_cast {{new:true}}]-(cast:Cast {{deleted_at:''}})<-[:creator_of_cast]-(cast_creator:User)
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
            response = GetNewContentsResponse.from_datas(record["new_roommates"],record["casts_received"],record["stickers_from"])

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
            GetNeighborsWithStickerResponse.from_data(record["neighbor"], record["stickers"])for record in records
        ]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()