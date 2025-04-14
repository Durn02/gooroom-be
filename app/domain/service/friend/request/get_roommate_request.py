from pydantic import BaseModel

class GetRoommateRequest(BaseModel):
    user_node_id: str
