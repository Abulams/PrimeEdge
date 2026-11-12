"""
Subscription Access Control Middleware
======================================
Middleware to check user subscription tier and feature access.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .auth import get_current_user
from .stripe_service import StripeService


def require_premium_tier(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dependency to require Premium tier for auto-execution features.
    Raises HTTPException if user doesn't have Premium access.
    """
    has_access = StripeService.check_auto_execution_access(db, current_user.id)
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-execution requires Premium subscription. Please upgrade your plan."
        )
    
    return current_user


def require_api_access(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dependency to require API access (Pro or Premium tier).
    """
    tier_info = StripeService.get_user_tier_info(db, current_user.id)
    
    if not tier_info or not tier_info.get("api_access_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access requires Pro or Premium subscription."
        )
    
    return current_user


def check_account_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user has reached their cTrader account limit based on tier.
    """
    tier_info = StripeService.get_user_tier_info(db, current_user.id)
    
    if not tier_info:
        # Free tier - 1 account limit
        max_accounts = 1
    else:
        max_accounts = tier_info.get("max_accounts", 1)
    
    # Count user's active accounts
    from .models import UserBrokerAccount
    account_count = db.query(UserBrokerAccount).filter(
        UserBrokerAccount.user_id == current_user.id,
        UserBrokerAccount.is_active == True
    ).count()
    
    if account_count >= max_accounts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account limit reached. Your current plan allows {max_accounts} cTrader account(s)."
        )
    
    return current_user