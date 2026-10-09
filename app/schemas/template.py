from typing import List, Optional, Any
from pydantic import BaseModel


class ChecklistItemBase(BaseModel):
    item_no: int
    description: str
    sort_order: int = 0


class ChecklistItemCreate(ChecklistItemBase):
    pass


class ChecklistItemUpdate(BaseModel):
    item_no: Optional[int] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class ChecklistItemResponse(ChecklistItemBase):
    id: int
    section_id: int

    class Config:
        from_attributes = True


class SectionBase(BaseModel):
    code: str
    title: str
    sort_order: int = 0


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    sort_order: Optional[int] = None


class SectionResponse(SectionBase):
    id: int
    template_id: int
    items: List[ChecklistItemResponse] = []

    class Config:
        from_attributes = True


class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    property_name: Optional[str] = None
    header_fields: Optional[List[str]] = None
    footer_fields: Optional[List[str]] = None
    is_active: Optional[bool] = None


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
