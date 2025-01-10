from pydantic import BaseModel
from typing import Dict,List

class Sticker(BaseModel):
    node_id:str
    content:str
    image_url:List[str]
    created_at:str

class Creator(BaseModel):
    node_id:str
    nickname:str
    my_memo:str

class GetMyStickersResponse(BaseModel):
    sticker:Sticker
    creator:Creator

    @classmethod
    def from_data(cls, sticker: Dict[str,List[str]|str],receiver_edge:Dict[str,str|bool],creator:Dict[str,str] ):
        return cls(
            sticker=Sticker(
                node_id=sticker.get('node_id'),
                content=sticker.get("content", ''),
                image_url=sticker.get("image_url", []),
                created_at=sticker.get("created_at")),
            creator=Creator(
                node_id=creator.get('node_id'),
                nickname=creator.get('nickname',creator.get('username')),
                my_memo=creator.get('memo',''))
        )