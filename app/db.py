from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configure connect args and pooling options
connect_args = {}
engine_kwargs = {
    "echo": False
}

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Neon / PostgreSQL serverless pooling resilience:
    # pool_pre_ping detects stale/dropped connections and automatically reconnects
    # pool_recycle prevents connections from exceeding Neon's idle timeout
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
    })
    # Remove channel_binding if present as Neon PgBouncer pooler terminates TLS and triggers EOF
    if "channel_binding=" in db_url:
        db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?").replace("?channel_binding=require", "")

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
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
                if "defects_status" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN defects_status VARCHAR(50) DEFAULT 'open'"))
                if "defects_completed_at" not in existing_cols:
                    conn.execute(text("ALTER TABLE inspections ADD COLUMN defects_completed_at TIMESTAMP"))

        if "inspection_items" in inspector.get_table_names():
            item_cols = {c["name"] for c in inspector.get_columns("inspection_items")}
            with engine.begin() as conn:
                if "inspector_remark" not in item_cols:
                    conn.execute(text("ALTER TABLE inspection_items ADD COLUMN inspector_remark TEXT"))
                if "is_fixed" not in item_cols:
                    conn.execute(text("ALTER TABLE inspection_items ADD COLUMN is_fixed BOOLEAN DEFAULT FALSE"))
                if "fixed_at" not in item_cols:
                    conn.execute(text("ALTER TABLE inspection_items ADD COLUMN fixed_at TIMESTAMP"))
                if "fixed_by" not in item_cols:
                    conn.execute(text("ALTER TABLE inspection_items ADD COLUMN fixed_by VARCHAR(255)"))
                if "fixed_remark" not in item_cols:
                    conn.execute(text("ALTER TABLE inspection_items ADD COLUMN fixed_remark TEXT"))

        if "rpm_records" in inspector.get_table_names():
            rpm_cols = {c["name"] for c in inspector.get_columns("rpm_records")}
            with engine.begin() as conn:
                if "rpm_date" not in rpm_cols:
                    conn.execute(text("ALTER TABLE rpm_records ADD COLUMN rpm_date VARCHAR(50)"))
                if "maintenance_carried_by" not in rpm_cols:
                    conn.execute(text("ALTER TABLE rpm_records ADD COLUMN maintenance_carried_by VARCHAR(255)"))
                if "inspected_by" not in rpm_cols:
                    conn.execute(text("ALTER TABLE rpm_records ADD COLUMN inspected_by VARCHAR(255)"))
                # Backfill submitters from inspections if available
                if "inspections" in inspector.get_table_names():
                    conn.execute(text("""
                        UPDATE rpm_records r
                        SET 
                            maintenance_carried_by = COALESCE(r.maintenance_carried_by, i.maintenance_carried_by),
                            inspected_by = COALESCE(r.inspected_by, i.inspected_by)
                        FROM inspections i
                        WHERE LOWER(TRIM(REPLACE(r.room_or_area, 'Room', ''))) = LOWER(TRIM(REPLACE(i.room_number, 'Room', '')))
                          AND (r.maintenance_carried_by IS NULL OR r.inspected_by IS NULL)
                    """))
    except Exception as e:
        print(f"[Warning] Failed to sync table columns: {e}")

