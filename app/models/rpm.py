from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db import Base


class RpmRecord(Base):
    __tablename__ = "rpm_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    property_name = Column(String(100), default="MAXWELL RESERVE", nullable=False, index=True)
    year = Column(Integer, default=2026, nullable=False, index=True)
    quarter = Column(String(100), default="2nd Quarter May-August 2026", nullable=False, index=True)
    
    floor = Column(String(50), nullable=False, index=True)  # Floor 1, Floor 2, Floor 3, Floor 4, Public Area
    category = Column(String(50), default="guest_room", nullable=False, index=True)  # guest_room, public_area
    room_or_area = Column(String(100), nullable=False, index=True)  # e.g., Room 101, Lobby, Shikar
    
    eng_date = Column(String(50), nullable=True)  # e.g., 2026-05-15
    ac_servicing = Column(String(255), nullable=True)  # e.g., 2026-05-15 or notes
    housekeeping = Column(String(100), nullable=True)
    inspection_status = Column(String(50), default="Pending", nullable=False, index=True)  # Done, Pending, In Progress
    
    remarks = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
