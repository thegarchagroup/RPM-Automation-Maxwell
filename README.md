# Maxwell Routine Preventive Maintenance (RPM) Backend

A modular FastAPI backend providing database storage, CSV data seeding, dashboard statistics, floor matrix views, and inspection checklists for The Maxwell Reserve.

## Architecture

```
backend/
├── app/
│   ├── main.py                  # FastAPI app & lifespan auto-seeder
│   ├── config.py                # App & DB configurations
│   ├── db.py                    # SQLAlchemy engine & session dependency
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── rpm.py               # RpmRecord (RPM tracking & inspection status)
│   │   ├── user.py              # User authentication model
│   │   ├── template.py          # Template, Section, ChecklistItem models
│   │   └── inspection.py        # Inspection & InspectionItem models
│   ├── schemas/                 # Pydantic v2 schemas
│   │   ├── rpm.py               # Request/Response models & DashboardStats
│   │   ├── user.py              # User & Token schemas
│   │   ├── template.py          # Template & Checklist schemas
│   │   └── inspection.py        # Inspection schemas
│   ├── routers/                 # API route controllers
│   │   ├── rpm.py               # /api/rpm (stats, matrix, records CRUD, seed)
│   │   ├── auth.py              # /api/auth (login, current user)
│   │   ├── templates.py         # /api/templates (Maxwell inspection checklist)
│   │   └── inspections.py       # /api/inspections (save/submit inspections)
│   └── services/                # Business logic & CSV parser
│       ├── csv_seeder.py        # Maxwell Reserve RPM 2026 CSV parser & seeder
│       └── template_seeder.py   # Maxwell Sections A-K checklist seeder
├── data/
│   └── maxwell_reserve_rpm_2026.csv   # Raw CSV data file
├── requirements.txt
└── pyproject.toml
```

## Running the Backend

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Interactive API Documentation
Open your browser to:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Key Endpoints

- `GET /api/rpm/dashboard-stats` — Aggregated completion rates, floor-wise progress, total units.
- `GET /api/rpm/matrix` — Multi-floor matrix structure matching the original sheet.
- `GET /api/rpm/records` — Filterable list of all RPM records (by floor, status, search).
- `PUT /api/rpm/records/{id}` — Update inspection status, ENG dates, AC servicing notes.
- `POST /api/rpm/seed` — Re-parse and re-seed the CSV data into the database.
- `GET /api/templates/maxwell` — Complete Maxwell checklist template (Sections A to K).
- `POST /api/inspections` — Submit official inspection report.
