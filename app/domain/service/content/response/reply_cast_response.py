from pydantic import BaseModel

class ReplyCastResponse(BaseModel):
    message:str = "replied successfully"
