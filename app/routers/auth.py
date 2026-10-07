from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserResponse, Token, UserCreate
from app.services.user_seeder import seed_default_users

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
        role = "rpm" if "rpm" in email else ("admin" if "admin" in email else "inspector")
        name = email.split("@")[0].replace(".", " ").title() + f" ({role.upper()})"
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
def get_current_user(email: str = "rpm@maxwell.com", db: Session = Depends(get_db)):
    """Fetch current user details."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        seed_default_users(db)
        user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """List all registered users (for Admin user management)."""
    seed_default_users(db)
    users = db.query(User).order_by(User.id.asc()).all()
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (Admin only)."""
    email = data.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=email,
        full_name=data.full_name.strip(),
        role=data.role.strip().lower(),
        hashed_password=f"hash_{data.password}",
        is_active=data.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
