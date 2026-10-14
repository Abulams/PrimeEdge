"""
ctrader_auth_router.py — PrimeEdge cTrader OAuth Onboarding Router
====================================================================
FastAPI router for connecting client accounts via cTrader OAuth 2.0.

Environment variables required:
    CTRADER_CLIENT_ID       – OAuth application client ID
    CTRADER_CLIENT_SECRET   – OAuth application client secret
    CTRADER_REDIRECT_URI    – Registered redirect URI (must match cTrader app settings)

OAuth endpoints:
    Authorise : https://connect.ctrader.com/apps/auth
    Token     : https://connect.ctrader.com/apps/token
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserBrokerAccount, User
from app.execution.ctrader_gateway import CTraderGateway, CTraderConnectionError

logger = logging.getLogger("ctrader_auth_router")

router = APIRouter(prefix="/api/v1/ctrader", tags=["cTrader OAuth"])

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

CTRADER_CLIENT_ID = os.getenv("CTRADER_CLIENT_ID", "43796_NUbyz1CxFRhD01Tm0Jqc1hMVHd4ubgk5lZQcwtftpuH5zJozj1")
CTRADER_CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET", "j9WYsJ4mG80iyHKbale8Fuxx75fO9eaMuUoOhrZWSlCS653C9C")
CTRADER_REDIRECT_URI = os.getenv(
    "CTRADER_REDIRECT_URI", "https://primeedge.app/api/v1/ctrader/callback"
)
CTRADER_AUTH_URL = "https://connect.spotware.com/apps/auth"
CTRADER_TOKEN_URL = "https://connect.spotware.com/apps/token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_gateway() -> CTraderGateway:
    is_demo = os.getenv("CTRADER_IS_DEMO", "true").lower() == "true"
    return CTraderGateway(
        client_id=CTRADER_CLIENT_ID,
        client_secret=CTRADER_CLIENT_SECRET,
        is_demo=is_demo,
    )


async def _exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> dict:
    r_uri = redirect_uri or CTRADER_REDIRECT_URI
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            CTRADER_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": r_uri,
                "client_id": CTRADER_CLIENT_ID,
                "client_secret": CTRADER_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        logger.error(
            "Token exchange failed: %s – %s", response.status_code, response.text
        )
        raise HTTPException(
            status_code=502,
            detail=f"Token exchange with cTrader failed: {response.text}",
        )

    return response.json()


async def _refresh_access_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            CTRADER_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CTRADER_CLIENT_ID,
                "client_secret": CTRADER_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Token refresh with cTrader failed: {response.text}",
        )

    return response.json()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/auth")
async def ctrader_auth_redirect(
    user_id: int = Query(1, description="PrimeEdge user ID to associate the account with"),
    redirect_uri: Optional[str] = Query(None, description="Optional custom redirect URI"),
) -> RedirectResponse:
    """
    Step 1 – Redirect user browser to cTrader OAuth consent screen.
    GET /api/v1/ctrader/auth?user_id=123
    """
    if not CTRADER_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="CTRADER_CLIENT_ID is not configured on the server.",
        )

    r_uri = redirect_uri or CTRADER_REDIRECT_URI

    auth_url = (
        f"{CTRADER_AUTH_URL}"
        f"?client_id={CTRADER_CLIENT_ID}"
        f"&redirect_uri={r_uri}"
        f"&scope=trading"
        f"&state={user_id}"
    )

    logger.info("Redirecting user %s to cTrader OAuth: %s", user_id, auth_url)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def ctrader_callback(
    request: Request,
    code: str = Query(..., description="Authorisation code from cTrader"),
    state: int = Query(1, description="user_id passed as OAuth state"),
    db: Session = Depends(get_db),
):
    """
    Step 2 – OAuth callback.
    1. Exchange code -> tokens
    2. Fetch list of cTrader accounts via OpenAPI
    3. Upsert UserBrokerAccount record
    """
    user_id = state

    # Ensure user exists in database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=f"trader_{user_id}@primeedge.app",
            password_hash="OAUTH_USER",
            role="trader",
            is_active=True,
            is_admin=True,
            email_verified=True
        )
        db.add(user)
        db.commit()

    # Determine the actual callback URI requested
    actual_redirect_uri = str(request.url).split('?')[0]
    tokens = await _exchange_code_for_tokens(code, redirect_uri=actual_redirect_uri)
    access_token: str = tokens.get("accessToken") or tokens.get("access_token", "")
    refresh_token: str = tokens.get("refreshToken") or tokens.get("refresh_token", "")
    expires_in: int = int(tokens.get("expiresIn") or tokens.get("expires_in", 3600))
    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Fetch accounts linked to this token via cTrader OpenAPI
    gateway = _get_gateway()
    linked_accounts = []
    try:
        await gateway.connect()
        linked_accounts = await gateway.get_accounts_by_access_token(access_token)
    except (CTraderConnectionError, Exception) as exc:
        logger.error("Failed to fetch cTrader accounts for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Connected to cTrader but failed to retrieve accounts: {exc}",
        )
    finally:
        await gateway.disconnect()

    if not linked_accounts:
        raise HTTPException(
            status_code=400,
            detail="No cTrader accounts found for this access token.",
        )

    upserted = []
    for ct_account in linked_accounts:
        ct_account_id: int = ct_account["ctid_trader_account_id"]

        uba = db.query(UserBrokerAccount).filter(
            UserBrokerAccount.user_id == user_id,
            UserBrokerAccount.ctrader_account_id == ct_account_id,
        ).first()

        if uba is None:
            uba = UserBrokerAccount(
                user_id=user_id,
                broker_server=ct_account.get("broker_name") or "cTrader-OpenAPI",
                login=ct_account_id,
                encrypted_password="OAUTH_TOKEN_MANAGED",
                platform_type="CTRADER_CLOUD",
                platform="ctrader",
                ctrader_account_id=ct_account_id,
                is_copier_active=True,
            )
            db.add(uba)
            logger.info("Created UserBrokerAccount for user %s, account %s", user_id, ct_account_id)
        else:
            uba.platform = "ctrader"
            uba.is_copier_active = True
            logger.info("Updating UserBrokerAccount for user %s, account %s", user_id, ct_account_id)

        uba.ctrader_access_token = access_token
        uba.ctrader_refresh_token = refresh_token
        uba.ctrader_token_expiry = token_expiry

        upserted.append({
            "ctid_trader_account_id": ct_account_id,
            "is_live": ct_account.get("is_live", False),
            "trader_login": ct_account.get("trader_login"),
            "broker_name": ct_account.get("broker_name"),
        })

    db.commit()

    logger.info("Successfully linked %d cTrader account(s) for user %s", len(upserted), user_id)
    
    accounts_html = "".join([f"<li>Account <b>{a['ctid_trader_account_id']}</b> ({a.get('broker_name') or 'cTrader'})</li>" for a in upserted])
    
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html>
<head>
    <title>PrimeEdge cTrader Link Successful</title>
    <meta http-equiv="refresh" content="4;url=https://primeedge.app" />
    <style>
        body {{ background: #0B0E14; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #151A24; border: 1px solid rgba(0, 242, 254, 0.4); box-shadow: 0 0 30px rgba(0, 242, 254, 0.15); padding: 40px; border-radius: 14px; text-align: center; max-width: 520px; }}
        h1 {{ color: #00f2fe; margin-top: 0; font-size: 26px; }}
        p {{ color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 20px; }}
        ul {{ list-style: none; padding: 0; margin: 20px 0; }}
        li {{ background: rgba(0, 242, 254, 0.08); border: 1px solid rgba(0, 242, 254, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 8px; font-size: 14px; color: #fff; }}
        .btn {{ display: inline-block; margin-top: 15px; padding: 12px 28px; background: linear-gradient(135deg, #00f2fe, #4facfe); color: #000; font-weight: 800; text-decoration: none; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>&#10003; cTrader Connected!</h1>
        <p>Your cTrader master account has been authenticated and linked to the PrimeEdge Copier.</p>
        <ul>{accounts_html}</ul>
        <p>Redirecting back to PrimeEdge in 4 seconds...</p>
        <a class="btn" href="https://primeedge.app">Return to PrimeEdge</a>
    </div>
</body>
</html>
""")


