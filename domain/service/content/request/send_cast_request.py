from pydantic import BaseModel, Field
from typing import List


class SendCastRequest(BaseModel):
    friends: List[str] = Field(..., min_items=1) 
    message: str
    duration: int = Field(
        ..., ge=1
    )  # cast의 지속 hour. ex) duration = 1 이면 1시간동안 cast가 살아있게됨
