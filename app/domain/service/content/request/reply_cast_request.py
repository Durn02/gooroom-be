from pydantic import BaseModel
from typing import Literal

class ReplyCastRequest(BaseModel):
    cast_node_id: str
    content: str
    type: Literal["image", "message", "emotion"]
    is_public:bool = True
