from pydantic import BaseModel
from typing import List, Dict

class Cast(BaseModel):
    message: str
    duration: int
    created_at: str
    node_id: str
    creator: str

class GetContentsResponse(BaseModel):
    casts: List[Cast]
    stickered_roommates: List[str]
    stickered_neighbors: List[str]

    @classmethod
    def from_datas(cls, casts: List[Dict], stickered_roommates: List[str], stickered_neighbors: List[str]):
        if casts[0]["cast"] is None and casts[0]["creator"] is None:
            cast_objects = []
        else:
            cast_objects = [
                Cast(
                    message=cast["cast"]["message"],
                    duration=cast["cast"]["duration"],
                    created_at=cast["cast"]["created_at"],
                    node_id=cast["cast"]["node_id"],
                    creator=cast["creator"],
                )
                for cast in casts
            ]
        
        return cls(
            casts=cast_objects,
            stickered_roommates=stickered_roommates,
            stickered_neighbors=stickered_neighbors,
        )
