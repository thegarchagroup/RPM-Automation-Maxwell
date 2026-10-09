import os
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.security import hash_password


def seed_default_users(db: Session) -> None:
    """
    Ensures default initial users exist if database is completely empty.
    Passwords are read from environment variables, securely hashed with bcrypt, and never hardcoded in git.
    In deployment/production, existing database users are left untouched.
    """
    if db.query(User).first():
        # Users already exist in database; no seeding needed
        return

    rpm_raw_pw = os.getenv("DEFAULT_RPM_PASSWORD", "")
    inspector_raw_pw = os.getenv("DEFAULT_INSPECTOR_PASSWORD", "")
    admin_raw_pw = os.getenv("DEFAULT_ADMIN_PASSWORD", "")

    default_users = [
        {
            "email": os.getenv("DEFAULT_RPM_EMAIL", "rpm@maxwell.com"),
            "full_name": "RPM Technician",
            "role": "rpm",
            "hashed_password": hash_password(rpm_raw_pw) if rpm_raw_pw else "",
            "is_active": True,
        },
        {
            "email": os.getenv("DEFAULT_INSPECTOR_EMAIL", "inspector@maxwell.com"),
            "full_name": "Inspector",
            "role": "inspector",
            "hashed_password": hash_password(inspector_raw_pw) if inspector_raw_pw else "",
            "is_active": True,
        },
        {
            "email": os.getenv("DEFAULT_ADMIN_EMAIL", "admin@maxwell.com"),
            "full_name": "Maxwell Admin",
            "role": "admin",
            "hashed_password": hash_password(admin_raw_pw) if admin_raw_pw else "",
            "is_active": True,
        }
    ]

    for u in default_users:
        if u["hashed_password"]:
            db.add(User(**u))
    db.commit()
