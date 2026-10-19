import os
import hmac
import hashlib
import json
import logging
import datetime
from typing import Dict, Any, Optional
import requests
from sqlalchemy.orm import Session

from .models import User, SubscriptionTier, UserSubscription

logger = logging.getLogger("marketos.paystack")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
PAYSTACK_API_BASE = "https://api.paystack.co"


class PaystackService:
    """Paystack payment and recurring subscription management."""

    @staticmethod
    def get_public_config() -> Dict[str, Any]:
        """Returns public Paystack configuration for frontend."""
        return {
            "paystack_public_key": os.getenv("PAYSTACK_PUBLIC_KEY", ""),
            "enabled": bool(os.getenv("PAYSTACK_SECRET_KEY"))
        }

    @staticmethod
    def create_checkout_session(
        db: Session,
        user_id: int,
        tier_name: str,
        billing_interval: str = "month"
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack checkout session for a subscription plan.
        """
        secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        if not secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY is not configured on the server")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        tier = db.query(SubscriptionTier).filter(SubscriptionTier.name == tier_name).first()
        if not tier:
            raise ValueError(f"Tier '{tier_name}' not found")

        amount_ngn = tier.price_monthly_ngn or (tier.price_monthly * 1500.0)
        amount_kobo = int(round(amount_ngn * 100))

        frontend_url = os.getenv("FRONTEND_URL", "https://primeedge.app").rstrip("/")
        callback_url = f"{frontend_url}/pricing?payment=paystack&activated={tier.name}"

        payload: Dict[str, Any] = {
            "email": user.email,
            "amount": amount_kobo,
            "callback_url": callback_url,
            "metadata": {
                "user_id": str(user.id),
                "tier_id": str(tier.id),
                "tier_name": tier.name,
                "billing_interval": billing_interval,
                "custom_fields": [
                    {
                        "display_name": "Plan",
                        "variable_name": "plan_name",
                        "value": f"PrimeEdge {tier.display_name}"
                    },
                    {
                        "display_name": "Account",
                        "variable_name": "user_email",
                        "value": user.email
                    }
                ]
            }
        }

        # If a monthly recurring plan code exists, attach it
        if billing_interval == "month" and tier.paystack_plan_id_monthly:
            payload["plan"] = tier.paystack_plan_id_monthly

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Initializing Paystack transaction for user {user.email}, tier {tier.name}, amount {amount_ngn} NGN")
        resp = requests.post(
            f"{PAYSTACK_API_BASE}/transaction/initialize",
            headers=headers,
            json=payload,
            timeout=15
        )

        data = resp.json()
        if not resp.ok or not data.get("status"):
            err_msg = data.get("message", "Failed to initialize Paystack transaction")
            logger.error(f"Paystack initialization error: {data}")
            raise ValueError(err_msg)

        tx_data = data["data"]
        return {
            "checkout_url": tx_data["authorization_url"],
            "access_code": tx_data.get("access_code"),
            "reference": tx_data.get("reference")
        }

    @staticmethod
    def verify_transaction(db: Session, reference: str) -> Dict[str, Any]:
        """
        Verify transaction with Paystack and activate the subscription.
        """
        secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        if not secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }

        resp = requests.get(
            f"{PAYSTACK_API_BASE}/transaction/verify/{reference}",
            headers=headers,
            timeout=15
        )
        data = resp.json()
        if not resp.ok or not data.get("status"):
            err_msg = data.get("message", "Transaction verification failed")
            logger.error(f"Paystack verification error for {reference}: {data}")
            raise ValueError(err_msg)

        tx_data = data["data"]
        status = tx_data.get("status")

        if status != "success":
            return {
                "success": False,
                "status": status,
                "message": tx_data.get("gateway_response", "Transaction was not successful")
            }

        # Extract metadata
        metadata = tx_data.get("metadata", {})
        user_id_str = metadata.get("user_id")
        tier_id_str = metadata.get("tier_id")

        if not user_id_str or not tier_id_str:
            # Fallback by email lookup
            customer_email = tx_data.get("customer", {}).get("email")
            user = db.query(User).filter(User.email == customer_email).first()
            if not user:
                raise ValueError("Could not match transaction to a user account")
            user_id = user.id
            tier_id = user.current_tier_id or 1
        else:
            user_id = int(user_id_str)
            tier_id = int(tier_id_str)

        user = db.query(User).filter(User.id == user_id).first()
        tier = db.query(SubscriptionTier).filter(SubscriptionTier.id == tier_id).first()

        if not user or not tier:
            raise ValueError("User or subscription tier not found")

        # Check if already processed
        existing_sub = db.query(UserSubscription).filter(
            UserSubscription.paystack_reference == reference
        ).first()

        if existing_sub:
            logger.info(f"Paystack transaction {reference} already processed for user {user.id}")
            return {
                "success": True,
                "status": "success",
                "tier_name": tier.name,
                "already_processed": True
            }

        # Cancel any previous active subscriptions
        active_subs = db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id,
            UserSubscription.status == "active"
        ).all()
        for s in active_subs:
            s.status = "canceled"
            s.cancel_at_period_end = True

        now = datetime.datetime.utcnow()
        period_end = now + datetime.timedelta(days=30)

        customer_code = tx_data.get("customer", {}).get("customer_code")
        plan_code = tx_data.get("plan")

        new_sub = UserSubscription(
            user_id=user.id,
            tier_id=tier.id,
            payment_provider="paystack",
            paystack_customer_code=customer_code,
            paystack_subscription_code=plan_code,
            paystack_reference=reference,
            status="active",
            billing_interval="month",
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False
        )
        db.add(new_sub)

        # Grant tier access
        user.current_tier_id = tier.id
        db.commit()

        logger.info(f"Successfully activated Paystack subscription for user {user.id} ({user.email}), tier {tier.name}")
        return {
            "success": True,
            "status": "success",
            "tier_name": tier.name,
            "already_processed": False
        }

    @staticmethod
    def handle_webhook_event(db: Session, payload_bytes: bytes, signature: str) -> None:
        """
        Verify Paystack HMAC SHA512 signature and process webhook event.
        """
        secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        if not secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY not configured")

        # Compute HMAC SHA512
        computed_sig = hmac.new(
            secret_key.encode("utf-8"),
            payload_bytes,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed_sig, signature):
            logger.error("Invalid Paystack webhook signature")
            raise ValueError("Invalid webhook signature")

        event = json.loads(payload_bytes.decode("utf-8"))
        event_type = event.get("event")
        data = event.get("data", {})

        logger.info(f"Received Paystack webhook event: {event_type}")

        if event_type in ("charge.success", "subscription.create"):
            reference = data.get("reference")
            metadata = data.get("metadata", {})
            user_id_str = metadata.get("user_id")
            tier_id_str = metadata.get("tier_id")

            if not user_id_str or not tier_id_str:
                customer_email = data.get("customer", {}).get("email")
                user = db.query(User).filter(User.email == customer_email).first()
                if not user:
                    logger.warning(f"No user found for Paystack event {event_type}, email {customer_email}")
                    return
                user_id = user.id
                tier = db.query(SubscriptionTier).filter(SubscriptionTier.paystack_plan_id_monthly == data.get("plan", {}).get("plan_code")).first()
                tier_id = tier.id if tier else 1
            else:
                user_id = int(user_id_str)
                tier_id = int(tier_id_str)

            user = db.query(User).filter(User.id == user_id).first()
            tier = db.query(SubscriptionTier).filter(SubscriptionTier.id == tier_id).first()
            if not user or not tier:
                logger.error(f"User or tier not found in Paystack webhook: user={user_id}, tier={tier_id}")
                return

            # Check if reference already recorded
            if reference:
                existing = db.query(UserSubscription).filter(
                    UserSubscription.paystack_reference == reference
                ).first()
                if existing:
                    logger.info(f"Paystack reference {reference} already processed, skipping")
                    return

            now = datetime.datetime.utcnow()
            period_end = now + datetime.timedelta(days=30)
            customer_code = data.get("customer", {}).get("customer_code")
            plan_code = data.get("plan", {}).get("plan_code") if isinstance(data.get("plan"), dict) else data.get("plan")

            new_sub = UserSubscription(
                user_id=user.id,
                tier_id=tier.id,
                payment_provider="paystack",
                paystack_customer_code=customer_code,
                paystack_subscription_code=plan_code,
                paystack_reference=reference,
                status="active",
                billing_interval="month",
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False
            )
            db.add(new_sub)
            user.current_tier_id = tier.id
            db.commit()
            logger.info(f"Webhook activated user {user.id} on tier {tier.name}")

        elif event_type in ("subscription.disable", "subscription.not_renew"):
            sub_code = data.get("subscription_code")
            sub = db.query(UserSubscription).filter(
                UserSubscription.paystack_subscription_code == sub_code
            ).first()
            if sub:
                sub.status = "canceled"
                sub.cancel_at_period_end = True
                db.commit()
                logger.info(f"Paystack subscription {sub_code} canceled")
