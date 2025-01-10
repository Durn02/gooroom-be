from pydantic import BaseModel
from typing import List

class CreateStickerRequest(BaseModel):
    content: str
    image_url: List[str]
