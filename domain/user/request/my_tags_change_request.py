from typing import List
from pydantic import BaseModel, Field


class MyTagsChangeRequest(BaseModel):
    tags: List[str] = Field(..., description="List of user's tags")
