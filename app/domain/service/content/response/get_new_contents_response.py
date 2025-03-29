from pydantic import BaseModel
from typing import List, Dict


class Friend(BaseModel):
    tags: List[str]
    username: str
    nickname: str
    my_memo: str
    node_id: str


class NewRoommate(BaseModel):
    new_roommate: Friend
    neighbors: List[Friend]


class Cast(BaseModel):
    message: str
    duration: int
    created_at: str
    node_id: str
    creator: str


class GetNewContentsResponse(BaseModel):
    new_roommates: List[NewRoommate]
    casts_received: List[Cast]
    stickers_from: List[str]

    @classmethod
    def from_datas(
        cls,
        new_roommates: List[Dict],
        casts: List[Dict],
        stickers_from: List[str]
    ):
        if new_roommates[0]["new_roommate"] is None and new_roommates[0]["neighbors"] == []:
            new_roommate_objects = []
        else:
            new_roommate_objects = [
                NewRoommate(
                    new_roommate=Friend(**roommate["new_roommate"]),
                    neighbors=[Friend(**neighbor) for neighbor in roommate["neighbors"]]
                )
                for roommate in new_roommates
            ]

        if casts[0]["cast"] is None and casts[0]["cast_creator"] is None:
            cast_objects = []
        else:
            cast_objects = [
                Cast(
                    message=cast["cast"]["message"],
                    duration=cast["cast"]["duration"],
                    created_at=cast["cast"]["created_at"],
                    node_id=cast["cast"]["node_id"],
                    creator=cast["cast_creator"],
                )
                for cast in casts
            ]

        return cls(
            new_roommates=new_roommate_objects,
            casts_received=cast_objects,
            stickers_from=stickers_from,
        )

    def is_empty(self) -> bool:
        return not self.new_roommates and not self.casts_received and not self.stickers_from
