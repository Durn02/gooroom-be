# backend/domain/service/friend/block/block.py
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from utils import verify_access_token, Logger
from config.connection import get_session
from .request import MuteFriendRequest, PopMutedRequest
from .response import MuteFriendResponse, GetMutedResponse, PopMutedResponse

router = APIRouter()
ACCESS_TOKEN = "access_token"

logger = Logger(__file__)


@router.post("/add_member", response_model=MuteFriendResponse)
async def mute_friend(
    request: Request,
    session=Depends(get_session),
    mute_friend_request: MuteFriendRequest = Body(...),
):
    logger.info("mute_friend")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
            MATCH (from_user:User {{node_id: '{user_node_id}'}}), (to_user:User {{node_id: '{mute_friend_request.user_node_id}'}})
            OPTIONAL MATCH (from_user)-[m:mute]->(to_user)

            WITH from_user, to_user, m

            CALL apoc.do.case(
            [
                from_user.node_id = to_user.node_id, 'RETURN "cannot mute myself" AS message',
                m IS NOT NULL, 'RETURN "already muted" AS message'
            ],
            'MERGE (from_user)-[:mute {{edge_id: randomUUID()}}]->(to_user) RETURN "muted successfully" AS message',
            {{from_user: from_user, to_user: to_user, m: m}}
            ) YIELD value
            RETURN value.message AS message
            """


        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(status_code=400, detail="Failed to mute")
        return MuteFriendResponse(message=record["message"])

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/get-members", response_model=List[GetMutedResponse])
async def get_muteed(
    request: Request,
    session=Depends(get_session),
):
    logger.info("get_muted")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})-[m:mute]->(muted_user:User)
        RETURN m.edge_id, muted_user
        """

        result = session.run(query)
        records = result.data()
        response = [
            GetMutedResponse.from_data(record["m.edge_id"], record["muted_user"])
            for record in records
        ]
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/pop-members")
async def pop_muted(
    request: Request,
    session=Depends(get_session),
    pop_muted_request: PopMutedRequest = Body(...),
):
    logger.info("pop_muted")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (from_user:User {{node_id: '{user_node_id}'}})-[m:mute {{edge_id: '{pop_muted_request.mute_edge_id}'}}]->(to_user:User)
        DELETE m
        RETURN m
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(status_code=400, detail="Failed to mute")
        else:
            return PopMutedResponse(
                message=f"'{pop_muted_request.mute_edge_id}' dropped"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
