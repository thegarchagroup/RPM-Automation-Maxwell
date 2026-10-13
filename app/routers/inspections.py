from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from app.db import get_db
from app.models.inspection import Inspection, InspectionItem
from app.models.rpm import RpmRecord
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionItemResult,
    DefectItemFixRequest,
    DefectBulkFixRequest,
)

router = APIRouter(prefix="/inspections", tags=["Inspections"])


def _format_inspection_response(insp: Inspection) -> InspectionResponse:
    items = [
        InspectionItemResult(
            id=it.id,
            checklist_item_id=it.checklist_item_id,
            result=it.result,
            remark=it.remark,
            inspector_remark=it.inspector_remark,
            photo_url=it.photo_url,
            is_fixed=bool(getattr(it, "is_fixed", False)),
            fixed_at=getattr(it, "fixed_at", None),
            fixed_by=getattr(it, "fixed_by", None),
            fixed_remark=getattr(it, "fixed_remark", None),
        )
        for it in insp.items
    ]
    return InspectionResponse(
        id=insp.id,
        room_number=insp.room_number,
        room_type=insp.room_type,
        inspection_date=insp.inspection_date,
        property_name=insp.property_name or "Maxwell",
        quarter=insp.quarter,
        status=insp.status,
        defects_status=getattr(insp, "defects_status", "open") or "open",
        defects_completed_at=getattr(insp, "defects_completed_at", None),
        maintenance_carried_by=insp.maintenance_carried_by,
        inspected_by=insp.inspected_by,
        signature_url=insp.signature_url,
        inspected_by_signature_url=insp.inspected_by_signature_url,
        overall_remark=insp.overall_remark,
        inspector_remark=insp.inspector_remark,
        started_at=insp.started_at,
        submitted_at=insp.submitted_at,
        verified_at=insp.verified_at,
        created_at=insp.created_at,
        updated_at=insp.updated_at,
        items=items
    )


