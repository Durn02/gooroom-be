# backend/domain/service/friend/friend.py
from datetime import datetime, timedelta
import uuid
from fastapi import HTTPException, APIRouter, Depends, Body, Request
from utils import verify_access_token, Logger, dispatcher
from config.connection import get_session
from .request import (
    SendKnockRequest,
    RejectKnockRequest,
    AcceptKnockRequest,
    GetFriendRequest,
    DeleteFriendRequest,
    GetMemoRequest,
    ModifyMemoRequest,
    ModifyGroupRequest,
)
from .response import (
    GetKnocksResponse,
    SendKnockResponse,
    AcceptKnockResponse,
    GetFriendResponse,
    DeleteFriendResponse,
    GetMemoResponse,
    ModifyMemoResponse,
    RejectKnockResponse,
    ModifyGroupResponse,
)
import os
from dotenv import load_dotenv

ACCESS_TOKEN = "access_token"
router = APIRouter()
logger = Logger(__file__)
load_dotenv()


@router.post("/knock/send", response_model=SendKnockResponse)
async def send_knock(
    request: Request,
    session=Depends(get_session),
    send_knock_request: SendKnockRequest = Body(...),
):
    logger.info("send_knock")
    token = request.cookies.get(ACCESS_TOKEN)
    from_user_node_id = verify_access_token(token)["user_node_id"]
    to_user_node_id = send_knock_request.to_user_node_id
    knock_edge_id = str(uuid.uuid4())

    try:
        query = f"""
        MATCH (from_user:User {{node_id: '{from_user_node_id}'}})
        MATCH (to_user:User {{node_id: '{to_user_node_id}'}})
        WHERE from_user.node_id <> to_user.node_id
        OPTIONAL MATCH (from_user)-[r:is_roommate]->(to_user)
        WITH from_user, to_user, r
        WHERE r IS NULL
        OPTIONAL MATCH (from_user)-[k:knock]->(to_user)
        WITH from_user, to_user, k
        WHERE k IS NULL AND NOT (from_user)-[:block]-(to_user) AND NOT (to_user)-[:block]-(from_user)
        CREATE (from_user)-[nk:knock]->(to_user)
        SET nk.edge_id = '{knock_edge_id}'
        RETURN "knock created" AS message, nk.edge_id AS knock_edge_id
        """

        result = session.run(query)
        record = result.single()
        if not record:
            raise HTTPException(
                status_code=404,
                detail="Cannot create knock_edge",
            )

        return SendKnockResponse()

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/knock/get-members", response_model=GetKnocksResponse)
async def get_knocks(
    request: Request,
    session=Depends(get_session),
):
    logger.info("list_knock")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})<-[k:knock]-(from_user:User)
        RETURN k.edge_id AS knock_edge_id, from_user.nickname AS nickname
        """

        result = session.run(query)
        records = result.data()

        result_list = GetKnocksResponse(knocks=[])
        for record in records:
            edge_id = record["knock_edge_id"]
            nickname = record.get("nickname", "")
            result_list.append_knock(edge_id, nickname)

        return result_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/knock/reject")
async def reject_knock(
    request: Request,
    session=Depends(get_session),
    reject_knock_request: RejectKnockRequest = Body(...),
):
    logger.info("reject_knock")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (from_user:User)-[k:knock]->(to_user:User {{node_id: '{user_node_id}'}})
        WHERE k.edge_id = '{reject_knock_request.knock_id}'
        DELETE k
        RETURN "knock deleted successfully" AS message
        """
        result = session.run(query)
        record = result.single()
        if not record:
            raise HTTPException(status_code=400, detail="no such knock_edge")

        return RejectKnockResponse(message=record["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/knock/accept", response_model=AcceptKnockResponse)
async def accept_knock(
    request: Request,
    session=Depends(get_session),
    accept_knock_request: AcceptKnockRequest = Body(...),
):
    logger.info("accept_knock")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (to_user:User {{node_id: '{user_node_id}'}})<-[k1:knock {{edge_id:'{accept_knock_request.knock_id}'}}]-(from_user:User)
            WHERE NOT (to_user)-[:is_roommate]-(from_user)
        OPTIONAL MATCH (from_user)-[knock_edge:knock]-(to_user)
        CREATE (from_user)-[:is_roommate {{memo: '', edge_id: randomUUID(),group: ''}}]->(to_user)
        CREATE (to_user)-[:is_roommate {{memo: '', edge_id: randomUUID(),group: '',new:true}}]->(from_user)
        DELETE knock_edge
        WITH from_user,to_user
        OPTIONAL MATCH (from_user)-[:is_roommate]->(new_neighbor:User)
            WHERE new_neighbor <> to_user AND NOT (from_user)-[:block]-(new_neighbor)
        RETURN from_user AS new_roommate ,collect(new_neighbor) AS new_neighbors
        """

        result = session.run(query)
        record = result.single()
        if not record:
            raise HTTPException(
                status_code=400,
                detail="no such knock_edge or already other relations(another knock,is_roommate) exist",
            )

        return AcceptKnockResponse.from_data(
            record["new_roommate"], record["new_neighbors"]
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/knock/create_link")
async def create_knock_by_link(
    request: Request,
    session=Depends(get_session),
):
    logger.info("create_knock_by_link")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    link_code = str(uuid.uuid4())

    expiration_time = datetime.now() + timedelta(hours=24)
    link_info = link_code + " : " + expiration_time.replace(microsecond=0).isoformat()

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})<-[:is_info]-(p:PrivateData)
        WITH p
        WHERE p.link_count < 5
        SET p.link_count = p.link_count + 1, 
            p.link_info = '{link_info}'
        RETURN 'knock link created' AS message
        """

        result = session.run(query)
        record = result.single()
        if not record:
            raise HTTPException(status_code=400, detail="failed to create link")

        front_url = os.getenv("FRONT_URL")
        return f"{front_url}/knock/{link_code}"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/knock/accept_by_link/{knock_id}")
async def accept_knock_by_link(
    knock_id: str,
    request: Request,
    session=Depends(get_session),
):
    logger.info("accept_knock_by_link")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        datetimenow = datetime.now().replace(microsecond=0).isoformat()

        query = f"""
            MATCH (u:User)<-[:is_info]-(p:PrivateData)
            WHERE left(p.link_info, 36) = '{knock_id}'
            WITH p, u, right(p.link_info, 19) AS expiration_time_str
            WITH p, u, expiration_time_str, datetime(expiration_time_str) AS expiration_time
            WHERE expiration_time > datetime("{datetimenow}")
            MATCH (from_user:User {{node_id: u.node_id}}), (to_user:User {{node_id: '{user_node_id}'}})
            WHERE NOT (from_user)-[:is_roommate]-(to_user)
            AND NOT (from_user)-[:block]-(to_user)
            AND NOT (to_user)-[:block]-(from_user)
            CREATE (from_user)-[:is_roommate {{memo: '', edge_id: randomUUID(),group: ''}}]->(to_user)
            CREATE (to_user)-[:is_roommate {{memo: '', edge_id: randomUUID(),group: '',new:true}}]->(from_user)
            RETURN 'Knock accepted successfully' AS message, from_user.node_id AS link_creator
            """

        result = session.run(query)
        record = result.single()
        print(record)
        if not record:
            raise HTTPException(
                status_code=400, detail="Cannot create is_roommate relationship"
            )

        # dispatcher.dispatch(dispatcher.NEW_ROOMMATE_CREATED,record["link_creator"],user_node_id)
        return record["message"]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/get-members")
async def get_members(
    request: Request,
    session=Depends(get_session),
):
    logger.info("get_members")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    try:
        query = f"""
        MATCH (me:User {{node_id: '{user_node_id}'}})
            OPTIONAL MATCH (me)-[r1:is_roommate]->(r:User)
            REMOVE r1.new
            WITH me,r1,r
            OPTIONAL MATCH (r)-[:is_roommate]->(n:User)
                WHERE n<>me
            WITH me, r1,collect(n.node_id) as ns
            WITH collect({{roommate_edge:properties(r1),roommate:properties(endNode(r1)),neighbors:ns}}) as collected,collect(endNode(r1)) as roommates, me
            OPTIONAL MATCH (me)-[r1:is_roommate]->(r:User)
            OPTIONAL MATCH (r)-[:is_roommate]->(n:User)
            WHERE n<>me AND NOT (me)-[:block]->(n) AND NOT n in roommates
            RETURN me,collect(DISTINCT n) as pure_neighbors,collected as roommatesWithNeighbors    
        """
        result = session.run(query)
        record = result.data()

        if record[0]["roommatesWithNeighbors"][0] == {
            "neighbors": [],
            "roommate_edge": None,
            "roommate": None,
        }:
            record[0]["roommatesWithNeighbors"] = []
        return record

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/get-member", response_model=GetFriendResponse)
async def get_member(
    request: Request,
    session=Depends(get_session),
    get_friend_request: GetFriendRequest = Body(...),
):
    logger.info("get_member")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        OPTIONAL MATCH (friend:User {{node_id: '{get_friend_request.user_node_id}'}})
        OPTIONAL MATCH (me:User {{node_id: '{user_node_id}'}})
        OPTIONAL MATCH (friend)<-[b:block]->(me)
        OPTIONAL MATCH (me)-[r:is_roommate]->(friend)
        OPTIONAL MATCH (friend)<-[:is_sticker]-(sticker:Sticker) WHERE sticker.deleted_at = ""
        OPTIONAL MATCH (friend)<-[:is_post]-(post:Post)
        WITH friend, b, r, collect(sticker) AS stickers, collect(post) AS posts
        RETURN
        CASE
            WHEN friend IS NULL THEN "no such node {get_friend_request.user_node_id}"
            WHEN b IS NOT NULL THEN "block exists"
            ELSE "welcome my friend"
        END AS message,
        friend, COALESCE(properties(r), []) AS roommate_edge, stickers,posts
        """

        result = session.run(query)
        record = result.single()

        if record["message"] != "welcome my friend":
            raise HTTPException(status_code=404, detail=record["message"])

        return GetFriendResponse.from_data(
            dict(record["friend"]),
            dict(record["roommate_edge"]),
            record["stickers"],
            record["posts"],
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/delete-member", response_model=DeleteFriendResponse)
async def delete_member(
    request: Request,
    session=Depends(get_session),
    delete_friend_request: DeleteFriendRequest = Body(...),
):
    logger.info("delete_member")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]
    try:
        query = f"""
        MATCH (u:User)-[r:is_roommate]->(f:User {{node_id: '{delete_friend_request.user_node_id}'}})
        WHERE u.node_id = '{user_node_id}'
        DELETE r
        WITH u, f
        MATCH (f)-[r2:is_roommate]->(u)
        DELETE r2
        RETURN 'Edge deleted' AS message
        """

        result = session.run(query)
        record = result.single()
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No such friend {delete_friend_request.user_node_id} to delete relationship",
            )

        return DeleteFriendResponse(message=record["message"])

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/memo/get-content", response_model=GetMemoResponse)
async def get_memo(
    request: Request,
    session=Depends(get_session),
    get_memo_request: GetMemoRequest = Body(...),
):
    logger.info("get_memo")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User {{node_id: '{user_node_id}'}})-[r:is_roommate]->(f:User {{node_id: '{get_memo_request.user_node_id}'}})
        RETURN r.memo AS memo
        """
        # f"""
        # MATCH (u:User)-[r:is_roommate]->(f:User {{node_id: '{get_memo_request.user_node_id}'}})
        # WHERE f.node_id = '{user_node_id}'
        # RETURN r.memo AS memo
        # """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No memo found for friend {get_memo_request.user_node_id}",
            )

        return GetMemoResponse(memo=record["memo"])

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/memo/modify", response_model=ModifyMemoResponse)
async def modify_memo(
    request: Request,
    session=Depends(get_session),
    modify_memo_request: ModifyMemoRequest = Body(...),
):
    logger.info("modify_memo")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User)-[r:is_roommate]->(f:User {{node_id: '{modify_memo_request.user_node_id}'}})
        WHERE u.node_id = '{user_node_id}'
        SET r.memo = '{modify_memo_request.new_memo}'
        RETURN r.memo AS memo
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No such friend {modify_memo_request.user_node_id} to modify memo",
            )

        return ModifyMemoResponse()

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/group/modify", response_model=ModifyGroupResponse)
async def modify_group(
    request: Request,
    session=Depends(get_session),
    modify_group_request: ModifyGroupRequest = Body(...),
):
    logger.info("modify_group")
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    try:
        query = f"""
        MATCH (u:User)-[r:is_roommate]->(f:User {{node_id: '{modify_group_request.user_node_id}'}})
        WHERE u.node_id = '{user_node_id}'
        SET r.group = '{modify_group_request.new_group}'
        RETURN r.group AS group
        """

        result = session.run(query)
        record = result.single()

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No such group {modify_group_request.user_node_id} to modify group",
            )

        return ModifyGroupResponse()

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
