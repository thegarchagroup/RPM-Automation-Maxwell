from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.template import Template, Section, ChecklistItem
from app.schemas.template import (
    TemplateResponse,
    TemplateUpdate,
    SectionCreate,
    SectionUpdate,
    SectionResponse,
    ChecklistItemCreate,
    ChecklistItemUpdate,
    ChecklistItemResponse,
)
import json
from pathlib import Path
from app.services.template_seeder import seed_maxwell_template, MAXWELL_SECTIONS_DATA

JSON_FILE = Path(__file__).resolve().parent.parent.parent / "Maxwell_Inspection_List.json"

router = APIRouter(prefix="/templates", tags=["Checklist Templates"])


@router.get("/maxwell")
def get_maxwell_template(db: Session = Depends(get_db)):
    """Fetch the active Maxwell checklist template from Maxwell_Inspection_List.json without slow DB queries."""
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    template = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if not template:
        template = seed_maxwell_template(db)
    return template


@router.put("/maxwell", response_model=TemplateResponse)
def update_maxwell_template(data: TemplateUpdate, db: Session = Depends(get_db)):
    """Update Maxwell template metadata (Title, Header fields, etc.)."""
    template = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if not template:
        template = seed_maxwell_template(db)

    if data.title is not None:
        template.title = data.title
    if data.property_name is not None:
        template.property_name = data.property_name
    if data.header_fields is not None:
        template.header_fields = data.header_fields
    if data.footer_fields is not None:
        template.footer_fields = data.footer_fields
    if data.is_active is not None:
        template.is_active = data.is_active

    db.commit()
    db.refresh(template)
    return template


@router.post("/maxwell/reset", response_model=TemplateResponse)
def reset_maxwell_template(db: Session = Depends(get_db)):
    """Reset the Maxwell template back to its default 11 sections (A through K)."""
    template = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if template:
        # Delete existing sections and cascade delete checklist items
        for sec in list(template.sections):
            db.delete(sec)
        db.commit()

        # Re-seed sections & items
        for sec_idx, sec_data in enumerate(MAXWELL_SECTIONS_DATA):
            section = Section(
                template_id=template.id,
                code=sec_data["code"],
                title=sec_data["title"],
                sort_order=sec_idx + 1
            )
            db.add(section)
            db.flush()

            for item_data in sec_data["items"]:
                item = ChecklistItem(
                    section_id=section.id,
                    item_no=item_data["item_no"],
                    description=item_data["description"],
                    sort_order=item_data["item_no"]
                )
                db.add(item)
        db.commit()
        db.refresh(template)
        return template
    else:
        return seed_maxwell_template(db)


# ===================== SECTION MANAGEMENT =====================

@router.post("/maxwell/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
def add_section(data: SectionCreate, db: Session = Depends(get_db)):
    """Add a new section to the Maxwell checklist template."""
    template = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if not template:
        template = seed_maxwell_template(db)

    # Determine sort order if not provided
    max_order = max([s.sort_order for s in template.sections] or [0])
    sort_order = data.sort_order if data.sort_order > 0 else max_order + 1

    section = Section(
        template_id=template.id,
        code=data.code.strip().upper(),
        title=data.title.strip(),
        sort_order=sort_order
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.put("/sections/{section_id}", response_model=SectionResponse)
def update_section(section_id: int, data: SectionUpdate, db: Session = Depends(get_db)):
    """Update section code, title, or sort order."""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    if data.code is not None:
        section.code = data.code.strip().upper()
    if data.title is not None:
        section.title = data.title.strip()
    if data.sort_order is not None:
        section.sort_order = data.sort_order

    db.commit()
    db.refresh(section)
    return section


@router.delete("/sections/{section_id}", status_code=status.HTTP_200_OK)
def delete_section(section_id: int, db: Session = Depends(get_db)):
    """Delete a section and all its checklist items."""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    db.delete(section)
    db.commit()
    return {"message": f"Section {section.code} and its items were successfully deleted"}


# ===================== CHECKLIST ITEM MANAGEMENT =====================

@router.post("/sections/{section_id}/items", response_model=ChecklistItemResponse, status_code=status.HTTP_201_CREATED)
def add_checklist_item(section_id: int, data: ChecklistItemCreate, db: Session = Depends(get_db)):
    """Add a new checklist item to a section."""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Determine item_no if not provided
    max_no = max([it.item_no for it in section.items] or [0])
    item_no = data.item_no if data.item_no > 0 else max_no + 1

    item = ChecklistItem(
        section_id=section.id,
        item_no=item_no,
        description=data.description.strip(),
        sort_order=data.sort_order if data.sort_order > 0 else item_no
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ChecklistItemResponse)
def update_checklist_item(item_id: int, data: ChecklistItemUpdate, db: Session = Depends(get_db)):
    """Update checklist item number, description, or sort order."""
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    if data.item_no is not None:
        item.item_no = data.item_no
    if data.description is not None:
        item.description = data.description.strip()
    if data.sort_order is not None:
        item.sort_order = data.sort_order

    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_checklist_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a checklist item from a section."""
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    db.delete(item)
    db.commit()
    return {"message": "Checklist item deleted successfully"}


@router.get("/", response_model=List[TemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    """List all inspection checklist templates."""
    templates = db.query(Template).all()
    if not templates:
        seed_maxwell_template(db)
        templates = db.query(Template).all()
    return templates