@router.get("/", response_model=List[InspectionResponse])
def list_inspections(
    room_number: Optional[str] = Query(None),
    property_name: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    has_defects: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List inspection records with optional filters."""
    query = db.query(Inspection).options(selectinload(Inspection.items))
    if room_number and isinstance(room_number, str):
        query = query.filter(Inspection.room_number.ilike(f"%{room_number.strip()}%"))
    if property_name and isinstance(property_name, str):
        query = query.filter(Inspection.property_name.ilike(f"%{property_name.strip()}%"))
    if quarter and isinstance(quarter, str):
        query = query.filter(Inspection.quarter == quarter.strip())
    if status and isinstance(status, str):
        query = query.filter(Inspection.status == status.strip())
    if has_defects is True:
        query = query.filter(Inspection.items.any(InspectionItem.result.ilike("fail")))
    elif has_defects is False:
        query = query.filter(~Inspection.items.any(InspectionItem.result.ilike("fail")))

    inspections = query.order_by(Inspection.created_at.desc()).all()
    return [_format_inspection_response(insp) for insp in inspections]


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Get single inspection details by ID."""
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return _format_inspection_response(insp)


@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_or_submit_inspection(data: InspectionCreate, db: Session = Depends(get_db)):
    """Create or submit an inspection report and auto-update the RPM schedule status."""
    now = datetime.utcnow()
    submitted_at = now if data.status in ["submitted", "verified", "accepted", "rejected"] else None
    verified_at = now if data.status in ["verified", "accepted", "rejected"] else None

    inspection = Inspection(
        room_number=data.room_number,
        room_type=data.room_type,
        inspection_date=data.inspection_date,
        property_name=data.property_name or "Maxwell",
        quarter=data.quarter,
        status=data.status,
        maintenance_carried_by=data.maintenance_carried_by,
        inspected_by=data.inspected_by,
        signature_url=data.signature_url,
        inspected_by_signature_url=data.inspected_by_signature_url,
        overall_remark=data.overall_remark,
        inspector_remark=data.inspector_remark,
        submitted_at=submitted_at,
        verified_at=verified_at,
    )
    db.add(inspection)
    db.flush()

    for item_data in data.items:
        item = InspectionItem(
            inspection_id=inspection.id,
            checklist_item_id=item_data.checklist_item_id,
            result=item_data.result,
            remark=item_data.remark,
            inspector_remark=item_data.inspector_remark,
            photo_url=item_data.photo_url
        )
        db.add(item)

    # Sync with RPM schedule table
    clean_target = data.room_number.lower().replace("room", "").strip()
    target_prop = (data.property_name or "Maxwell").strip().lower()
    rpm_items = db.query(RpmRecord).all()
    rpm_item = next(
        (
            r for r in rpm_items
            if r.room_or_area.lower().replace("room", "").strip() == clean_target
            and (
                target_prop in r.property_name.lower()
                or r.property_name.lower() in target_prop
                or ("maxwell" in target_prop and "maxwell" in r.property_name.lower())
                or ("serangoon" in target_prop and "serangoon" in r.property_name.lower())
                or ("vagabond" in target_prop and "vagabond" in r.property_name.lower())
            )
        ),
        None
    )
    if rpm_item:
        if data.status in ["verified", "accepted"]:
            rpm_item.inspection_status = "Accepted"
            rpm_item.inspection_date = data.inspection_date or now.strftime("%Y-%m-%d")
            if not getattr(rpm_item, 'rpm_date', None):
                rpm_item.rpm_date = rpm_item.eng_date or data.inspection_date
            if data.inspected_by:
                rpm_item.inspected_by = data.inspected_by
            if data.maintenance_carried_by:
                rpm_item.maintenance_carried_by = data.maintenance_carried_by
        elif data.status == "rejected":
            rpm_item.inspection_status = "Rejected"
            rpm_item.inspection_date = data.inspection_date or now.strftime("%Y-%m-%d")
            if data.inspected_by:
                rpm_item.inspected_by = data.inspected_by
            if data.maintenance_carried_by:
                rpm_item.maintenance_carried_by = data.maintenance_carried_by
        elif data.status == "submitted":
            rpm_item.inspection_status = "Pending"
            rpm_item.rpm_date = data.inspection_date or now.strftime("%Y-%m-%d")
            rpm_item.eng_date = data.inspection_date or now.strftime("%Y-%m-%d")
            if data.maintenance_carried_by:
                rpm_item.maintenance_carried_by = data.maintenance_carried_by

    db.commit()
    db.refresh(inspection)
    return _format_inspection_response(inspection)


@router.put("/{inspection_id}", response_model=InspectionResponse)
def update_inspection(inspection_id: int, data: InspectionUpdate, db: Session = Depends(get_db)):
    """Update inspection details, inspector remarks/signature, or checklist answers."""
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")

    now = datetime.utcnow()
    is_verifying = data.status in ["verified", "accepted", "rejected"]

    # Ensure verified forms cannot be altered by normal edits
    if insp.status in ["verified", "accepted"] and not is_verifying:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This form is already verified and locked. Submitted forms cannot be edited."
        )

    if insp.status == "submitted" and not is_verifying:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted forms cannot be edited. Only Inspector verification is permitted."
        )

    if not is_verifying:
        if data.room_number is not None:
            insp.room_number = data.room_number
        if data.room_type is not None:
            insp.room_type = data.room_type
        if data.inspection_date is not None:
            insp.inspection_date = data.inspection_date
        if data.property_name is not None:
            insp.property_name = data.property_name
        if data.quarter is not None:
            insp.quarter = data.quarter
        if data.maintenance_carried_by is not None:
            insp.maintenance_carried_by = data.maintenance_carried_by
        if data.signature_url is not None:
            insp.signature_url = data.signature_url
        if data.overall_remark is not None:
            insp.overall_remark = data.overall_remark

    # Inspector verification fields
    if data.inspected_by is not None:
        insp.inspected_by = data.inspected_by
    if data.inspected_by_signature_url is not None:
        insp.inspected_by_signature_url = data.inspected_by_signature_url
    if data.inspector_remark is not None:
        insp.inspector_remark = data.inspector_remark

    if data.status is not None:
        insp.status = data.status
        if data.status in ["verified", "accepted", "rejected"]:
            insp.verified_at = now
        elif data.status == "submitted" and not insp.submitted_at:
            insp.submitted_at = now

    # Update checklist items if passed
    if data.items is not None:
        existing_items = {it.checklist_item_id: it for it in insp.items}
        for item_data in data.items:
            if item_data.checklist_item_id in existing_items:
                ex = existing_items[item_data.checklist_item_id]
                # Always allow updating result (Pass / Fail) and inspector_remark
                if item_data.result is not None:
                    ex.result = item_data.result
                if not is_verifying:
                    if item_data.remark is not None:
                        ex.remark = item_data.remark
                    if item_data.photo_url is not None:
                        ex.photo_url = item_data.photo_url
                if item_data.inspector_remark is not None:
                    ex.inspector_remark = item_data.inspector_remark
            else:
                if not is_verifying:
                    db.add(InspectionItem(
                        inspection_id=insp.id,
                        checklist_item_id=item_data.checklist_item_id,
                        result=item_data.result,
                        remark=item_data.remark,
                        inspector_remark=item_data.inspector_remark,
                        photo_url=item_data.photo_url
                    ))

    # Sync with RPM schedule table
    clean_target = insp.room_number.lower().replace("room", "").strip()
    target_prop = (insp.property_name or "Maxwell").strip().lower()
    rpm_items = db.query(RpmRecord).all()
    rpm_item = next(
        (
            r for r in rpm_items
            if r.room_or_area.lower().replace("room", "").strip() == clean_target
            and (
                target_prop in r.property_name.lower()
                or r.property_name.lower() in target_prop
                or ("maxwell" in target_prop and "maxwell" in r.property_name.lower())
                or ("serangoon" in target_prop and "serangoon" in r.property_name.lower())
                or ("vagabond" in target_prop and "vagabond" in r.property_name.lower())
            )
        ),
        None
    )
    if rpm_item:
        if insp.status in ["verified", "accepted"]:
            rpm_item.inspection_status = "Accepted"
            rpm_item.inspection_date = insp.inspection_date or now.strftime("%Y-%m-%d")
            if not getattr(rpm_item, 'rpm_date', None):
                rpm_item.rpm_date = rpm_item.eng_date or insp.inspection_date
            if insp.inspected_by:
                rpm_item.inspected_by = insp.inspected_by
            if insp.maintenance_carried_by:
                rpm_item.maintenance_carried_by = insp.maintenance_carried_by
        elif insp.status == "rejected":
            rpm_item.inspection_status = "Rejected"
            rpm_item.inspection_date = insp.inspection_date or now.strftime("%Y-%m-%d")
            if insp.inspected_by:
                rpm_item.inspected_by = insp.inspected_by
            if insp.maintenance_carried_by:
                rpm_item.maintenance_carried_by = insp.maintenance_carried_by
        elif insp.status == "submitted":
            rpm_item.inspection_status = "Pending"
            rpm_item.rpm_date = insp.inspection_date or now.strftime("%Y-%m-%d")
            rpm_item.eng_date = insp.inspection_date or now.strftime("%Y-%m-%d")
            if insp.maintenance_carried_by:
                rpm_item.maintenance_carried_by = insp.maintenance_carried_by

    db.commit()
    db.refresh(insp)
    return _format_inspection_response(insp)


