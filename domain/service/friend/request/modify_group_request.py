from pydantic import BaseModel


class ModifyGroupRequest(BaseModel):
    user_node_id: str
    new_group: str
