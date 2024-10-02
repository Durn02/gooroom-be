from pydantic import BaseModel, Field
from typing import List


class MyTagsChangeRequest(BaseModel):
    tags: List[str] = Field(..., description="List of user's tags")
