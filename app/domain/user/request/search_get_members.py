from pydantic import BaseModel


class SearchGetMembersRequest(BaseModel):
    query: str = ""
