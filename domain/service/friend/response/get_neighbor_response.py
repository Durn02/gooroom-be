from typing import List, Dict
from pydantic import BaseModel


class Sticker(BaseModel):
    sticker_node_id: str
    content: str
    image_url: List[str]
    created_at: str

    @classmethod
    def from_data(cls, sticker: Dict[str, List[str] | str]):
        return cls(
            sticker_node_id=sticker.get("node_id", ""),
            content=sticker.get("content", ""),
            image_url=sticker.get("image_url", []),
            created_at=sticker.get("created_at", ""),
        )


class Post(BaseModel):
    post_node_id: str
    content: str
    image_url: List[str]
    created_at: str
    tags: List[str]
    title: str

    @classmethod
    def from_data(cls, post: Dict[str, List[str] | str]):
        return cls(
            post_node_id=post.get("node_id", ""),
            content=post.get("content", ""),
            image_url=post.get("image_url", []),
            created_at=post.get("created_at", ""),
            tags=post.get("tags", []),
            title=post.get("title", ""),
        )


class GetNeighborResponse(BaseModel):
    friend: Dict[str, str | List[str]]
    stickers: List[Sticker]
    posts: List[Post]

    @classmethod
    def from_data(
        cls,
        friend: Dict[str, str],
        stickers: List[Dict[str, str]],
        posts: List[Dict[str, str]],
    ):
        sticker_objects = [Sticker.from_data(dict(sticker)) for sticker in stickers]
        post_objects = [Post.from_data(dict(post)) for post in posts]
        return cls(
            friend=friend,
            stickers=sticker_objects,
            posts=post_objects,
        )
