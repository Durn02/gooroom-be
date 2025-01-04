from typing import List
from fastapi import APIRouter, HTTPException, Depends
from domain.auth.request.signup_request import SignUpRequest
from domain.service.content.content import delete_old_casts
from utils import Logger
from config.connection import get_session
from .dummy import (
    CREATE_SEVERAL_DUMMY,
    CREATE_FOURTEEN_DUMMY_NODES_QUERY,
    CREATE_FOURTEEN_DUMMY_RELATIONS_QUERY,
    DELETE_DUMMY_DATA_QUERY,
)

router = APIRouter()
logger = Logger(__file__)


@router.get("/nodes")
async def read_nodes(session=Depends(get_session)):
    try:
        logger.info("get nodes - test")
        result = session.run("MATCH (n) RETURN n")
        nodes = []
        for record in result:
            nodes.append(record["n"])
        return {"nodes": nodes}
    finally:
        session.close()


@router.post("/create-fourteen-dummy-nodes")
async def create_fourteen_dummy_nodes(
    session=Depends(get_session),
):
    logger.info("create-fourteen-dummy-nodes")

    try:
        dummy_users = [
            SignUpRequest(
                email=f"test{i}@gooroom.com",
                password="$2b$12$K4kuDTzku5n.xyXYd45lUODLIZH5FGHY7upzFAGie20nQkG8iTibS",
                tags=["string"],
                nickname=f"nickname{i}",
                username=f"test{i}",
            )
            for i in range(1, 15)
        ]

        query = CREATE_TEN_DUMMY_NODES_QUERY
        result = session.run(
            query, {"users": [user.model_dump() for user in dummy_users]}
        )

        if "data already exists" in [d["value.message"] for d in result.data()]:
            raise HTTPException(status_code=400, detail="Data already exists")

        query = CREATE_FOURTEEN_DUMMY_RELATIONS_QUERY
        result = session.run(query)
        record = result.single()

        if record is None:
            raise HTTPException(status_code=400, detail="Failed to create dummy data")

        return "creating dummy data successfully"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/create-several-dummy")
async def create_several_dummy(
    adjacency_matrix: List[List[int]], session=Depends(get_session)
):
    logger.info("create-several-dummy")

    try:
        number_of_nodes = len(adjacency_matrix)
        dummy_users = [
            SignUpRequest(
                email=f"test{i}@gooroom.com",
                password="$2b$12$K4kuDTzku5n.xyXYd45lUODLIZH5FGHY7upzFAGie20nQkG8iTibS",
                tags=["string"],
                nickname=f"nickname{i}",
                username=f"test{i}",
            )
            for i in range(number_of_nodes)
        ]

        query = CREATE_SEVERAL_DUMMY
        result = session.run(
            query,
            {
                "users": [user.model_dump() for user in dummy_users],
                "adjacency_matrix": adjacency_matrix,
            },
        )

        record = result.single()

        if record is None:
            raise HTTPException(status_code=400, detail="Failed to create dummy data")

        return f"Creating {number_of_nodes} dummy nodes and their relationships successfully"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/dummy_delete")
async def dummy_delete(session=Depends(get_session)):
    try:
        logger.info("dummy-delete")
        result = session.run(DELETE_DUMMY_DATA_QUERY)
        record = result.single()

        return record[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/delete_old_casts")
async def delete_old_casts_api():
    try:
        delete_old_casts()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
