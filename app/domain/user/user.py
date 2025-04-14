# backend/domain/user/user.py
import json
import mimetypes
from typing import List
from urllib.parse import quote
from fastapi import (
    Body,
    File,
    Form,
    HTTPException,
    APIRouter,
    Depends,
    Request,
    UploadFile,
)
from app.utils import verify_access_token, Logger
from app.utils.s3_client import s3_client
from app.config.connection import S3_BUCKET_NAME, S3_REGION, get_session

from .request import (
    MyInfoChangeWithoutTagsRequest,
    MyTagsChangeRequest,
    MyGroupsChangeRequest,
    SearchGetMembersRequest,
)

logger = Logger(__file__)
router = APIRouter()
ACCESS_TOKEN = "access_token"


@router.get("/my/info")
async def my_info(
    request: Request,
    session=Depends(get_session),
):
    logger.info("my_info")
    token = request.cookies.get(ACCESS_TOKEN)

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        RETURN properties(u) as user
        """
        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(status_code=400, detail="User not found")
        else:
            user_data = record["user"]
            return user_data

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/my/info/change")
async def my_info_change(
    request: Request,
    # user_info: MyInfoChangeRequest,
    my_memo: str = Form("", description="Memo for the user"),
    nickname: str = Form(..., description="User's nickname"),
    username: str = Form(..., description="User's full name"),
    tags: List[str] = Form([""], description="User's tags"),
    profile_image: UploadFile = File("", description="profile imgurl"),
    remove_profile_image: bool = Form(False, description="Remove profile image"),
    session=Depends(get_session),
):
    logger.info("my_info_change")
    token = request.cookies.get(ACCESS_TOKEN)

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]
    try:
        update_data = {
            "my_memo": my_memo,
            "nickname": nickname,
            "username": username,
            "tags": json.loads(tags[0]),
        }
        if remove_profile_image:
            update_data["profile_image_url"] = None
            s3_key = f"{user_node_id}/profile_image"
            try:
                s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            except Exception as e:
                logger.error(f"Error deleting S3 object: {e}")
                raise HTTPException(
                    status_code=500, detail="Failed to delete profile image"
                ) from e

        if profile_image:
            s3_key = f"{user_node_id}/profile_image"
            mime_type, _ = mimetypes.guess_type(profile_image.filename)
            extra_args = {
                "ContentType": mime_type or "application/octet-stream",
                "ACL": "public-read",
            }

            try:
                s3_client.upload_fileobj(
                    profile_image.file,
                    S3_BUCKET_NAME,
                    s3_key,
                    ExtraArgs=extra_args,
                )
            except s3_client.exceptions.ClientError as e:
                logger.error(f"Failed to upload {profile_image.file} to S3: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload {profile_image.file} to S3",
                ) from e
            update_data["profile_image_url"] = (
                f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{quote(s3_key)}"
            )

        query = """
        MATCH (u:User {node_id: $user_node_id})
        SET u += $update_data
        RETURN u
        """
        result = session.run(query, user_node_id=user_node_id, update_data=update_data)
        record = result.single()

        if not record:
            raise ValueError("User not found")
        else:
            updated_user = record["u"]
            return updated_user
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/my/info/change-without-tags")
async def my_info_change_without_tags(
    request: Request,
    user_info: MyInfoChangeWithoutTagsRequest,
    session=Depends(get_session),
):
    logger.info("my_info_change_without_tags")
    token = request.cookies.get(ACCESS_TOKEN)

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        SET u.my_memo = '{user_info.my_memo}',
            u.nickname = '{user_info.nickname}',
            u.username = '{user_info.username}'
            u.profile_image_url = '{user_info.profile_image_url}'
        RETURN u
        """
        result = session.run(query)

        record = result.single()

        if not record:
            raise HTTPException(
                status_code=400, detail="User not found or failed to update"
            )
        else:
            updated_user = record["u"]
            return updated_user

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/my/tags/change")
async def my_tags_change(
    request: Request,
    user_tags_info: MyTagsChangeRequest,
    session=Depends(get_session),
):
    logger.info("my_tags_change")
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        SET u.tags = {user_tags_info.tags}
        RETURN u
        """
        result = session.run(query)

        record = result.single()

        if not record:
            raise HTTPException(
                status_code=400, detail="User not found or failed to update"
            )
        else:
            updated_user = record["u"]
            return updated_user

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/my/groups/change")
async def my_groups_change(
    request: Request,
    user_groups_info: MyGroupsChangeRequest,
    session=Depends(get_session),
):
    logger.info("my_tags_change")
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        SET u.groups = '{user_groups_info.groups}'
        RETURN u
        """
        result = session.run(query)

        record = result.single()

        if not record:
            raise HTTPException(
                status_code=400, detail="User not found or failed to update"
            )
        else:
            updated_user = record["u"]
            return updated_user

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search/get-members")
async def search_get_memgers(
    request: Request,
    session=Depends(get_session),
    search: SearchGetMembersRequest = Body(...),
):
    logger.info("get_members")
    token = request.cookies.get(ACCESS_TOKEN)

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]

    if not user_node_id:
        raise HTTPException(status_code=401, detail="Invalid access token")

    try:
        query = f"""
        OPTIONAL MATCH (n:User)
        WHERE 
        (toLower(n.nickname) CONTAINS '{search.query}' OR 
        toLower(n.username) CONTAINS '{search.query}')
        AND n.node_id <> '{user_node_id}'
        RETURN 
        n.nickname AS nickname,
        n.username AS username,
        n.profile_image_url AS profile_image_url,
        n.node_id AS node_id
        ORDER BY n.username
        """
        print(query)
        result = session.run(query)
        record = result.data()

        if not record:
            raise HTTPException(status_code=400, detail="error with query")
        else:
            print(record)
            return record

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
