import os
from datetime import datetime
from typing import Optional, Tuple
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Query, Response
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


KNOWN_QUARTERS = [
    "1st Quarter (Jan - April)",
    "2nd Quarter (May - August)",
    "3rd Quarter (Sept - Dec)",
]


def _normalize_quarter(quarter: Optional[str], fallback_date: Optional[datetime] = None) -> str:
    """Normalizes quarter string to standard folder name, e.g. '1st Quarter (Jan - April)'."""
    if quarter and str(quarter).strip():
        q_str = str(quarter).strip().replace("/", "_")
        q_lower = q_str.lower()
        if "1st" in q_lower or q_lower == "q1":
            return "1st Quarter (Jan - April)"
        elif "2nd" in q_lower or q_lower == "q2":
            return "2nd Quarter (May - August)"
        elif "3rd" in q_lower or q_lower == "q3":
            return "3rd Quarter (Sept - Dec)"
        return q_str

    d = fallback_date or datetime.now()
    m = d.month
    if 1 <= m <= 4:
        return "1st Quarter (Jan - April)"
    elif 5 <= m <= 8:
        return "2nd Quarter (May - August)"
    else:
        return "3rd Quarter (Sept - Dec)"


@router.post("/upload-pdf", response_model=DropboxUploadResponse)
async def upload_pdf_to_dropbox(
    file: UploadFile = File(...),
    room_number: Optional[str] = Form(None),
    quarter: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    filename: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
):
    """
    Upload an inspection report PDF to Dropbox.
    Folder structure:
      {MAXWELL_RPM_FOLDER}/{year}/{quarter}/RPM_report/
        -> for RPM submitted reports
      {MAXWELL_RPM_FOLDER}/{year}/{quarter}/Inspection_report/Accepted/
        -> for accepted inspection reports
      {MAXWELL_RPM_FOLDER}/{year}/{quarter}/Inspection_report/Rejected/
        -> for rejected inspection reports
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    now = datetime.now()
    date_str = now.strftime("%d_%m_%y")

    # Prioritize provided filename if specified (e.g., RPM_101_date.pdf or Inspection_ACCEPTED_101_date.pdf)
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

    # Construct the folder path based on Year -> Quarter -> RPM_report or Inspection_report/(Accepted|Rejected)
    actual_year = year if year else now.year
    clean_quarter = _normalize_quarter(quarter, now)
    base_quarter_path = f"{MAXWELL_RPM_FOLDER}/{actual_year}/{clean_quarter}"

    doc_type_upper = (document_type or "").strip().upper()
    status_upper = (status or "").strip().upper()
    fname_upper = final_filename.upper()

    is_inspection = (
        doc_type_upper == "INSPECTION"
        or fname_upper.startswith("INSPECTION")
        or "INSPECTION" in fname_upper
    )

    if is_inspection:
        is_rejected = (
            "REJECT" in status_upper
            or "REJECT" in fname_upper
        )
        sub_folder = "Inspection_report/Rejected" if is_rejected else "Inspection_report/Accepted"
        folder_path = f"{base_quarter_path}/{sub_folder}"
    else:
        folder_path = f"{base_quarter_path}/RPM_report"

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


def _find_dropbox_pdf(
    room_number: str,
    inspection_date: str,
    year: int,
    quarter: Optional[str] = None,
    document_type: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Finds matching Dropbox PDF file path and filename.
    Searches in:
      - {MAXWELL_RPM_FOLDER}/{year}/{quarter}/RPM_report/
      - {MAXWELL_RPM_FOLDER}/{year}/{quarter}/Inspection_report/Accepted/
      - {MAXWELL_RPM_FOLDER}/{year}/{quarter}/Inspection_report/Rejected/
      - fallback across quarters
      - legacy fallback: {MAXWELL_RPM_FOLDER}/{year}/RPM_report/, {MAXWELL_RPM_FOLDER}/{year}/{quarter}
    """
    clean_room = str(room_number).strip().replace("Room ", "").replace("room ", "").replace("Room", "").replace("room", "").strip()
    req_quarter = _normalize_quarter(quarter) if quarter else ""
    doc_type_upper = (document_type or "").strip().upper()

    # Build prioritized candidate directories to search
    candidate_dirs: List[str] = []

    quarters_to_search: List[str] = []
    if req_quarter:
        quarters_to_search.append(req_quarter)
    for q in KNOWN_QUARTERS:
        if q not in quarters_to_search:
            quarters_to_search.append(q)

    for q_name in quarters_to_search:
        q_safe = q_name.replace("/", "_")
        if doc_type_upper == "RPM":
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/RPM_report")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}")
        elif doc_type_upper == "INSPECTION":
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/Inspection_report/Accepted")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/Inspection_report/Rejected")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/Inspection_report/accepted")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/Inspection_report/rejected")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}")
        else:
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/RPM_report")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/Inspection_report/Accepted")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}/Inspection_report/Rejected")
            candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/{q_safe}")

    # Fallbacks without quarter
    candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/RPM_report")
    candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/Inspection_report/Accepted")
    candidate_dirs.append(f"{MAXWELL_RPM_FOLDER}/{year}/Inspection_report/Rejected")

    seen_dirs = set()
    unique_candidate_dirs: List[str] = []
    for d in candidate_dirs:
        if d not in seen_dirs:
            seen_dirs.add(d)
            unique_candidate_dirs.append(d)

    # Build date representations
    date_variants: List[str] = []
    if inspection_date:
        date_variants.append(inspection_date)
        date_variants.append(inspection_date.replace("-", "_").replace(" ", "_"))

        # Parse ISO date YYYY-MM-DD
        iso_parts = inspection_date.split("-")
        if len(iso_parts) == 3:
            yyyy, mm, dd = iso_parts[0], iso_parts[1], iso_parts[2]
            yy = yyyy[-2:]
            date_variants.append(f"{dd}_{mm}_{yy}")
            date_variants.append(f"{dd}_{mm}_{yyyy}")
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            try:
                m_idx = int(mm) - 1
                if 0 <= m_idx < 12:
                    m_abbr = month_names[m_idx]
                    date_variants.append(f"{dd}_{m_abbr}_{yyyy}")
                    date_variants.append(f"{dd}_{m_abbr}_{yy}")
            except Exception:
                pass

        # Parse "08 Oct 2026"
        month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                     "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
        text_parts = inspection_date.replace("-", " ").replace("_", " ").split()
        if len(text_parts) == 3 and text_parts[1].lower()[:3] in month_map:
            dd = text_parts[0].zfill(2)
            mm = month_map[text_parts[1].lower()[:3]]
            yyyy = text_parts[2]
            yy = yyyy[-2:]
            date_variants.append(f"{dd}_{mm}_{yy}")
            date_variants.append(f"{dd}_{mm}_{yyyy}")
            m_abbr = text_parts[1].capitalize()
            date_variants.append(f"{dd}_{m_abbr}_{yyyy}")
            date_variants.append(f"{dd}_{m_abbr}_{yy}")

    date_variants = list(dict.fromkeys(date_variants))

    candidate_filenames = []
    for d_var in date_variants:
        if doc_type_upper == "INSPECTION":
            candidate_filenames.append(f"Inspection_ACCEPTED_{clean_room}_{d_var}.pdf")
            candidate_filenames.append(f"Inspection_REJECTED_{clean_room}_{d_var}.pdf")
            candidate_filenames.append(f"Inspection_{clean_room}_{d_var}.pdf")
        elif doc_type_upper == "RPM":
            candidate_filenames.append(f"RPM_{clean_room}_{d_var}.pdf")
            candidate_filenames.append(f"{clean_room}_date_{d_var}.pdf")
        elif document_type:
            candidate_filenames.append(f"{document_type}_{clean_room}_{d_var}.pdf")
        
        candidate_filenames.append(f"Inspection_ACCEPTED_{clean_room}_{d_var}.pdf")
        candidate_filenames.append(f"Inspection_REJECTED_{clean_room}_{d_var}.pdf")
        candidate_filenames.append(f"Inspection_{clean_room}_{d_var}.pdf")
        candidate_filenames.append(f"RPM_{clean_room}_{d_var}.pdf")
        candidate_filenames.append(f"{clean_room}_date_{d_var}.pdf")

    seen_fnames = set()
    unique_candidate_fnames = []
    for fname in candidate_filenames:
        if fname not in seen_fnames:
            seen_fnames.add(fname)
            unique_candidate_fnames.append(fname)

    # 1. Search candidate directories by exact candidate filenames
    for dir_path in unique_candidate_dirs:
        for fname in unique_candidate_fnames:
            file_path = f"{dir_path}/{fname}"
            try:
                link = dropbox_service.get_preview_link(file_path)
                if link:
                    return file_path, fname
            except Exception:
                continue

    # 2. Fallback to list_folder_files across candidate directories
    for dir_path in unique_candidate_dirs:
        try:
            entries = dropbox_service.list_folder_files(dir_path)
            matching_entries = []
            for entry in entries:
                name = entry.get("name", "")
                if not name.lower().endswith(".pdf"):
                    continue
                name_parts = name.replace(".pdf", "").split("_")
                if clean_room in name_parts or f"_{clean_room}_" in name or name.startswith(f"{clean_room}_"):
                    matching_entries.append(entry)

            if matching_entries:
                def score_entry(e):
                    nm = e.get("name", "").upper()
                    score = 0
                    if doc_type_upper == "INSPECTION":
                        if "INSPECTION" in nm:
                            score += 10
                        if "ACCEPTED" in nm:
                            score += 2
                        if "REJECTED" in nm:
                            score += 2
                    elif doc_type_upper == "RPM":
                        if "RPM" in nm:
                            score += 10
                        elif "INSPECTION" not in nm:
                            score += 5
                    return score

                matching_entries.sort(key=score_entry, reverse=True)
                for best_entry in matching_entries:
                    p_display = best_entry.get("path_display")
                    if p_display:
                        return p_display, best_entry.get("name", "")
        except Exception:
            pass

    return None, None


