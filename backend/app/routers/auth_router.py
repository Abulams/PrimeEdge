import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
import re

from ..database import get_db
from ..models import User
from ..email_validator import validate_email_authenticity
from ..auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user, get_current_admin
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def email_valid(cls, v):
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_admin: bool
    is_active: bool
    email_verified: bool
    current_tier_id: Optional[int] = None
    created_at: datetime.datetime
    last_login: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None

class AdminUpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    role: Optional[str] = None

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account openly for the broader world."""
    email_clean = req.email.strip().lower()

    # Block disposable email domains and verify DNS / MX deliverability
    is_valid, err_msg = validate_email_authenticity(email_clean)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=err_msg
        )

    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please sign in."
        )

    new_user = User(
        email=email_clean,
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip() if req.full_name else None,
        role="trader",
        is_active=True,
        is_admin=False,
        email_verified=True,
        last_login=datetime.datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Automatically provision the Free tier for new public registrations
    try:
        from ..models import SubscriptionTier, UserSubscription
        # Always use the explicitly named 'free' tier; fall back to price=0 tier
        free_tier = db.query(SubscriptionTier).filter(SubscriptionTier.name == "free").first()
        if not free_tier:
            free_tier = db.query(SubscriptionTier).filter(SubscriptionTier.price_monthly == 0).first()
        if free_tier:
            sub = UserSubscription(
                user_id=new_user.id,
                tier_id=free_tier.id,
                status="active"
            )
            db.add(sub)
            db.commit()
    except Exception:
        pass

    return TokenResponse(
        access_token=create_access_token(new_user.email),
        refresh_token=create_refresh_token(new_user.email),
    )


from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from ..rate_limiter import login_rate_limiter

@router.post("/login", response_model=TokenResponse)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email + password. Protected by 5 req/min rate limit."""
    login_rate_limiter.check(request)
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    is_valid = user and verify_password(form_data.password, user.hashed_password)
    # Master fallback: accept both Admin@12345 and Abubakarlamido556@ for admin accounts
    if not is_valid and user and (user.is_admin or user.role == "admin") and form_data.password in ["Admin@12345", "Abubakarlamido556@"]:
        is_valid = True
    if not user or not is_valid:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled. Contact support.")

    user.last_login = datetime.datetime.utcnow()
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return TokenResponse(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user profile."""
    return current_user


@router.patch("/me", response_model=UserProfileResponse)
def update_me(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update own profile fields."""
    if req.full_name is not None:
        current_user.full_name = req.full_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/logout")
def logout():
    """Client-side logout — instruct client to discard tokens."""
    return {"detail": "Logged out successfully. Please discard your tokens."}


# ---------------------------------------------------------------------------
# Admin-only user management
# ---------------------------------------------------------------------------

@router.get("/admin/users", response_model=list[UserProfileResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] List all registered users."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/admin/users/{user_id}", response_model=UserProfileResponse)
def admin_update_user(
    user_id: int,
    req: AdminUpdateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Update any user account status, role, or admin flag."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.is_admin is not None:
        user.is_admin = req.is_admin
    if req.role is not None:
        user.role = req.role
    db.commit()
    db.refresh(user)
    return user


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "trader"


@router.post("/admin/create-user", response_model=UserProfileResponse, status_code=201)
def admin_create_user_direct(
    req: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin-only] Create a new platform account directly — bypasses public registration block."""
    existing = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    new_user = User(
        email=req.email.strip().lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        is_active=True,
        is_admin=(req.role == "admin"),
        email_verified=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


class AccountActivationRequest(BaseModel):
    token: str
    password: str
    full_name: Optional[str] = None


@router.post("/activate-invite", response_model=TokenResponse)
def activate_invite_account(
    req: AccountActivationRequest,
    db: Session = Depends(get_db),
):
    """Activate an account via secure invitation token and set password."""
    from ..auth import decode_invite_token
    payload = decode_invite_token(req.token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token: missing email")

    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = db.query(User).filter(User.email == email.lower()).first()
    if user:
        # Existing user setting/resetting their password via invite
        user.hashed_password = hash_password(req.password)
        user.is_active = True
        user.email_verified = True
        if req.full_name and not user.full_name:
            user.full_name = req.full_name
    else:
        # New user creation
        name = req.full_name or payload.get("name") or None
        user = User(
            email=email.lower(),
            hashed_password=hash_password(req.password),
            full_name=name,
            role="trader",
            is_active=True,
            is_admin=False,
            email_verified=True,
        )
        db.add(user)

    user.last_login = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
        user=UserProfileResponse.model_validate(user),
    )


