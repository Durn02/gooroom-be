from typing import List
from pydantic import BaseModel, Field

class MyInfoChangeRequest(BaseModel):
    my_memo: str = Field("", description="Memo for the user")
    nickname: str = Field(..., description="User's nickname")
    username: str = Field(..., description="User's full name")
    tags: List[str] = Field([], description="User's tags")
    profile_image_url:str = Field(...,description="profile imgurl")