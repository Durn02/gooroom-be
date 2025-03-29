from pydantic import BaseModel
from typing import List, Dict

class Sticker(BaseModel):
    sticker_node_id:str
    content:str
    image_url:List[str]
    created_at: str

    @classmethod
    def from_data(cls, sticker: Dict[str,List[str]|str] ):
        return cls(
            sticker_node_id = sticker.get('node_id',''),
            content=sticker.get("content", ''),
            image_url=sticker.get("image_url", []),
            created_at=sticker.get("created_at", '')
        )

class Post(BaseModel):
    post_node_id:str
    content:str
    image_url:List[str]
    created_at:str
    tags:List[str]
    title:str

    @classmethod
    def from_data(cls, post: Dict[str,List[str]|str] ):
        return cls(
            post_node_id = post.get('node_id',''),
            content=post.get("content", ''),
            image_url=post.get("image_url", []),
            created_at=post.get("created_at",''),
            tags=post.get("tags",[]),
            title=post.get("title","")
        )
    
class GetFriendResponse(BaseModel):
    friend: Dict[str,str|List[str]]
    roommate_edge: Dict[str, str|List[str]]
    stickers: List[Sticker]
    posts: List[Post]

    @classmethod
    def from_data(cls, 
            friend: Dict[str, str],
            roommate_edge: Dict[str, str|List[str]], 
            stickers: List[Dict[str, str]], 
            posts: List[Dict[str, str]]
        ):
        sticker_objects = [Sticker.from_data(dict(sticker)) for sticker in stickers]
        post_objects = [Post.from_data(dict(post)) for post in posts]
        return cls(
            friend=friend,
            roommate_edge=roommate_edge,
            stickers=sticker_objects,
            posts=post_objects,
        )


# class Cast(BaseModel):
#     cast_edge_id:str
#     cast_id:str
#     message:str
#     created_at:str
#     friend_nickname:str
#     friend_node_id:str

#     @classmethod
#     def from_data(cls, cast: Dict[str,str] ,friend:Dict[str,str]):
#         return cls(
#             cast_edge_id = cast.get("edge_id",''),
#             cast_id=cast.get("cast_id",''),
#             message=cast.get("message", ''),
#             created_at=cast.get("created_at",''),
#             friend_nickname=friend.get("nickname"),
#             friend_node_id=friend.get("node_id",'')
#         )
