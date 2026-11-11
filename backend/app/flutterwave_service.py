"""
Flutterwave Payment & Subscription Service
============================================
Handles checkout initiation, transaction verification, and webhooks
for USD and multi-currency payments via Flutterwave Standard API (v3).
"""
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

logger = logging.getLogger("marketos.flutterwave")

FLUTTERWAVE_API_BASE = "https://api.flutterwave.com/v3"


class FlutterwaveService:
    """Flutterwave checkout session creation and transaction verification."""

    @staticmethod
    def get_public_config() -> Dict[str, Any]:
        """Returns public Flutterwave configuration for the frontend."""
        public_key = os.getenv("FLUTTERWAVE_PUBLIC_KEY", "FLWPUBK-c2f3d3766bdfbacc00eee7f4bf951ece-X")
        secret_key = os.getenv("FLUTTERWAVE_SECRET_KEY", "FLWSECK-ce4c3f22e8e4b8f70b2c21f116fdf9c9-1a1c3160d76vt-X")
        return {
            "flutterwave_public_key": public_key,
            "enabled": bool(secret_key)
        }

    @staticmethod
    def create_checkout_session(
        db: Session,
        user_id: int,
        tier_name: str,
        billing_interval: str = "month",
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Initializes a Flutterwave standard checkout payment link for a subscription.
        Default currency is USD for international cards.
        """
        secret_key = os.getenv("FLUTTERWAVE_SECRET_KEY", "FLWSECK-ce4c3f22e8e4b8f70b2c21f116fdf9c9-1a1c3160d76vt-X")
        if not secret_key:
            raise ValueError("FLUTTERWAVE_SECRET_KEY is not configured on the server")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        tier = db.query(SubscriptionTier).filter(SubscriptionTier.name == tier_name).first()
        if not tier:
            raise ValueError(f"Tier '{tier_name}' not found")

        # Determine price by currency and interval
        if currency.upper() == "USD":
            base_price = tier.price_monthly
            amount = (base_price * 10.0) if billing_interval == "year" else base_price
        else:
            base_ngn = tier.price_monthly_ngn or (tier.price_monthly * 1500.0)
            amount = (base_ngn * 10.0) if billing_interval == "year" else base_ngn

        timestamp = int(datetime.datetime.utcnow().timestamp())
        tx_ref = f"pe_flw_{user.id}_{tier.id}_{timestamp}"

        frontend_url = os.getenv("FRONTEND_URL", "https://primeedge.app").rstrip("/")
        redirect_url = f"{frontend_url}/pricing?payment=flutterwave&activated={tier.name}&reference={tx_ref}"

        payload: Dict[str, Any] = {
            "tx_ref": tx_ref,
            "amount": float(amount),
            "currency": currency.upper(),
            "redirect_url": redirect_url,
            "customer": {
                "email": user.email,
                "name": getattr(user, "full_name", None) or getattr(user, "username", "PrimeEdge Trader")
            },
            "customizations": {
                "title": f"PrimeEdge {tier.display_name} Plan",
                "description": f"Intraday Decision Support Software ({billing_interval}ly)",
                "logo": f"{frontend_url}/market_os_logo_emblem.jpg"
            },
            "meta": {
                "user_id": str(user.id),
                "tier_id": str(tier.id),
                "tier_name": tier.name,
                "billing_interval": billing_interval,
                "currency": currency.upper()
            }
        }

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Initializing Flutterwave checkout for user {user.email}, tier {tier.name}, amount {amount} {currency}")
        resp = requests.post(
            f"{FLUTTERWAVE_API_BASE}/payments",
            headers=headers,
            json=payload,
            timeout=15
        )

        data = resp.json()
        if not resp.ok or data.get("status") != "success":
            err_msg = data.get("message", "Flutterwave initialization failed")
            logger.error(f"Flutterwave error: {err_msg} | response={data}")
            raise ValueError(f"Flutterwave payment initialization failed: {err_msg}")

        checkout_url = data.get("data", {}).get("link")
        if not checkout_url:
            raise ValueError("No checkout link received from Flutterwave")

        return {
            "checkout_url": checkout_url,
            "reference": tx_ref,
            "amount": amount,
            "currency": currency.upper()
        }

    @staticmethod
    def verify_transaction(db: Session, reference: str, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify a Flutterwave transaction using tx_ref or transaction_id and activate subscription.
        """
        secret_key = os.getenv("FLUTTERWAVE_SECRET_KEY", "FLWSECK-ce4c3f22e8e4b8f70b2c21f116fdf9c9-1a1c3160d76vt-X")
        if not secret_key:
            raise ValueError("FLUTTERWAVE_SECRET_KEY is not configured on the server")

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }

        # Verify endpoint by ID or tx_ref
        if transaction_id:
            verify_url = f"{FLUTTERWAVE_API_BASE}/transactions/{transaction_id}/verify"
        else:
            verify_url = f"{FLUTTERWAVE_API_BASE}/transactions/verify_by_reference?tx_ref={reference}"

        resp = requests.get(verify_url, headers=headers, timeout=15)
        data = resp.json()

        if not resp.ok or data.get("status") != "success":
            msg = data.get("message", "Flutterwave verification failed")
            logger.error(f"Flutterwave verify error for {reference}: {msg}")
            raise ValueError(f"Payment verification failed: {msg}")

        tx_data = data.get("data", {})
        status = tx_data.get("status")
        if status != "successful":
            raise ValueError(f"Transaction not successful. Status: {status}")

        meta = tx_data.get("meta", {})
        user_id_str = meta.get("user_id")
        tier_id_str = meta.get("tier_id")

        if not user_id_str or not tier_id_str:
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

        tx_ref = tx_data.get("tx_ref", reference)

        # Check idempotency
        existing_sub = db.query(UserSubscription).filter(
            UserSubscription.paystack_reference == tx_ref
        ).first()

        if existing_sub:
            logger.info(f"Flutterwave transaction {tx_ref} already processed for user {user.id}")
            return {
                "success": True,
                "status": "success",
                "tier_name": tier.name,
                "already_processed": True
            }

        # Cancel previous active subscriptions
        active_subs = db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id,
            UserSubscription.status == "active"
        ).all()
        for s in active_subs:
            s.status = "canceled"
            s.cancel_at_period_end = True

        now = datetime.datetime.utcnow()
        interval = meta.get("billing_interval", "month")
        days = 365 if interval == "year" else 30
        period_end = now + datetime.timedelta(days=days)

        new_sub = UserSubscription(
            user_id=user.id,
            tier_id=tier.id,
            payment_provider="flutterwave",
            paystack_reference=tx_ref,  # Store reference in existing reference field
            status="active",
            billing_interval=interval,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False
        )
        db.add(new_sub)

        # Upgrade user tier directly
        user.current_tier_id = tier.id
        db.commit()

        logger.info(f"Successfully activated Flutterwave subscription for user {user.email}: tier={tier.name}, tx_ref={tx_ref}")
        return {
            "success": True,
            "status": "success",
            "tier_name": tier.name,
            "period_end": period_end.isoformat(),
            "already_processed": False
        }

    @staticmethod
    def handle_webhook_event(db: Session, body_bytes: bytes, signature_header: str) -> bool:
        """
        Verify and process Flutterwave webhook event.
        Flutterwave sends the hash configured in dashboard in 'verif-hash' header.
        """
        secret_hash = os.getenv("FLUTTERWAVE_WEBHOOK_HASH", "Lamido556@")
        if secret_hash and signature_header != secret_hash:
            logger.warning("Flutterwave webhook signature mismatch")
            raise ValueError("Invalid webhook signature")

        try:
            event_data = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            raise ValueError("Malformed JSON payload")

        event = event_data.get("event")
        data = event_data.get("data", {})
        logger.info(f"Received Flutterwave webhook event: {event}")

        if event == "charge.completed" and data.get("status") == "successful":
            tx_ref = data.get("tx_ref")
            flw_id = str(data.get("id"))
            if tx_ref:
                FlutterwaveService.verify_transaction(db, tx_ref, transaction_id=flw_id)
                return True

        return True
