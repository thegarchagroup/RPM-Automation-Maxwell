from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.db import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    room_number = Column(String(50), nullable=False, index=True)
    room_type = Column(String(50), nullable=False)
    
    inspection_date = Column(String(50), nullable=False)
    property_name = Column(String(100), default="Maxwell", nullable=True)
    quarter = Column(String(100), nullable=True)
    status = Column(String(50), default="in_progress", nullable=False)  # in_progress, submitted, verified
    defects_status = Column(String(50), default="open", nullable=True)  # open, in_progress, completed
    defects_completed_at = Column(DateTime, nullable=True)
    
    maintenance_carried_by = Column(String(255), nullable=True)
    inspected_by = Column(String(255), nullable=True)
    signature_url = Column(Text, nullable=True)
    inspected_by_signature_url = Column(Text, nullable=True)
    overall_remark = Column(Text, nullable=True) # RPM/maintenance remark
    inspector_remark = Column(Text, nullable=True) # Inspector remark
    
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship("InspectionItem", back_populates="inspection", cascade="all, delete-orphan")


class InspectionItem(Base):
    __tablename__ = "inspection_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    checklist_item_id = Column(Integer, nullable=False)
    result = Column(String(20), nullable=False)  # pass, fail, na
    remark = Column(Text, nullable=True)  # RPM remark
    inspector_remark = Column(Text, nullable=True)  # Inspector remark
    photo_url = Column(Text, nullable=True)
    is_fixed = Column(Boolean, default=False, nullable=True)
    fixed_at = Column(DateTime, nullable=True)
    fixed_by = Column(String(255), nullable=True)
    fixed_remark = Column(Text, nullable=True)

    inspection = relationship("Inspection", back_populates="items")
