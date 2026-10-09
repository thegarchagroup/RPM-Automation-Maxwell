from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserResponse, Token, UserCreate, UserUpdate
from app.services.user_seeder import seed_default_users
from app.services.security import verify_password, hash_password

from sqlalchemy import func

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user with email or role and verify bcrypt password from user database."""
    # Ensure default users and passwords exist in database if fresh
    seed_default_users(db)

    user = None
    role_input = (login_data.role or "").strip().lower()
    email_input = (login_data.email or "").strip().lower()
    provided_password = (login_data.password or "").strip()

    if not provided_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required."
        )

    norm_role = None
    if role_input in ["rpm", "rpm technician", "rpm user", "rpm technicial"]:
        norm_role = "rpm"
    elif role_input in ["inspector", "john tan", "john tan (inspector)"]:
        norm_role = "inspector"
    elif role_input in ["admin", "maxwell admin"]:
        norm_role = "admin"
    elif role_input:
        norm_role = role_input

    # 1. If email is provided, look up specifically by email
    if email_input:
        candidate = db.query(User).filter(func.lower(User.email) == email_input).first()
        if candidate:
            if not candidate.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive. Please contact administration."
                )
            if not verify_password(provided_password, candidate.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid password for this account."
                )
            user = candidate

    # 2. If no email or not matched yet, check all active users with this role in DB
    if not user and norm_role:
        role_candidates = db.query(User).filter(User.role == norm_role, User.is_active == True).all()
        for candidate in role_candidates:
            if verify_password(provided_password, candidate.hashed_password):
                user = candidate
                break

    # 3. If still not found and no specific email was entered, search across all active users in DB
    if not user and not email_input:
        all_candidates = db.query(User).filter(User.is_active == True).all()
        for candidate in all_candidates:
            if verify_password(provided_password, candidate.hashed_password):
                user = candidate
                break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your role, email, and password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administration."
        )

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
    """Create a new user with bcrypt password hashing (Admin only)."""
    email = data.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=email,
        full_name=data.full_name.strip(),
        role=data.role.strip().lower(),
        hashed_password=hash_password(data.password),
        is_active=data.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    """Update user details (Admin only: name, role, email, status, password)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.email is not None:
        email = data.email.strip().lower()
        if email != user.email:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email is already used by another account")
            user.email = email

    if data.full_name is not None:
        user.full_name = data.full_name.strip()

    if data.role is not None:
        user.role = data.role.strip().lower()

    if data.is_active is not None:
        user.is_active = data.is_active

    if data.password is not None and data.password.strip():
        user.hashed_password = hash_password(data.password.strip())

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user account (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety check: prevent deleting main admin account
    if user.email == "admin@maxwell.com":
        raise HTTPException(status_code=400, detail="Cannot delete default admin account")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.full_name} ({user.email}) deleted successfully"}
