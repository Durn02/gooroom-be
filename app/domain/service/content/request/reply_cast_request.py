from pydantic import BaseModel, Field
from typing import List


class ReplyCastRequest(BaseModel):
    message: str
    cast_id: str
