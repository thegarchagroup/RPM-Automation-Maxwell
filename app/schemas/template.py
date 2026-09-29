from typing import List, Optional, Any
from pydantic import BaseModel


class ChecklistItemBase(BaseModel):
    item_no: int
    description: str
    sort_order: int = 0


class ChecklistItemResponse(ChecklistItemBase):
    id: int
    section_id: int

    class Config:
        from_attributes = True


class SectionBase(BaseModel):
    code: str
    title: str
    sort_order: int = 0


class SectionResponse(SectionBase):
    id: int
    template_id: int
    items: List[ChecklistItemResponse] = []

    class Config:
        from_attributes = True


class TemplateResponse(BaseModel):
    id: int
    property_name: str
    title: str
    header_fields: List[str]
    footer_fields: List[str]
    version: int
    is_active: bool
    sections: List[SectionResponse] = []

    class Config:
        from_attributes = True
