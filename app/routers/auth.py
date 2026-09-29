from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserResponse, Token
from app.services.csv_seeder import seed_default_users

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user with email and return token."""
    email = login_data.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Seed demo users if missing
        seed_default_users(db)
        user = db.query(User).filter(User.email == email).first()

    if not user:
        # Auto-create user for demo convenience
        role = "supervisor" if "supervisor" in email else ("admin" if "admin" in email else "inspector")
        name = email.split("@")[0].replace(".", " ").title() + f" ({role.title()})"
        user = User(
            email=email,
            full_name=name,
            role=role,
            hashed_password="demo_password_hash"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = f"jwt_mock_token_for_{user.email}_{user.role}"
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(email: str = "inspector@maxwell.com", db: Session = Depends(get_db)):
    """Fetch current user details."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        seed_default_users(db)
        user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
