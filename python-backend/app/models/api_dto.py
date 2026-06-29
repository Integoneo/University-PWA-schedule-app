from pydantic import BaseModel, ConfigDict
from typing import List


class Groups_PWA_schema(BaseModel):
    id: int
    name: str
    course: str | None
    education_form: str | None

    model_config = ConfigDict(from_attributes=True)


class Institutes_PWA_schema(BaseModel):
    id: int
    name: str
    short_name: str
    icon_url: str | None
    groups: List[Groups_PWA_schema]

    model_config = ConfigDict(from_attributes=True)
