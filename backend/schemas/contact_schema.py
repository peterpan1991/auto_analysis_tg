from pydantic import BaseModel


class ContactResponse(BaseModel):
    id: int
    name: str
    is_group: bool

    model_config = {"from_attributes": True}