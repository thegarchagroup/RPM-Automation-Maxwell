from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.template import Template
from app.schemas.template import TemplateResponse
from app.services.template_seeder import seed_maxwell_template

router = APIRouter(prefix="/templates", tags=["Checklist Templates"])


@router.get("/maxwell", response_model=TemplateResponse)
def get_maxwell_template(db: Session = Depends(get_db)):
    """Fetch the active Maxwell checklist template with Sections A through K."""
    template = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if not template:
        template = seed_maxwell_template(db)
    return template


@router.get("/", response_model=List[TemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    """List all inspection checklist templates."""
    templates = db.query(Template).all()
    if not templates:
        seed_maxwell_template(db)
        templates = db.query(Template).all()
    return templates
