import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Query
from pydantic import BaseModel

from app.services.dropbox_service import dropbox_service

router = APIRouter(prefix="/dropbox", tags=["Dropbox Cloud Storage"])


class DropboxStatusResponse(BaseModel):
    configured: bool
    app_key_present: bool
    has_token: bool
    target_folder: str


class DropboxUploadResponse(BaseModel):
    success: bool
    message: str
    path: str
    size: int
    share_url: Optional[str] = None


MAXWELL_RPM_FOLDER = (
    "/2 - maxwell operations (murray pte ltd)"
    "/6 - engineering ops (maxwell)"
    "/2 - preventive maintenance"
    "/RPM"
)


@router.get("/status", response_model=DropboxStatusResponse)
def get_dropbox_status():
    """Check if Dropbox configuration credentials are present in .env"""
    has_token = bool(dropbox_service.refresh_token or dropbox_service.access_token)
    app_key_present = bool(dropbox_service.app_key)
    return DropboxStatusResponse(
        configured=has_token,
        app_key_present=app_key_present,
        has_token=has_token,
        target_folder=MAXWELL_RPM_FOLDER
    )


@router.post("/upload-pdf", response_model=DropboxUploadResponse)
async def upload_pdf_to_dropbox(
    file: UploadFile = File(...),
    room_number: Optional[str] = Form(None),
    quarter: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    filename: Optional[str] = Form(None)
):
    """
    Upload an inspection report PDF to Dropbox, into the confirmed
    Maxwell RPM folder. If no filename is given, dropbox_service
    auto-generates one from today's date.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    now = datetime.now()
    date_str = now.strftime("%d_%m_%y")

    # Prioritize provided filename if specified (e.g., RPM_101_date.pdf or Inspection_101_date.pdf)
    if filename and filename.strip():
        final_filename = filename.strip()
        if not final_filename.endswith(".pdf"):
            final_filename = f"{final_filename}.pdf"
    elif file.filename and file.filename.strip() and not file.filename.startswith("blob"):
        final_filename = file.filename.strip()
        if not final_filename.endswith(".pdf"):
            final_filename = f"{final_filename}.pdf"
    elif room_number:
        clean_room_no = str(room_number).strip().replace(" ", "_").replace("/", "_")
        final_filename = f"{clean_room_no}_date_{date_str}.pdf"
    else:
        final_filename = f"report_date_{date_str}.pdf"

    # Construct the folder path based on year and quarter
    # The Dropbox API automatically creates missing folders during upload
    folder_path = MAXWELL_RPM_FOLDER
    actual_year = year if year else now.year
    folder_path += f"/{actual_year}"
    
    if quarter:
        clean_quarter = str(quarter).strip().replace("/", "_")
        folder_path += f"/{clean_quarter}"

    try:
        result = dropbox_service.upload_pdf(
            file_bytes=file_bytes,
            filename=final_filename,
            folder_path=folder_path
        )
        return DropboxUploadResponse(**result)
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/download-link")
def get_dropbox_download_link(
    room_number: str,
    inspection_date: str,
    year: int,
    quarter: str,
    document_type: Optional[str] = Query(None) # "Inspection" or "RPM" or None
):
    """
    Generate a temporary Dropbox download link for an inspection PDF.
    Searches for Inspection_<room>_<date>.pdf, RPM_<room>_<date>.pdf, or <room>_date_<date>.pdf.
    """
    # Parse the date from YYYY-MM-DD to dd_mm_yy
    try:
        parts = inspection_date.split("-")
        if len(parts) == 3:
            yy = parts[0][-2:]  # last 2 digits of year
            mm = parts[1]
            dd = parts[2]
            date_str = f"{dd}_{mm}_{yy}"
        else:
            date_str = inspection_date.replace("-", "_")
    except Exception:
        date_str = inspection_date.replace("-", "_")

    # Clean room number (extract just the number)
    clean_room = str(room_number).strip().replace("Room ", "").replace("room ", "").strip()
    clean_quarter = str(quarter).strip()
    dir_path = f"{MAXWELL_RPM_FOLDER}/{year}/{clean_quarter}"

    # Try preferred filenames
    candidate_filenames = []
    if document_type:
        candidate_filenames.append(f"{document_type}_{clean_room}_{inspection_date}.pdf")
        candidate_filenames.append(f"{document_type}_{clean_room}_{date_str}.pdf")
    
    candidate_filenames.extend([
        f"Inspection_{clean_room}_{inspection_date}.pdf",
        f"Inspection_{clean_room}_{date_str}.pdf",
        f"RPM_{clean_room}_{inspection_date}.pdf",
        f"RPM_{clean_room}_{date_str}.pdf",
        f"{clean_room}_date_{date_str}.pdf",
        f"{clean_room}_date_{inspection_date}.pdf",
    ])

    for fname in candidate_filenames:
        file_path = f"{dir_path}/{fname}"
        try:
            link = dropbox_service.get_preview_link(file_path)
            if link:
                return {"success": True, "download_url": link, "filename": fname, "path": file_path}
        except Exception:
            continue

    raise HTTPException(
        status_code=404,
        detail=f"Report PDF not found in Dropbox for Room {clean_room} ({inspection_date})"
    )