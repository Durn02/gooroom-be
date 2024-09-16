from pydantic import BaseModel
from typing import List, Dict

class CastNode(BaseModel):
    duration: str
    created_at: str
    message: str
    deleted_at: str
    node_id: str

class Creator(BaseModel):
    my_memo: str
    nickname: str
    username: str
    node_id: str
    concern: List[str]

class GetCastsResponse(BaseModel):
    cast_node: CastNode
    creator: Creator

    @classmethod
    def from_data(cls, cast: Dict[str, str], creator: Dict[str, str]):
        return cls(
            cast_node=CastNode(
                duration=cast.get("duration", ''),
                created_at=cast.get("created_at", ''),
                message=cast.get("message", ''),
                deleted_at=cast.get("deleted_at", ''),
                node_id=cast.get("node_id", '')
            ),
            creator=Creator(
                my_memo=creator.get("my_memo", ''),
                nickname=creator.get("nickname", ''),
                username=creator.get("username", ''),
                node_id=creator.get("node_id", ''),
                concern=creator.get("concern", [])
            )
        )
