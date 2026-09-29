from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.inspection import Inspection, InspectionItem
from app.models.rpm import RpmRecord
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionItemResult,
)

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.get("/", response_model=List[InspectionResponse])
def list_inspections(
    room_number: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List inspection records."""
    query = db.query(Inspection)
    if room_number:
        query = query.filter(Inspection.room_number == room_number)
    if status:
        query = query.filter(Inspection.status == status)

    inspections = query.order_by(Inspection.created_at.desc()).all()
    results = []
    for insp in inspections:
        items = [
            InspectionItemResult(
                checklist_item_id=it.checklist_item_id,
                result=it.result,
                remark=it.remark,
                photo_url=it.photo_url
            )
            for it in insp.items
        ]
        insp_resp = InspectionResponse(
            id=insp.id,
            room_number=insp.room_number,
            room_type=insp.room_type,
            inspection_date=insp.inspection_date,
            status=insp.status,
            maintenance_carried_by=insp.maintenance_carried_by,
            inspected_by=insp.inspected_by,
            signature_url=insp.signature_url,
            overall_remark=insp.overall_remark,
            started_at=insp.started_at,
            submitted_at=insp.submitted_at,
            created_at=insp.created_at,
            updated_at=insp.updated_at,
            items=items
        )
        results.append(insp_resp)
    return results


@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_or_submit_inspection(data: InspectionCreate, db: Session = Depends(get_db)):
    """Create or submit an inspection report and auto-update the RPM schedule status."""
    submitted_at = datetime.utcnow() if data.status == "submitted" else None

    inspection = Inspection(
        room_number=data.room_number,
        room_type=data.room_type,
        inspection_date=data.inspection_date,
        status=data.status,
        maintenance_carried_by=data.maintenance_carried_by,
        inspected_by=data.inspected_by,
        signature_url=data.signature_url,
        overall_remark=data.overall_remark,
        submitted_at=submitted_at
    )
    db.add(inspection)
    db.flush()

    for item_data in data.items:
        item = InspectionItem(
            inspection_id=inspection.id,
            checklist_item_id=item_data.checklist_item_id,
            result=item_data.result,
            remark=item_data.remark,
            photo_url=item_data.photo_url
        )
        db.add(item)

    # Sync with RPM schedule table
    if data.status == "submitted":
        rpm_item = db.query(RpmRecord).filter(
            RpmRecord.room_or_area.ilike(f"%{data.room_number}%")
        ).first()
        if rpm_item:
            rpm_item.inspection_status = "Done"

    db.commit()
    db.refresh(inspection)

    items = [
        InspectionItemResult(
            checklist_item_id=it.checklist_item_id,
            result=it.result,
            remark=it.remark,
            photo_url=it.photo_url
        )
        for it in inspection.items
    ]

    return InspectionResponse(
        id=inspection.id,
        room_number=inspection.room_number,
        room_type=inspection.room_type,
        inspection_date=inspection.inspection_date,
        status=inspection.status,
        maintenance_carried_by=inspection.maintenance_carried_by,
        inspected_by=inspection.inspected_by,
        signature_url=inspection.signature_url,
        overall_remark=inspection.overall_remark,
        started_at=inspection.started_at,
        submitted_at=inspection.submitted_at,
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        items=items
    )
