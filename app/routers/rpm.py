from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.db import get_db
from app.models.rpm import RpmRecord
from app.schemas.rpm import (
    RpmRecordCreate,
    RpmRecordUpdate,
    RpmRecordResponse,
    DashboardStats,
    FloorStats,
    FloorMatrixResponse,
)

router = APIRouter(prefix="/rpm", tags=["RPM Schedule & Dashboard"])


def get_quarter_filter(quarter_str: Optional[str]):
    if not quarter_str:
        return None
    q = quarter_str.lower()
    if "1st" in q or "jan" in q or "q1" in q:
        return or_(RpmRecord.quarter.ilike("%1st%"), RpmRecord.quarter.ilike("%Jan%"))
    elif "2nd" in q or "2st" in q or "may" in q or "aug" in q or "q2" in q:
        return or_(RpmRecord.quarter.ilike("%2nd%"), RpmRecord.quarter.ilike("%2st%"), RpmRecord.quarter.ilike("%May%"))
    elif "3rd" in q or "sep" in q or "q3" in q:
        return or_(RpmRecord.quarter.ilike("%3rd%"), RpmRecord.quarter.ilike("%Sep%"))
    elif "4th" in q or "oct" in q or "q4" in q:
        return or_(RpmRecord.quarter.ilike("%4th%"), RpmRecord.quarter.ilike("%Oct%"))
    clean_q = quarter_str.replace("st", "nd").replace("2st", "2nd")
    return or_(
        RpmRecord.quarter.ilike(f"%{quarter_str}%"),
        RpmRecord.quarter.ilike(f"%{clean_q}%")
    )


@router.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats(
    property_name: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns aggregate dashboard statistics for Maxwell Room Preventive Maintenance.
    """
    query = db.query(RpmRecord)
    if property_name:
        query = query.filter(RpmRecord.property_name.ilike(f"%{property_name}%"))
    if year:
        query = query.filter(RpmRecord.year == year)
    q_filter = get_quarter_filter(quarter)
    if q_filter is not None:
        query = query.filter(q_filter)
    
    total_records = query.all()
    total_units = len(total_records)

    total_rooms = sum(1 for r in total_records if r.category == "guest_room")
    total_public_areas = sum(1 for r in total_records if r.category == "public_area")
    completed_count = sum(1 for r in total_records if r.inspection_status == "Done")
    pending_count = total_units - completed_count
    overall_rate = round((completed_count / total_units * 100), 1) if total_units > 0 else 0.0

    # Floor-wise stats
    floor_order = ["Floor 1", "Floor 2", "Floor 3", "Floor 4", "Public Area"]
    floor_stats: List[FloorStats] = []

    for fl in floor_order:
        floor_items = [r for r in total_records if r.floor == fl]
        fl_total = len(floor_items)
        if fl_total == 0:
            continue
        fl_completed = sum(1 for r in floor_items if r.inspection_status == "Done")
        fl_pending = fl_total - fl_completed
        fl_rate = round((fl_completed / fl_total * 100), 1) if fl_total > 0 else 0.0
        floor_stats.append(FloorStats(
            floor=fl,
            total=fl_total,
            completed=fl_completed,
            pending=fl_pending,
            completion_rate=fl_rate
        ))

    recent_completed = [r for r in total_records if r.inspection_status == "Done"][:10]

    return DashboardStats(
        property_name=property_name or "MAXWELL RESERVE",
        quarter=quarter or "2nd Quarter May-August 2026",
        year=year or 2026,
        total_units=total_units,
        total_rooms=total_rooms,
        total_public_areas=total_public_areas,
        completed_count=completed_count,
        pending_count=pending_count,
        overall_completion_rate=overall_rate,
        floor_stats=floor_stats,
        recent_completed=recent_completed
    )


@router.get("/matrix", response_model=FloorMatrixResponse)
def get_floor_matrix(
    property_name: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns records grouped by floor to render the side-by-side 4-column matrix layout.
    """
    query = db.query(RpmRecord)
    if property_name:
        query = query.filter(RpmRecord.property_name.ilike(f"%{property_name}%"))
    if year:
        query = query.filter(RpmRecord.year == year)
    q_filter = get_quarter_filter(quarter)
    if q_filter is not None:
        query = query.filter(q_filter)

    records = query.order_by(RpmRecord.sort_order).all()

    floors_dict: Dict[str, List[RpmRecordResponse]] = {
        "Floor 1": [],
        "Floor 2": [],
        "Floor 3": [],
        "Floor 4": [],
        "Public Area": []
    }

    for r in records:
        target_floor = r.floor if r.floor in floors_dict else "Public Area"
        floors_dict[target_floor].append(RpmRecordResponse.from_orm(r))

    return FloorMatrixResponse(
        property_name=property_name or "MAXWELL RESERVE",
        quarter=quarter or "2nd Quarter May-August 2026",
        year=year or 2026,
        floors=floors_dict
    )


@router.get("/records", response_model=List[RpmRecordResponse])
def list_rpm_records(
    floor: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    property_name: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List RPM records with optional filtering by floor, category, inspection status, year, quarter, and search query.
    """
    query = db.query(RpmRecord)

    if property_name:
        query = query.filter(RpmRecord.property_name.ilike(f"%{property_name}%"))
    if year:
        query = query.filter(RpmRecord.year == year)
    q_filter = get_quarter_filter(quarter)
    if q_filter is not None:
        query = query.filter(q_filter)
    if floor:
        query = query.filter(RpmRecord.floor == floor)
    if category:
        query = query.filter(RpmRecord.category == category)
    if status:
        query = query.filter(RpmRecord.inspection_status == status)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                RpmRecord.room_or_area.ilike(search_pattern),
                RpmRecord.ac_servicing.ilike(search_pattern),
                RpmRecord.housekeeping.ilike(search_pattern),
                RpmRecord.remarks.ilike(search_pattern),
            )
        )

    records = query.order_by(RpmRecord.sort_order).all()

    return records


@router.get("/records/{record_id}", response_model=RpmRecordResponse)
def get_rpm_record(record_id: int, db: Session = Depends(get_db)):
    """Fetch single RPM record by ID."""
    record = db.query(RpmRecord).filter(RpmRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="RPM Record not found")
    return record


@router.post("/records", response_model=RpmRecordResponse, status_code=status.HTTP_201_CREATED)
def create_rpm_record(data: RpmRecordCreate, db: Session = Depends(get_db)):
    """Create a new RPM record."""
    new_record = RpmRecord(**data.dict())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.put("/records/{record_id}", response_model=RpmRecordResponse)
def update_rpm_record(record_id: int, data: RpmRecordUpdate, db: Session = Depends(get_db)):
    """Update an RPM record (e.g. mark inspection as Done or update dates)."""
    record = db.query(RpmRecord).filter(RpmRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="RPM Record not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rpm_record(record_id: int, db: Session = Depends(get_db)):
    """Delete an RPM record."""
    record = db.query(RpmRecord).filter(RpmRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="RPM Record not found")
    db.delete(record)
    db.commit()
    return None

