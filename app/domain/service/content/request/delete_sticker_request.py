from pydantic import BaseModel


class DeleteStickerRequest(BaseModel):
    sticker_node_id: str
    sticker_image_urls: list[str]
