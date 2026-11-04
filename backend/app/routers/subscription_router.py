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
    price_monthly_ngn: Optional[float] = 0.0
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
            price_monthly_ngn=getattr(tier, "price_monthly_ngn", 0.0) or 0.0,
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


# --- Paystack Routes ---

class PaystackCheckoutResponse(BaseModel):
    checkout_url: str
    access_code: Optional[str] = None
    reference: Optional[str] = None


@router.get("/paystack/config")
def get_paystack_config():
    """Get Paystack public configuration for frontend checkout."""
    from ..paystack_service import PaystackService
    return PaystackService.get_public_config()


@router.post("/paystack/checkout", response_model=PaystackCheckoutResponse)
def create_paystack_checkout(
    req: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Paystack checkout session for NGN card or bank payments."""
    from ..paystack_service import PaystackService
    try:
        session = PaystackService.create_checkout_session(
            db=db,
            user_id=current_user.id,
            tier_name=req.tier_name,
            billing_interval=req.billing_interval
        )
        return PaystackCheckoutResponse(
            checkout_url=session["checkout_url"],
            access_code=session.get("access_code"),
            reference=session.get("reference")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating Paystack checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/paystack/verify/{reference}")
def verify_paystack_payment(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify a Paystack transaction and activate subscription immediately."""
    from ..paystack_service import PaystackService
    try:
        result = PaystackService.verify_transaction(db, reference)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying Paystack payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify payment")


@router.post("/paystack-webhook")
async def handle_paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming Paystack webhook events.
    Verifies HMAC SHA512 signature in x-paystack-signature.
    """
    from ..paystack_service import PaystackService
    body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing x-paystack-signature header")
    try:
        PaystackService.handle_webhook_event(db, body, signature)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Paystack webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# --- Flutterwave Routes (USD / Global) ---

class FlutterwaveCheckoutRequest(BaseModel):
    tier_name: str
    billing_interval: str = "month"
    currency: str = "USD"


class FlutterwaveCheckoutResponse(BaseModel):
    checkout_url: str
    reference: str


@router.get("/flutterwave/config")
def get_flutterwave_config():
    """Get Flutterwave public configuration for frontend checkout."""
    from ..flutterwave_service import FlutterwaveService
    return FlutterwaveService.get_public_config()


@router.post("/flutterwave/checkout", response_model=FlutterwaveCheckoutResponse)
def create_flutterwave_checkout(
    req: FlutterwaveCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Flutterwave checkout session for USD / international cards."""
    from ..flutterwave_service import FlutterwaveService
    try:
        session = FlutterwaveService.create_checkout_session(
            db=db,
            user_id=current_user.id,
            tier_name=req.tier_name,
            billing_interval=req.billing_interval,
            currency=req.currency
        )
        return FlutterwaveCheckoutResponse(
            checkout_url=session["checkout_url"],
            reference=session["reference"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating Flutterwave checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Flutterwave checkout session")


@router.get("/flutterwave/verify/{reference}")
def verify_flutterwave_payment(
    reference: str,
    transaction_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify a Flutterwave transaction and activate subscription immediately."""
    from ..flutterwave_service import FlutterwaveService
    try:
        result = FlutterwaveService.verify_transaction(db, reference=reference, transaction_id=transaction_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying Flutterwave payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify payment")


@router.post("/flutterwave-webhook")
async def handle_flutterwave_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming Flutterwave webhook events.
    Verifies verif-hash header against secret hash.
    """
    from ..flutterwave_service import FlutterwaveService
    body = await request.body()
    signature = request.headers.get("verif-hash")
    try:
        FlutterwaveService.handle_webhook_event(db, body, signature or "")
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Flutterwave webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
