from pydantic import BaseModel
from typing import List,Dict

class User(BaseModel):
    my_memo: str
    nickname: str
    tags: List[str]
    node_id: str
    username: str
    
    @classmethod
    def from_data(cls, user: Dict[str,str|List[str]]):
        return cls(
            node_id = user.get('node_id',''),
            nickname = user.get('nickname',''),
            tags = user.get('tags',[]),
            my_memo = user.get('my_memo',''),
            username = user.get('username', '')
        )

class GetRoommateResponse(BaseModel):
    roommate: User
    neighbors: List[User]

    @classmethod
    def from_data(cls, roommate: Dict[str,str|List[str]],neighbors: List[Dict[str,str|List[str]]]):
        return cls(
            roommate = User.from_data(roommate),
            neighbors = [User.from_data(n) for n in neighbors]
        )
