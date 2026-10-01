from sqlalchemy.orm import Session
from app.models.user import User


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
