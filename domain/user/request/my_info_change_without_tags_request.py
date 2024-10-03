from pydantic import BaseModel, Field


class MyInfoChangeWithoutTagsRequest(BaseModel):
    my_memo: str = Field("", description="Memo for the user")
    nickname: str = Field(..., description="User's nickname")
    username: str = Field(..., description="User's full name")
