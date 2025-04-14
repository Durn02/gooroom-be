from pydantic import BaseModel

class GetNeighborsWithStickerRequest(BaseModel):
    roommate_node_id:str