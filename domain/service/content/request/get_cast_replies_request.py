from pydantic import BaseModel

class GetCastRepliesRequest(BaseModel):
    cast_node_id:str