# backend/domain/user/user.py
from fastapi import HTTPException, APIRouter, Depends, Request
from domain.user.request.my_info_change_request import MyInfoChangeRequest
from utils import verify_access_token, Logger
from config.connection import get_session

from .request import (
    MyInfoChangeWithoutTagsRequest,
    MyTagsChangeRequest,
)

ACCESS_TOKEN = "access_token"
router = APIRouter()
logger = Logger(__file__)

router = APIRouter()


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
        RETURN u
        """
        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(status_code=400, detail="User not found")
        else:
            user_data = record["u"]
            return user_data

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/my/info/change")
async def my_info_change(
    request: Request,
    user_info: MyInfoChangeRequest,
    session=Depends(get_session),
):
    logger.info("my_info_change")
    token = request.cookies.get(ACCESS_TOKEN)

    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})
        SET u.my_memo = '{user_info.my_memo}',
            u.nickname = '{user_info.nickname}',
            u.username = '{user_info.username}',
            u.tags = {user_info.tags}
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
    user_groups_info: MyTagsChangeRequest,
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
