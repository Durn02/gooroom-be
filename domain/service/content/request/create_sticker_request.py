from pydantic import BaseModel, Field
from typing import List


class CreateStickerRequest(BaseModel):
    content: str = Field(..., min_length=0)
    image_url: List[str]
