from pydantic import BaseModel

class ReadStickerRequest(BaseModel):
    sticker_id:str
    
