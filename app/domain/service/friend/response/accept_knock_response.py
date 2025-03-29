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

class AcceptKnockResponse(BaseModel):
    new_roommate: User
    new_neighbors: List[User]

    @classmethod
    def from_data(cls, new_roommate: Dict[str,str|List[str]],new_neighbors: List[Dict[str,str|List[str]]]):
        return cls(
            new_roommate = User.from_data(new_roommate),
            new_neighbors = [User.from_data(n) for n in new_neighbors]
        )
