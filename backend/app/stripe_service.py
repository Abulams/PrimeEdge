"""
Stripe Payment Integration Service
==================================
Handles Stripe API interactions for subscription management, checkout sessions, and webhooks.
"""
import os
import datetime
import logging
from typing import Optional, Dict, Any
import stripe
from sqlalchemy.orm import Session

from .models import User, SubscriptionTier, UserSubscription, StripeWebhookEvent
from .database import get_db

logger = logging.getLogger(__name__)

# Initialize Stripe with secret key from environment
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


class StripeService:
    """Service for Stripe payment operations."""

    @staticmethod
    def get_stripe_mode() -> str:
        """Returns current Stripe mode (test or live)."""
        return os.getenv("STRIPE_MODE", "test")

    @staticmethod
    def initialize_default_tiers(db: Session) -> None:
        """Initialize default subscription tiers if they don't exist."""
        existing_tiers = db.query(SubscriptionTier).count()
        if existing_tiers > 0:
            logger.info(f"Found {existing_tiers} existing tiers, skipping initialization")
            return

        tiers = [
            {
                "name": "starter",
                "display_name": "Starter",
                "description": "Essential market intelligence for manual traders",
                "price_monthly": 29.0,
                "price_yearly": 290.0,
                "features": [
                    "Real-time market signals",
                    "Basic opportunity radar",
                    "Manual trade journaling",
                    "1 MT5 account",
                    "Community access"
                ],
                "max_accounts": 1,
                "auto_execution_enabled": False,
                "api_access_enabled": False
            },
            {
                "name": "pro",
                "display_name": "Pro",
                "description": "Advanced tools for serious systematic traders",
                "price_monthly": 99.0,
                "price_yearly": 990.0,
                "features": [
                    "All Starter features",
                    "Advanced market analysis",
                    "Historical performance analytics",
                    "3 MT5 accounts",
                    "Priority support",
                    "API access (read-only)"
                ],
                "max_accounts": 3,
                "auto_execution_enabled": False,
                "api_access_enabled": True
            },
            {
                "name": "premium",
                "display_name": "Premium",
                "description": "Full institutional-grade platform with auto-execution",
                "price_monthly": 299.0,
                "price_yearly": 2990.0,
                "features": [
                    "All Pro features",
                    "Fully automated execution",
                    "Unlimited MT5 accounts",
                    "Custom strategy backtesting",
                    "Dedicated support",
                    "Full API access (read/write)",
                    "White-label reporting"
                ],
                "max_accounts": 999,
                "auto_execution_enabled": True,
                "api_access_enabled": True
            }
        ]

        for tier_data in tiers:
            tier = SubscriptionTier(**tier_data)
            db.add(tier)

        db.commit()
        logger.info(f"Initialized {len(tiers)} default subscription tiers")

    @staticmethod
    def create_checkout_session(
        db: Session,
        user_id: int,
        tier_name: str,
        billing_interval: str = "month"
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for subscription purchase.
        
        Args:
            db: Database session
            user_id: User ID
            tier_name: Tier name (starter, pro, premium)
            billing_interval: 'month' or 'year'
            
        Returns:
            Dictionary with checkout session URL and session ID
        """
        # Get user and tier
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        tier = db.query(SubscriptionTier).filter(SubscriptionTier.name == tier_name).first()
        if not tier:
            raise ValueError(f"Tier '{tier_name}' not found")

        stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        stripe_mode = os.getenv("STRIPE_MODE", "test")
        is_mock_key = (not stripe_key) or stripe_key.startswith("mk_")

        # If mock key or test mode without valid secret key, simulate instant tier activation
        if is_mock_key:
            logger.info(f"Test/Simulated checkout for user {user_id}, tier {tier_name} (Stripe key: {stripe_key or 'None'})")
            # Cancel existing active subscriptions
            existing_subs = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == "active"
            ).all()
            for sub in existing_subs:
                sub.status = "canceled"
                sub.cancel_at_period_end = True

            now = datetime.datetime.utcnow()
            days = 365 if billing_interval == "year" else 30
            period_end = now + datetime.timedelta(days=days)

            new_sub = UserSubscription(
                user_id=user_id,
                tier_id=tier.id,
                stripe_customer_id=f"sim_cust_{user_id}",
                stripe_subscription_id=f"sim_sub_{user_id}_{int(now.timestamp())}",
                status="active",
                billing_interval=billing_interval,
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False
            )
            db.add(new_sub)
            user.current_tier_id = tier.id
            db.commit()

            frontend_url = os.getenv("FRONTEND_URL", "https://primeedge.app").rstrip("/")
            return {
                "checkout_url": f"{frontend_url}/pricing?activated={tier.name}",
                "session_id": f"sim_sess_{user_id}",
                "customer_id": f"sim_cust_{user_id}"
            }

        # Otherwise, attempt real Stripe checkout
        try:
            # Get or create Stripe customer
            stripe_customer_id = user.subscriptions[0].stripe_customer_id if user.subscriptions else None
            
            if not stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.full_name or user.email,
                    metadata={"user_id": user_id}
                )
                stripe_customer_id = customer.id
            else:
                stripe.Customer.modify(
                    stripe_customer_id,
                    email=user.email,
                    name=user.full_name or user.email
                )

            # Determine price based on billing interval
            price_id = tier.stripe_price_id_monthly if billing_interval == "month" else tier.stripe_price_id_yearly
            
            if not price_id:
                amount = int(tier.price_monthly * 100) if billing_interval == "month" else int(tier.price_yearly * 100)
                price = stripe.Price.create(
                    unit_amount=amount,
                    currency="usd",
                    recurring={"interval": billing_interval},
                    product_data={
                        "name": f"PrimeEdge {tier.display_name}",
                        "description": tier.description
                    },
                    metadata={"tier_name": tier.name}
                )
                price_id = price.id

            frontend_url = os.getenv("FRONTEND_URL", "https://primeedge.app").rstrip("/")
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=f"{frontend_url}/pricing?session_id={{CHECKOUT_SESSION_ID}}&activated={tier.name}",
                cancel_url=f"{frontend_url}/pricing",
                metadata={
                    "user_id": str(user_id),
                    "tier_id": str(tier.id),
                    "tier_name": tier.name,
                    "billing_interval": billing_interval
                }
            )

            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "customer_id": stripe_customer_id
            }
        except stripe.error.AuthenticationError as e:
            logger.error(f"Stripe Authentication Error: {e}")
            if stripe_mode == "test":
                logger.warning("Falling back to test activation due to invalid Stripe credentials in test mode")
                now = datetime.datetime.utcnow()
                days = 365 if billing_interval == "year" else 30
                period_end = now + datetime.timedelta(days=days)
                new_sub = UserSubscription(
                    user_id=user_id,
                    tier_id=tier.id,
                    stripe_customer_id=f"sim_cust_{user_id}",
                    stripe_subscription_id=f"sim_sub_{user_id}_{int(now.timestamp())}",
                    status="active",
                    billing_interval=billing_interval,
                    current_period_start=now,
                    current_period_end=period_end,
                    cancel_at_period_end=False
                )
                db.add(new_sub)
                user.current_tier_id = tier.id
                db.commit()
                frontend_url = os.getenv("FRONTEND_URL", "https://primeedge.app").rstrip("/")
                return {
                    "checkout_url": f"{frontend_url}/pricing?activated={tier.name}",
                    "session_id": f"sim_sess_{user_id}",
                    "customer_id": f"sim_cust_{user_id}"
                }
            raise ValueError(f"Stripe authentication failed: {e}")
        except Exception as e:
            logger.error(f"Stripe checkout error: {e}")
            raise

    @staticmethod
    def handle_webhook_event(db: Session, payload: Dict[str, Any], signature: str) -> None:
        """
        Handle Stripe webhook events.
        
        Args:
            db: Database session
            payload: Webhook payload
            signature: Stripe signature for verification
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise ValueError("Webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise

        # Log the event
        event_type = event["type"]
        stripe_event_id = event["id"]

        # Check if event already processed
        existing = db.query(StripeWebhookEvent).filter(
            StripeWebhookEvent.stripe_event_id == stripe_event_id
        ).first()
        
        if existing:
            logger.info(f"Event {stripe_event_id} already processed, skipping")
            return

        # Create webhook event log
        webhook_log = StripeWebhookEvent(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            payload=payload,
            processed=False
        )
        db.add(webhook_log)

        try:
            # Handle different event types
            if event_type == "checkout.session.completed":
                StripeService._handle_checkout_completed(db, event["data"]["object"])
            elif event_type == "customer.subscription.created":
                StripeService._handle_subscription_created(db, event["data"]["object"])
            elif event_type == "customer.subscription.updated":
                StripeService._handle_subscription_updated(db, event["data"]["object"])
            elif event_type == "customer.subscription.deleted":
                StripeService._handle_subscription_deleted(db, event["data"]["object"])
            elif event_type == "invoice.payment_succeeded":
                StripeService._handle_payment_succeeded(db, event["data"]["object"])
            elif event_type == "invoice.payment_failed":
                StripeService._handle_payment_failed(db, event["data"]["object"])
            else:
                logger.info(f"Unhandled event type: {event_type}")

            webhook_log.processed = True
            db.commit()
            logger.info(f"Successfully processed webhook event: {event_type}")

        except Exception as e:
            webhook_log.processed = False
            webhook_log.error_message = str(e)
            db.commit()
            logger.error(f"Error processing webhook event {event_type}: {e}")
            raise

    @staticmethod
    def _handle_checkout_completed(db: Session, session: Dict[str, Any]) -> None:
        """Handle checkout.session.completed event."""
        metadata = session.get("metadata", {})
        user_id = int(metadata.get("user_id"))
        tier_id = int(metadata.get("tier_id"))
        tier_name = metadata.get("tier_name")
        billing_interval = metadata.get("billing_interval", "month")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        # Get user and tier
        user = db.query(User).filter(User.id == user_id).first()
        tier = db.query(SubscriptionTier).filter(SubscriptionTier.id == tier_id).first()

        if not user or not tier:
            logger.error(f"User or tier not found for checkout session {session['id']}")
            return

        # Cancel existing active subscriptions
        existing_subs = db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active"
        ).all()
        
        for sub in existing_subs:
            sub.status = "canceled"
            sub.cancel_at_period_end = True

        # Create new subscription record
        new_subscription = UserSubscription(
            user_id=user_id,
            tier_id=tier_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status="active",
            billing_interval=billing_interval,
            current_period_start=None,  # Will be set by subscription.created event
            current_period_end=None,
            cancel_at_period_end=False
        )
        db.add(new_subscription)

        # Update user's current tier
        user.current_tier_id = tier_id

        db.commit()
        logger.info(f"Checkout completed for user {user_id}, tier {tier_name}")

    @staticmethod
    def _handle_subscription_created(db: Session, subscription: Dict[str, Any]) -> None:
        """Handle customer.subscription.created event."""
        stripe_sub_id = subscription.get("id")
        customer_id = subscription.get("customer")
        
        # Find subscription by stripe ID
        user_sub = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if user_sub:
            # Update subscription details
            user_sub.current_period_start = subscription.get("current_period_start")
            user_sub.current_period_end = subscription.get("current_period_end")
            user_sub.status = subscription.get("status", "active")
            db.commit()
            logger.info(f"Subscription created/updated: {stripe_sub_id}")

    @staticmethod
    def _handle_subscription_updated(db: Session, subscription: Dict[str, Any]) -> None:
        """Handle customer.subscription.updated event."""
        stripe_sub_id = subscription.get("id")
        
        user_sub = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if user_sub:
            user_sub.status = subscription.get("status", "active")
            user_sub.current_period_start = subscription.get("current_period_start")
            user_sub.current_period_end = subscription.get("current_period_end")
            user_sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)
            db.commit()
            logger.info(f"Subscription updated: {stripe_sub_id}")

    @staticmethod
    def _handle_subscription_deleted(db: Session, subscription: Dict[str, Any]) -> None:
        """Handle customer.subscription.deleted event."""
        stripe_sub_id = subscription.get("id")
        
        user_sub = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if user_sub:
            user_sub.status = "canceled"
            # Downgrade user to starter tier
            starter_tier = db.query(SubscriptionTier).filter(SubscriptionTier.name == "starter").first()
            if starter_tier and user_sub.user:
                user_sub.user.current_tier_id = starter_tier.id
            db.commit()
            logger.info(f"Subscription deleted: {stripe_sub_id}")

    @staticmethod
    def _handle_payment_succeeded(db: Session, invoice: Dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded event."""
        logger.info(f"Payment succeeded for invoice: {invoice.get('id')}")

    @staticmethod
    def _handle_payment_failed(db: Session, invoice: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed event."""
        stripe_sub_id = invoice.get("subscription")
        
        if stripe_sub_id:
            user_sub = db.query(UserSubscription).filter(
                UserSubscription.stripe_subscription_id == stripe_sub_id
            ).first()
            
            if user_sub:
                user_sub.status = "past_due"
                db.commit()
                logger.warning(f"Payment failed for subscription: {stripe_sub_id}")

    @staticmethod
    def get_user_tier_info(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """Get current tier information for a user."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.current_tier_id:
            return None

        tier = db.query(SubscriptionTier).filter(SubscriptionTier.id == user.current_tier_id).first()
        if not tier:
            return None

        return {
            "tier_id": tier.id,
            "name": tier.name,
            "display_name": tier.display_name,
            "description": tier.description,
            "price_monthly": tier.price_monthly,
            "price_yearly": tier.price_yearly,
            "features": tier.features,
            "max_accounts": tier.max_accounts,
            "auto_execution_enabled": tier.auto_execution_enabled,
            "api_access_enabled": tier.api_access_enabled
        }

    @staticmethod
    def check_auto_execution_access(db: Session, user_id: int) -> bool:
        """Check if user has auto-execution access (Premium tier only)."""
        tier_info = StripeService.get_user_tier_info(db, user_id)
        return tier_info and tier_info.get("auto_execution_enabled", False)