from pydantic import BaseModel, Field
from typing import List


class MyTagsChangeResponse(BaseModel):
    message: str
