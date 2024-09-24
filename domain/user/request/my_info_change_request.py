from pydantic import BaseModel, Field
from typing import List


class MyInfoChangeRequest(BaseModel):
    my_memo: str = Field("", description="Memo for the user")
    nickname: str = Field(..., description="User's nickname")
    username: str = Field(..., description="User's full name")
    tags: List[str] = Field(..., description="List of user's tags")
