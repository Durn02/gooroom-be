from pydantic import BaseModel


class ModifyGroupResponse(BaseModel):
    message: str = "Group modified successfully"
