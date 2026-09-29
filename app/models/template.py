from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    property_name = Column(String(100), default="The Maxwell", nullable=False)
    title = Column(String(255), default="ROOM PREVENTIVE MAINTENANCE", nullable=False)
    header_fields = Column(JSON, default=lambda: ["Type", "Room"], nullable=False)
    footer_fields = Column(JSON, default=lambda: ["Date", "Maintenance carried By", "Inspected By"], nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sections = relationship("Section", back_populates="template", cascade="all, delete-orphan", order_by="Section.sort_order")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    code = Column(String(10), nullable=False)  # "A", "B", "C"...
    title = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    template = relationship("Template", back_populates="sections")
    items = relationship("ChecklistItem", back_populates="section", cascade="all, delete-orphan", order_by="ChecklistItem.sort_order")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    item_no = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    section = relationship("Section", back_populates="items")
