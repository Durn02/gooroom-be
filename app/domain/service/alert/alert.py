import asyncio
from typing import List
from datetime import datetime, timezone
from fastapi import HTTPException, APIRouter, Depends, Body, Request
from app.utils import verify_access_token, Logger
from app.config.connection import get_session

logger = Logger(__file__)
router = APIRouter()
ACCESS_TOKEN = "access_token"


@router.get("/get-members")
async def get_alerts(
    request: Request,
):
    token = request.cookies.get(ACCESS_TOKEN)
    user_node_id = verify_access_token(token)["user_node_id"]

    for _ in range(3):
        alerts = {"new_roommates": [], "stickers_from": [], "casts_received": []}
        session = get_session()
        try:
            query = f"""
            MATCH (me:User {{node_id: '{user_node_id}'}})
            with me
            match (me)<-[new_roommate_edge:is_roommate {{new:true}}]-(new_roommate:User)
            set new_roommate_edge.new = false
            with me, collect(new_roommate) as new_roommates
            MATCH (me)<-[:receiver_of_cast {{new:true}}]-(cast:Cast)<-[:creator_of_cast]-(cast_creator:User)
            return me,new_roommates,cast,cast_creator
            """

            result = session.run(query)
            record = result.single()

            if not record:
                raise HTTPException(
                    status_code=500,
                    detail=f"no such user {user_node_id} or its alertBox",
                )

            if record["new_roommates"]:
                alerts["new_roommates"] = record["new_roommates"]
            if record["stickers_from"]:
                alerts["stickers_from"] = record["stickers_from"]
            if record["casts_received"]:
                alerts["casts_received"] = record["casts_received"]

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            session.close()

        if any(alerts.values()):
            return {"alerts": alerts}
        else:
            await asyncio.sleep(10)

    return {"alerts": alerts}
