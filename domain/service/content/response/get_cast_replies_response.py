from pydantic import BaseModel
from typing import Dict

class Reply(BaseModel):
    content: str
    created_at: str
    type: str
    is_public:bool
    node_id: str

class Replier(BaseModel):
    nickname: str
    node_id: str

class GetCastRepliesResponse(BaseModel):
    reply: Reply
    replier: Replier

    @classmethod
    def from_data(cls, reply: Dict[str, str|bool], replier: Dict[str, str]):

        return cls(
            reply=Reply(
                content=reply.get("content"),
                created_at=reply.get("created_at"),
                type=reply.get("type"),
                private=reply.get("is_public"),
                node_id=reply.get("node_id"),
            ),
            replier=Replier(
                nickname=replier.get("nickname"),
                node_id=replier.get("node_id"),
            )
        )

    def is_empty(self) -> bool:
        return not self.reply is None