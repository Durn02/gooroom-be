from pydantic import BaseModel
from typing import List, Dict

class GetNeighborsWithStickerResponse(BaseModel):
    tags: List[str]
    username: str
    nickname: str
    my_memo: str
    node_id: str
    has_sticker:bool

    @classmethod
    def from_data(
        cls,
        neighbor: Dict[str,str|List],
        stickers: List[str],
    ):
        return cls(
            tags=neighbor["tags"],
            username=neighbor["username"],
            nickname=neighbor["nickname"],
            my_memo=neighbor["my_memo"],
            node_id=neighbor["node_id"],
            has_sticker= False if not stickers else True
        )