@router.get("/download-link")
def get_dropbox_download_link(
    room_number: str,
    inspection_date: str,
    year: int,
    quarter: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None)
):
    """
    Generate a temporary Dropbox download link for an inspection PDF.
    """
    file_path, fname = _find_dropbox_pdf(room_number, inspection_date, year, quarter, document_type)
    if file_path and fname:
        link = dropbox_service.get_preview_link(file_path)
        if link:
            return {"success": True, "download_url": link, "filename": fname, "path": file_path}

    clean_room = str(room_number).strip().replace("Room ", "").replace("room ", "").replace("Room", "").replace("room", "").strip()
    raise HTTPException(
        status_code=404,
        detail=f"Report PDF not found in Dropbox for Room {clean_room} ({inspection_date})"
    )


@router.get("/download")
def download_dropbox_file(
    room_number: str,
    inspection_date: str,
    year: int,
    quarter: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None)
):
    """
    Stream the PDF directly from Dropbox with Content-Disposition attachment header,
    ensuring browsers save it with the correct .pdf filename instead of a temporary UUID.
    """
    file_path, fname = _find_dropbox_pdf(room_number, inspection_date, year, quarter, document_type)
    clean_room = str(room_number).strip().replace("Room ", "").replace("room ", "").replace("Room", "").replace("room", "").strip()

    if not file_path or not fname:
        raise HTTPException(
            status_code=404,
            detail=f"Report PDF not found in Dropbox for Room {clean_room} ({inspection_date})"
        )

    try:
        file_bytes = dropbox_service.download_file(file_path)
        safe_fname = fname if fname.lower().endswith(".pdf") else f"{fname}.pdf"
        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_fname}"',
                "Content-Type": "application/pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download PDF from Dropbox: {str(e)}"
        )