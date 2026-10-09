import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.template import Template, Section, ChecklistItem

JSON_PATH = Path(__file__).resolve().parent.parent.parent / "Maxwell_Inspection_List.json"


def load_maxwell_sections_data():
    if JSON_PATH.exists():
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sections", [])
        except Exception as e:
            print(f"[Template Seeder] Error reading {JSON_PATH}: {e}")
    return []


MAXWELL_SECTIONS_DATA = load_maxwell_sections_data()


def seed_maxwell_template(db: Session) -> Template:
    """Seed Maxwell template and sections into database if not present."""
    existing = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if existing:
        return existing

    template = Template(
        property_name="The Maxwell",
        title="MAXWELL INSPECTION LIST",
        header_fields=["Type", "Room"],
        footer_fields=["Date", "Inspected By", "Verified By"],
        version=1,
        is_active=True
    )
    db.add(template)
    db.flush()

    sections_data = MAXWELL_SECTIONS_DATA or load_maxwell_sections_data()
    for sec_idx, sec_data in enumerate(sections_data):
        section = Section(
            template_id=template.id,
            code=sec_data["code"],
            title=sec_data["title"],
            sort_order=sec_idx + 1
        )
        db.add(section)
        db.flush()

        for item_data in sec_data.get("items", []):
            item = ChecklistItem(
                section_id=section.id,
                item_no=item_data["item_no"],
                description=item_data["description"],
                sort_order=item_data.get("sort_order", item_data["item_no"])
            )
            db.add(item)

    db.commit()
    print(f"[Template Seeder] Seeded Maxwell template with {len(sections_data)} sections.")
    return template
