import os
import csv
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.rpm import RpmRecord
from app.models.user import User

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "maxwell_reserve_rpm_2026.csv")


def parse_and_seed_csv(db: Session, csv_file_path: str = CSV_PATH) -> int:
    """
    Parses the Maxwell Reserve RPM 2026 CSV file and seeds the database.
    Returns the count of records inserted/updated.
    """
    if db.query(RpmRecord).first() is not None:
        print("[CSV Seeder] RPM records already exist. Skipping seed.")
        return 0

    if not os.path.exists(csv_file_path):
        print(f"[CSV Seeder] File not found at: {csv_file_path}")
        return 0

    records_to_insert: List[dict] = []
    
    # 4 Column blocks: (start_col_index, default_floor)
    column_blocks: List[Tuple[int, str]] = [
        (0, "Floor 1"),
        (5, "Floor 2"),
        (10, "Floor 3"),
        (15, "Floor 4"),
    ]

    with open(csv_file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Header parsing
    property_name = "MAXWELL RESERVE"
    quarter = "2nd Quarter April-June 2026"
    year = 2026

    # Iterate through data rows (skip initial 4 header rows)
    sort_counter = 0
    for row_idx in range(4, len(rows)):
        row = rows[row_idx]
        if not row:
            continue

        # Check for footer/legend markers
        first_cell = row[0].strip() if len(row) > 0 else ""
        if first_cell.upper() in ["LEGEND", "NOT COMPLETE", "COMPLETED"]:
            continue

        for start_col, block_floor in column_blocks:
            if start_col >= len(row):
                continue

            room_raw = row[start_col].strip() if start_col < len(row) else ""
            if not room_raw or room_raw.lower() in ["public area", "room"]:
                continue

            eng_date = row[start_col + 1].strip() if (start_col + 1) < len(row) else ""
            ac_servicing = row[start_col + 2].strip() if (start_col + 2) < len(row) else ""
            housekeeping = row[start_col + 3].strip() if (start_col + 3) < len(row) else ""
            inspection_raw = row[start_col + 4].strip() if (start_col + 4) < len(row) else ""

            # Determine category and floor
            category = "guest_room"
            floor = block_floor

            public_areas = [
                "lobby", "cultivate", "shikar", "polo & isabel", "gym", 
                "zen room", "l1 corridor", "l2 corridor", "l3 corridor", "l4 corridor"
            ]
            if room_raw.lower() in public_areas or "corridor" in room_raw.lower():
                category = "public_area"
                floor = "Public Area"
            elif room_raw.startswith("Room 1"):
                floor = "Floor 1"
            elif room_raw.startswith("Room 2"):
                floor = "Floor 2"
            elif room_raw.startswith("Room 3"):
                floor = "Floor 3"
            elif room_raw.startswith("Room 4"):
                floor = "Floor 4"

            # Normalize inspection status
            inspection_status = "Done" if inspection_raw.strip().lower() == "done" else "Pending"

            sort_counter += 1
            records_to_insert.append({
                "property_name": property_name,
                "year": year,
                "quarter": quarter,
                "floor": floor,
                "category": category,
                "room_or_area": room_raw,
                "eng_date": eng_date if eng_date else None,
                "ac_servicing": ac_servicing if ac_servicing else None,
                "housekeeping": housekeeping if housekeeping else None,
                "inspection_status": inspection_status,
                "sort_order": sort_counter
            })

    def shift_date_str(date_str: str, target_yr: int, q_idx: int) -> str:
        if not date_str or len(date_str) < 10:
            return date_str
        try:
            parts = date_str.split("-")
            if len(parts) != 3:
                return date_str
            _, m_str, d_str = parts
            orig_m = int(m_str)
            shift = {1: -3, 2: 0, 3: 3, 4: 6}.get(q_idx, 0)
            new_m = max(1, min(12, orig_m + shift))
            day = min(int(d_str), 28)
            return f"{target_yr}-{new_m:02d}-{day:02d}"
        except Exception:
            return date_str

    quarter_configs = [
        (1, "1st Quarter Jan-March", 1),
        (2, "2nd Quarter April-June", 2),
        (3, "3rd Quarter July-Sept", 3),
        (4, "4th Quarter Oct-Dec", 4),
    ]

    all_records = []
    years = [2025, 2026, 2027]

    for yr in years:
        for q_num, q_label, q_idx in quarter_configs:
            full_quarter_name = f"{q_label} {yr}" if yr != 2026 or q_num != 2 else quarter
            # Also store with short format compatibility
            for base_rec in records_to_insert:
                copied = dict(base_rec)
                copied["year"] = yr
                copied["quarter"] = full_quarter_name
                
                # Shift dates
                if copied.get("eng_date"):
                    copied["eng_date"] = shift_date_str(copied["eng_date"], yr, q_idx)
                if copied.get("ac_servicing") and "-" in str(copied.get("ac_servicing", "")):
                    copied["ac_servicing"] = shift_date_str(copied["ac_servicing"], yr, q_idx)
                
                # Status variations
                if yr < 2026:
                    copied["inspection_status"] = "Done"
                elif yr == 2026 and q_num == 1:
                    copied["inspection_status"] = "Done" if (copied["sort_order"] % 3 != 0) else "Pending"
                elif yr == 2026 and q_num == 2:
                    copied["inspection_status"] = base_rec["inspection_status"]
                else:
                    copied["inspection_status"] = "Pending"

                all_records.append(copied)

    # Clear existing RPM records
    db.query(RpmRecord).delete()

    for item in all_records:
        db_record = RpmRecord(**item)
        db.add(db_record)

    db.commit()
    print(f"[CSV Seeder] Successfully seeded {len(all_records)} RPM records across multiple quarters and years.")
    return len(all_records)


def seed_default_users(db: Session) -> None:
    """Seed default demo users (Inspector, Supervisor, Admin) if not exist."""
    demo_users = [
        {
            "email": "inspector@maxwell.com",
            "full_name": "John Tan (Inspector)",
            "role": "inspector",
            "hashed_password": "hashed_default_password_123"
        },
        {
            "email": "supervisor@maxwell.com",
            "full_name": "Sarah Lee (Supervisor)",
            "role": "supervisor",
            "hashed_password": "hashed_default_password_123"
        },
        {
            "email": "admin@maxwell.com",
            "full_name": "Admin Officer",
            "role": "admin",
            "hashed_password": "hashed_default_password_123"
        }
    ]

    for u in demo_users:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if not existing:
            db.add(User(**u))
    db.commit()
