from pydantic import BaseModel


class DeleteMyPostRequest(BaseModel):
    post_node_id: str
    post_image_urls: list[str]
