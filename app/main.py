from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import engine, Base, SessionLocal
from app.services.csv_seeder import parse_and_seed_csv, seed_default_users
from app.services.template_seeder import seed_maxwell_template
from app.routers import rpm_router, auth_router, templates_router, inspections_router, dropbox_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB Tables
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed initial datasets into database
    db = SessionLocal()
    try:
        seed_default_users(db)
        seed_maxwell_template(db)
        parse_and_seed_csv(db)
    finally:
        db.close()
    
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for The Maxwell Room Preventive Maintenance (RPM) & Inspection Checklist System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(rpm_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(templates_router, prefix=settings.API_V1_STR)
app.include_router(inspections_router, prefix=settings.API_V1_STR)
app.include_router(dropbox_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": "The Maxwell Room Preventive Maintenance API",
        "docs_url": "/docs",
        "version": "1.0.0"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Maxwell RPM Inspection Backend"
    }


def start():
    """Run via uvicorn programmatically."""
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