@router.put("/{inspection_id}/items/{item_id}/fix", response_model=InspectionResponse)
def fix_defect_item(
    inspection_id: int,
    item_id: int,
    data: DefectItemFixRequest,
    db: Session = Depends(get_db)
):
    """Mark a specific defect checklist item as fixed with resolution remark."""
    insp = db.query(Inspection).options(selectinload(Inspection.items)).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")

    item = next((it for it in insp.items if it.id == item_id or it.checklist_item_id == item_id), None)
    if not item:
        item = db.query(InspectionItem).filter(
            InspectionItem.inspection_id == inspection_id,
            (InspectionItem.id == item_id) | (InspectionItem.checklist_item_id == item_id)
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Checklist item not found for this inspection")

    now = datetime.utcnow()
    item.is_fixed = data.is_fixed
    if data.is_fixed:
        item.fixed_at = now
        item.fixed_by = data.fixed_by or "Admin"
        item.fixed_remark = data.fixed_remark or "Marked as fixed"
    else:
        item.fixed_at = None
        item.fixed_by = None
        item.fixed_remark = None

    # Recalculate room overall defects status
    failed_items = [it for it in insp.items if it.result and it.result.lower() == "fail"]
    if failed_items:
        all_fixed = all(bool(it.is_fixed) for it in failed_items)
        if all_fixed:
            insp.defects_status = "completed"
            insp.defects_completed_at = now
        else:
            any_fixed = any(bool(it.is_fixed) for it in failed_items)
            insp.defects_status = "in_progress" if any_fixed else "open"
            insp.defects_completed_at = None

    db.commit()
    db.refresh(insp)
    return _format_inspection_response(insp)


@router.put("/{inspection_id}/fix-all", response_model=InspectionResponse)
def fix_all_defect_items(
    inspection_id: int,
    data: DefectBulkFixRequest,
    db: Session = Depends(get_db)
):
    """Mark all failed defect items in an inspection as fixed."""
    insp = db.query(Inspection).options(selectinload(Inspection.items)).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")

    now = datetime.utcnow()
    target_ids = set(data.item_ids) if data.item_ids else None

    for it in insp.items:
        if it.result and it.result.lower() == "fail":
            if target_ids is None or it.id in target_ids or it.checklist_item_id in target_ids:
                it.is_fixed = True
                it.fixed_at = now
                it.fixed_by = data.fixed_by or "Admin"
                if data.fixed_remark:
                    it.fixed_remark = data.fixed_remark
                elif not it.fixed_remark:
                    it.fixed_remark = "Resolved by Admin"

    # Recalculate defects status
    failed_items = [it for it in insp.items if it.result and it.result.lower() == "fail"]
    if failed_items:
        all_fixed = all(bool(it.is_fixed) for it in failed_items)
        if all_fixed:
            insp.defects_status = "completed"
            insp.defects_completed_at = now
        else:
            insp.defects_status = "in_progress"
            insp.defects_completed_at = None

    db.commit()
    db.refresh(insp)
    return _format_inspection_response(insp)
