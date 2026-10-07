from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configure connect args for SQLite if used
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sync_table_columns():
    """Ensure missing columns in existing tables are added if schema changed without alembic."""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "inspections" in inspector.get_table_names():
            existing_cols = {c["name"] for c in inspector.get_columns("inspections")}
            with engine.begin() as conn:
                if "property_name" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN property_name VARCHAR(100) DEFAULT 'Maxwell'"))
                if "quarter" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN quarter VARCHAR(100)"))
                if "inspected_by_signature_url" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN inspected_by_signature_url TEXT"))
                if "inspector_remark" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN inspector_remark TEXT"))
                if "verified_at" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN verified_at TIMESTAMP"))

        if "inspection_items" in inspector.get_table_names():
            item_cols = {c["name"] for c in inspector.get_columns("inspection_items")}
            with engine.begin() as conn:
                if "inspector_remark" not in item_cols:
                    conn.execute(text("ALTER TABLE inspection_items ADD COLUMN inspector_remark TEXT"))

        if "rpm_records" in inspector.get_table_names():
            rpm_cols = {c["name"] for c in inspector.get_columns("rpm_records")}
            with engine.begin() as conn:
                if "rpm_date" not in rpm_cols:
                    conn.execute(text("ALTER TABLE rpm_records ADD COLUMN rpm_date VARCHAR(50)"))
    except Exception as e:
        print(f"[Warning] Failed to sync table columns: {e}")