@router.post("/disconnect")
def ctrader_disconnect(
    user_id: int = Query(..., description="PrimeEdge user ID"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Clear all stored cTrader tokens for a user and disable copier."""
    accounts = db.query(UserBrokerAccount).filter(
        UserBrokerAccount.user_id == user_id,
        UserBrokerAccount.platform == "ctrader",
    ).all()

    if not accounts:
        raise HTTPException(
            status_code=404,
            detail=f"No cTrader accounts found for user {user_id}.",
        )

    for uba in accounts:
        uba.ctrader_access_token = None
        uba.ctrader_refresh_token = None
        uba.ctrader_token_expiry = None
        uba.is_copier_active = False

    db.commit()
    logger.info("Disconnected cTrader for user %s (%d account(s))", user_id, len(accounts))

    return JSONResponse(content={
        "status": "success",
        "user_id": user_id,
        "accounts_cleared": len(accounts),
    })


@router.get("/accounts/{user_id}")
def get_ctrader_accounts(
    user_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Return all cTrader accounts connected to a PrimeEdge user."""
    accounts = db.query(UserBrokerAccount).filter(
        UserBrokerAccount.user_id == user_id,
        UserBrokerAccount.platform == "ctrader",
    ).all()

    account_list = []
    for uba in accounts:
        is_token_valid = (
            uba.ctrader_token_expiry is not None
            and uba.ctrader_token_expiry > datetime.now(timezone.utc)
        )
        account_list.append({
            "broker_account_db_id": uba.id,
            "ctrader_account_id": uba.ctrader_account_id,
            "platform": uba.platform,
            "is_copier_active": uba.is_copier_active,
            "token_valid": is_token_valid,
            "risk_mode": uba.risk_mode,
            "fixed_lot_size": uba.fixed_lot_size,
            "risk_pct": uba.risk_pct,
            "allowed_instruments": uba.allowed_instruments,
        })

    return JSONResponse(content={"user_id": user_id, "accounts": account_list})
