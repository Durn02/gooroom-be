from pydantic import BaseModel, Field
from typing import List


class MyGroupsChangeRequest(BaseModel):
    groups: List[str] = Field(..., description="List of user's groups")
