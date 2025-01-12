from pydantic import BaseModel
from typing import Dict,List

class GetMyStickersResponse(BaseModel):
    sticker_node_id:str
    content:str
    image_url:List[str]
    created_at: str

    @classmethod
    def from_data(cls, sticker: Dict[str,List[str]|str] ):
        return cls(
            sticker_node_id = sticker["node_id"],
            content=sticker["content"],
            image_url=sticker["image_url"],
            created_at=sticker["created_at"]
        )