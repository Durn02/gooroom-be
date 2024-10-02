from pydantic import BaseModel, Field
from typing import List


class MyGroupsChangeResponse(BaseModel):
    message: str
