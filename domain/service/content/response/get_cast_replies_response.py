from pydantic import BaseModel
from typing import Dict

class Reply(BaseModel):
    content: str
    created_at: str
    type: str
    node_id: str

class Replier(BaseModel):
    nickname: str
    node_id: str

class GetCastRepliesResponse(BaseModel):
    reply: Reply
    replier: Replier

    @classmethod
    def from_data(cls, arg1: Dict[str, str], arg2: Dict[str, str]):

        return cls(
            reply=Reply(
                content=arg1.get("content"),
                created_at=arg1.get("created_at"),
                type=arg1.get("type"),
                node_id=arg1.get("node_id"),
            ),
            replier=Replier(
                nickname=arg2.get("nickname"),
                node_id=arg2.get("node_id"),
            )
        )
