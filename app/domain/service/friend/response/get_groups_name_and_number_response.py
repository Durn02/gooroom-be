from pydantic import BaseModel


class GroupMembers(BaseModel):
    name: str
    count: int


class GetGroupsNameAndNumberResponse(BaseModel):
    group_members: list[GroupMembers]
