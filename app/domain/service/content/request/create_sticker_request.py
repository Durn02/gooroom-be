from typing import List
from fastapi import Form, UploadFile
from pydantic import BaseModel


class CreateStickerRequest(BaseModel):
    content: str = (Form(...),)
    image_url: List[UploadFile] = (Form(...),)
