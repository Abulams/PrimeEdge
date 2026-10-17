"""
Subscription Management Router
================================
Handles subscription checkout, management, and tier information endpoints.
"""
import os
import logging
from typing import List, Optional
import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, SubscriptionTier, UserSubscription
from ..auth import get_current_user
from ..stripe_service import StripeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/subscription", tags=["Subscription Management"])


# --- Schemas ---

class TierInfo(BaseModel):
    tier_id: int
    name: str
    display_name: str
    description: str
    price_monthly: float
    price_yearly: Optional[float]
    features: List[str]
    max_accounts: int
    auto_execution_enabled: bool
    api_access_enabled: bool


class CheckoutRequest(BaseModel):
    tier_name: str  # "starter", "pro", "premium"
    billing_interval: str = "month"  # "month" or "year"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    customer_id: str


class UserSubscriptionInfo(BaseModel):
    tier: Optional[TierInfo]
    status: str
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    trial_used: bool


# --- Endpoints ---

@router.get("/tiers", response_model=List[TierInfo])
def get_available_tiers(db: Session = Depends(get_db)):
    """Get all available subscription tiers."""
    tiers = db.query(SubscriptionTier).filter(SubscriptionTier.active == True).all()
    
    return [
        TierInfo(
            tier_id=tier.id,
            name=tier.name,
            display_name=tier.display_name,
            description=tier.description,
            price_monthly=tier.price_monthly,
            price_yearly=tier.price_yearly,
            features=tier.features or [],
            max_accounts=tier.max_accounts,
            auto_execution_enabled=tier.auto_execution_enabled,
            api_access_enabled=tier.api_access_enabled
        )
        for tier in tiers
    ]


@router.get("/current", response_model=UserSubscriptionInfo)
def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription information."""
    tier_info = StripeService.get_user_tier_info(db, current_user.id)
    
    # Get active subscription
    active_sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).first()
    
    return UserSubscriptionInfo(
        tier=tier_info,
        status=active_sub.status if active_sub else "none",
        current_period_end=active_sub.current_period_end.isoformat() if active_sub and active_sub.current_period_end else None,
        cancel_at_period_end=active_sub.cancel_at_period_end if active_sub else False,
        trial_used=current_user.trial_used
    )


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    req: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe checkout session for subscription purchase."""
    try:
        result = StripeService.create_checkout_session(
            db=db,
            user_id=current_user.id,
            tier_name=req.tier_name,
            billing_interval=req.billing_interval
        )
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel user's subscription at the end of current billing period."""
    active_sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).first()
    
    if not active_sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    try:
        # Cancel in Stripe
        if active_sub.stripe_subscription_id:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            stripe.Subscription.modify(
                active_sub.stripe_subscription_id,
                cancel_at_period_end=True
            )
            active_sub.cancel_at_period_end = True
            db.commit()
        
        return {"status": "success", "message": "Subscription will be canceled at period end"}
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.get("/webhook-config")
def get_webhook_config(current_user: User = Depends(get_current_user)):
    """Get Stripe webhook configuration for frontend (test mode only)."""
    if os.getenv("STRIPE_MODE") == "live":
        raise HTTPException(status_code=403, detail="Webhook config not available in live mode")
    
    return {
        "stripe_publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY"),
        "stripe_mode": os.getenv("STRIPE_MODE", "test")
    }


@router.post("/webhook")
async def handle_stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events.
    This endpoint should be configured in Stripe Dashboard as the webhook URL.
    """
    # Get raw body bytes for HMAC signature verification
    body = await request.body()
    
    # Get Stripe signature
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    try:
        StripeService.handle_webhook_event(db, body, sig_header)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")