from sqlalchemy.orm import Session
from app.models.template import Template, Section, ChecklistItem

MAXWELL_SECTIONS_DATA = [
    {
        "code": "A",
        "title": "MAIN ENTRANCE DOOR",
        "items": [
            {"item_no": 1, "description": "Door lock & handle"},
            {"item_no": 2, "description": "Door closer & hinges"},
            {"item_no": 3, "description": "Door frame & stopper"},
            {"item_no": 4, "description": "Eye viewer & door chain"},
            {"item_no": 5, "description": "Door bell / Chime"},
            {"item_no": 6, "description": "DND / Make up room indicator"},
        ],
    },
    {
        "code": "B",
        "title": "FOYER / ENTRY WAY",
        "items": [
            {"item_no": 1, "description": "Master switch / Key card slot"},
            {"item_no": 2, "description": "Ceiling downlight & switches"},
            {"item_no": 3, "description": "Flooring & skirting"},
            {"item_no": 4, "description": "Wardrobe door & internal light"},
            {"item_no": 5, "description": "Safety deposit box"},
            {"item_no": 6, "description": "Iron & ironing board / Torchlight"},
        ],
    },
    {
        "code": "C",
        "title": "BATHROOM - GENERAL & VANITY",
        "items": [
            {"item_no": 1, "description": "Bathroom door & lock"},
            {"item_no": 2, "description": "Vanity mirror & demister / Lighting"},
            {"item_no": 3, "description": "Basin, mixer tap & pop-up waste"},
            {"item_no": 4, "description": "Under-basin bottle trap & angle valves (no leaks)"},
            {"item_no": 5, "description": "Shaver socket & hair dryer"},
            {"item_no": 6, "description": "Silicone sealant & grout condition"},
        ],
    },
    {
        "code": "D",
        "title": "BATHROOM - SHOWER & WATER CLOSET (WC)",
        "items": [
            {"item_no": 1, "description": "Shower door, seal & hinges"},
            {"item_no": 2, "description": "Overhead rain shower & hand shower"},
            {"item_no": 3, "description": "Thermostatic mixer valve / Hot water temp"},
            {"item_no": 4, "description": "Shower drain / Floor trap (drainage flow)"},
            {"item_no": 5, "description": "WC bowl, seat & cover"},
            {"item_no": 6, "description": "WC flush valve / Cistern mechanism & bidet spray"},
            {"item_no": 7, "description": "Exhaust fan ventilation"},
        ],
    },
    {
        "code": "E",
        "title": "BEDROOM AREA",
        "items": [
            {"item_no": 1, "description": "Headboard & reading lights"},
            {"item_no": 2, "description": "Bedside tables & USB / Power sockets"},
            {"item_no": 3, "description": "Bed base, mattress & castor wheels"},
            {"item_no": 4, "description": "Carpet / Timber flooring condition"},
            {"item_no": 5, "description": "Walls, wallpaper & ceiling condition"},
            {"item_no": 6, "description": "Luggage rack & wardrobe drawers"},
        ],
    },
    {
        "code": "F",
        "title": "AIR CONDITIONING & VENTILATION (FCU)",
        "items": [
            {"item_no": 1, "description": "Digital thermostat / Room temperature sensor"},
            {"item_no": 2, "description": "FCU cooling performance / Airflow"},
            {"item_no": 3, "description": "Supply & return air grilles (cleanliness)"},
            {"item_no": 4, "description": "Condensate drain pan & pipe (no blockage)"},
            {"item_no": 5, "description": "Fan motor & blower noise level"},
        ],
    },
    {
        "code": "G",
        "title": "LIGHTING & ELECTRICAL FIXTURES",
        "items": [
            {"item_no": 1, "description": "All ceiling downlights & cove lights"},
            {"item_no": 2, "description": "Desk lamp & standing floor lamp"},
            {"item_no": 3, "description": "Dimmer controls & scene switches"},
            {"item_no": 4, "description": "All power sockets & USB charging points"},
            {"item_no": 5, "description": "DB box (circuit breakers & ELCD test)"},
        ],
    },
    {
        "code": "H",
        "title": "TELEVISION & AUDIO VISUAL",
        "items": [
            {"item_no": 1, "description": "Smart TV mounting bracket & cables"},
            {"item_no": 2, "description": "TV display & audio channels"},
            {"item_no": 3, "description": "Remote control & batteries"},
            {"item_no": 4, "description": "Telephone unit & dial tone"},
            {"item_no": 5, "description": "Bluetooth speaker / Alarm clock"},
        ],
    },
    {
        "code": "I",
        "title": "MINI BAR & BEVERAGE STATION",
        "items": [
            {"item_no": 1, "description": "Mini fridge temperature & door gasket"},
            {"item_no": 2, "description": "Electric kettle / Coffee machine operation"},
            {"item_no": 3, "description": "Cabinet door hinges & pull-out tray"},
        ],
    },
    {
        "code": "J",
        "title": "WINDOWS & CURTAINS",
        "items": [
            {"item_no": 1, "description": "Window glass, latch & safety restrictor"},
            {"item_no": 2, "description": "Day sheer curtain & track glide"},
            {"item_no": 3, "description": "Night blackout curtain & track / Motor"},
        ],
    },
    {
        "code": "K",
        "title": "FURNITURE & GENERAL FIXTURES",
        "items": [
            {"item_no": 1, "description": "Work desk & armchair / Sofa"},
            {"item_no": 2, "description": "Coffee table & side tables"},
            {"item_no": 3, "description": "Wall artwork, mirrors & frames"},
            {"item_no": 4, "description": "Smoke detector & fire sprinkler head"},
        ],
    },
]


def seed_maxwell_template(db: Session) -> Template:
    """Seed Maxwell template and sections into database if not present."""
    existing = db.query(Template).filter(Template.property_name == "The Maxwell").first()
    if existing:
        return existing

    template = Template(
        property_name="The Maxwell",
        title="ROOM PREVENTIVE MAINTENANCE",
        header_fields=["Type", "Room"],
        footer_fields=["Date", "Maintenance carried By", "Inspected By"],
        version=1,
        is_active=True
    )
    db.add(template)
    db.flush()

    for sec_idx, sec_data in enumerate(MAXWELL_SECTIONS_DATA):
        section = Section(
            template_id=template.id,
            code=sec_data["code"],
            title=sec_data["title"],
            sort_order=sec_idx + 1
        )
        db.add(section)
        db.flush()

        for item_data in sec_data["items"]:
            item = ChecklistItem(
                section_id=section.id,
                item_no=item_data["item_no"],
                description=item_data["description"],
                sort_order=item_data["item_no"]
            )
            db.add(item)

    db.commit()
    print(f"[Template Seeder] Seeded Maxwell template with {len(MAXWELL_SECTIONS_DATA)} sections.")
    return template
