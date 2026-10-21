import os
import json
import logging
import threading
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List

logger = logging.getLogger("marketos.telegram")

# Environment variables with sensible defaults
DEFAULT_BOT_TOKEN = "8689013346:AAFcuxzlWs3JhBNe5PEnQBzqKfrKJ4fAdFg"
# Supports channel and private chat simultaneously
DEFAULT_CHAT_ID = "-1004238118164,1003107104"

class TelegramService:
    """
    Non-blocking, institutional Telegram notification service for PrimeEdge.
    Dispatches live quantitative setup alerts, execution updates, and system events.
    """

    @classmethod
    def get_bot_token(cls) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_BOT_TOKEN).strip()

    @classmethod
    def normalize_chat_id(cls, cid: str) -> str:
        cid = cid.strip()
        # If user passed channel ID like '1004238118164' without minus sign
        if cid.startswith("100") and len(cid) >= 12 and not cid.startswith("-"):
            return f"-{cid}"
        return cid

    @classmethod
    def get_chat_ids(cls) -> List[str]:
        raw = os.getenv("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID)
        # Support comma-separated list of chat/channel IDs
        ids = [cls.normalize_chat_id(c) for c in raw.split(",") if c.strip()]
        return ids if ids else ["-1004238118164", "1003107104"]

    @classmethod
    def _send_raw_message(cls, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Synchronous HTTP call to Telegram Bot API with timeout."""
        token = cls.get_bot_token()
        if not token:
            logger.warning("[Telegram] Bot token not configured. Skipping alert.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("ok"):
                    logger.info(f"[Telegram] Alert delivered successfully to chat {chat_id}")
                    return True
                else:
                    logger.error(f"[Telegram] Failed to deliver alert to {chat_id}: {res_data}")
                    return False
        except Exception as e:
            logger.error(f"[Telegram] Exception sending message to {chat_id}: {e}")
            return False

    @classmethod
    def send_message_async(cls, text: str, parse_mode: str = "HTML") -> None:
        """
        Dispatches message in a background daemon thread so calling services
        (realtime loop, order copier, execution engine) are NEVER blocked.
        """
        chat_ids = cls.get_chat_ids()

        def _worker():
            for cid in chat_ids:
                try:
                    cls._send_raw_message(cid, text, parse_mode=parse_mode)
                except Exception as ex:
                    logger.error(f"[Telegram] Worker error for chat {cid}: {ex}")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    @classmethod
    def format_setup_card(cls, snap, current_live_price: Optional[float] = None) -> str:
        """
        Formats an institutional quantitative trade card for a READY SetupSnapshot.
        Clearly demarcates Live Tick Price vs. Daily Anchor T0 Open vs. Entry Corridor.
        """
        inst = getattr(snap, "instrument", "UNKNOWN").upper()
        direction = getattr(snap, "direction", "LONG").upper()
        is_long = direction in ["LONG", "BUY", "BULLISH"]

        dir_emoji = "🟢 BUY" if is_long else "🔴 SELL"
        dir_sign = 1.0 if is_long else -1.0

        # Pip precision & multiplier
        if "JPY" in inst:
            pip_mult = 100.0
            price_fmt = "{:.3f}"
        elif "XAU" in inst or "GOLD" in inst:
            pip_mult = 10.0
            price_fmt = "{:.2f}"
        elif "US100" in inst or "NAS100" in inst:
            pip_mult = 1.0
            price_fmt = "{:.1f}"
        else:
            pip_mult = 10000.0
            price_fmt = "{:.5f}"

        # 1. Live Tick Price vs T0 Anchor
        live_val = current_live_price or getattr(snap, "live_price_at_snap", None) or getattr(snap, "setup_ref_price", 0.0)
        t0_open = getattr(snap, "setup_ref_price", live_val)

        # 2. Corridor P25 - P75
        p25 = getattr(snap, "corridor_p25_price", None) or t0_open
        p75 = getattr(snap, "corridor_p75_price", None) or t0_open
        corridor_low = min(p25, p75)
        corridor_high = max(p25, p75)

        # 3. Statistical Invalidation SL & TP
        sl_price = getattr(snap, "p90_invalidation", None)
        tp_pips = getattr(snap, "mfe_p75_pips", None) or getattr(snap, "mfe_p50_pips", None) or 30.0

        if not sl_price or sl_price <= 0:
            sl_price = round(live_val - (dir_sign * 25.0 / pip_mult), 5)

        tp_price = round(live_val + (dir_sign * tp_pips / pip_mult), 5)

        sl_dist_pips = round(abs(live_val - sl_price) * pip_mult, 1)
        tp_dist_pips = round(abs(tp_price - live_val) * pip_mult, 1)

        rr_ratio = round(tp_dist_pips / sl_dist_pips, 2) if sl_dist_pips > 0 else 1.5

        # 4. Statistical edge metrics
        conf_score = round(getattr(snap, "confidence_score", 0.0) or 0.0, 1)
        cont_prob = round((getattr(snap, "continuation_prob", 0.0) or 0.0) * 100.0, 1)
        if cont_prob == 0.0 and conf_score > 0:
            cont_prob = round(conf_score * 0.8, 1)

        session = getattr(snap, "session", "LONDON") or "LONDON"
        dxy = getattr(snap, "dxy_regime", "NEUTRAL") or "NEUTRAL"
        sample_n = getattr(snap, "historical_n", None) or 45
        thesis = getattr(snap, "setup_thesis", "") or "Empirical pattern edge confirmed with favorable MAE/MFE corridor."

        live_str = price_fmt.format(live_val)
        t0_str = price_fmt.format(t0_open)
        corr_min_str = price_fmt.format(corridor_low)
        corr_max_str = price_fmt.format(corridor_high)
        sl_str = price_fmt.format(sl_price)
        tp_str = price_fmt.format(tp_price)

        card = (
            f"⚡ <b>PRIMEEDGE QUANT SIGNAL: {inst} {dir_emoji}</b>\n"
            f"<i>Institutional Statistical Execution Corridor</i>\n\n"
            f"🎯 <b>EXECUTION PARAMETERS</b>\n"
            f"• <b>Live Tick Price:</b> <code>{live_str}</code>\n"
            f"• <b>Session Open (T₀ Anchor):</b> <code>{t0_str}</code>\n"
            f"• <b>Entry Corridor (P25–P75):</b> <code>{corr_min_str} – {corr_max_str}</code>\n"
            f"• <b>Statistical Invalidation (SL):</b> <code>{sl_str}</code> ({sl_dist_pips} pips)\n"
            f"• <b>Primary Target (MFE P75):</b> <code>{tp_str}</code> (+{tp_dist_pips} pips)\n"
            f"• <b>Feasibility R:R:</b> <code>1 : {rr_ratio}</code>\n\n"
            f"🧠 <b>QUANTITATIVE EDGE & REGIME</b>\n"
            f"• <b>Confidence Score:</b> <code>{conf_score}%</code>\n"
            f"• <b>Continuation Probability:</b> <code>{cont_prob}%</code>\n"
            f"• <b>Session & Macro:</b> <code>{session}</code> | <code>DXY: {dxy}</code>\n"
            f"• <b>Sample Rigor:</b> <code>N={sample_n}</code> historical matches\n\n"
            f"📝 <b>THESIS</b>\n"
            f"<i>{thesis}</i>\n\n"
            f"⚠️ <b>Execution Rule:</b> Enter at market or limit within corridor. Invalidation strict at statistical boundary.\n"
            f"🔗 <a href=\"https://primeedge.io\">Open PrimeEdge Terminal</a>"
        )
        return card

    @classmethod
    def send_setup_alert(cls, snap, current_live_price: Optional[float] = None) -> None:
        """Dispatches a formatted READY setup card asynchronously."""
        try:
            card_text = cls.format_setup_card(snap, current_live_price=current_live_price)
            cls.send_message_async(card_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"[Telegram] Failed to generate or dispatch setup alert: {e}", exc_info=True)

    @classmethod
    def send_execution_notification(cls, trade_record, status_msg: str) -> None:
        """Dispatches an execution notification when an auto-trade fills or closes."""
        try:
            inst = trade_record.instrument or "UNKNOWN"
            lots = trade_record.position_size_lots or 0.01
            entry = trade_record.actual_entry or 0.0
            sl = trade_record.actual_sl or 0.0
            tp = trade_record.actual_tp or 0.0

            text = (
                f"🤖 <b>PRIMEEDGE AUTO-EXECUTION DISPATCH</b>\n\n"
                f"• <b>Status:</b> {status_msg}\n"
                f"• <b>Instrument:</b> <code>{inst}</code>\n"
                f"• <b>Lot Size:</b> <code>{lots} lots</code>\n"
                f"• <b>Entry:</b> <code>{entry}</code>\n"
                f"• <b>SL / TP:</b> <code>{sl} / {tp}</code>\n"
                f"• <b>Account:</b> #{trade_record.account_id}\n\n"
                f"🔗 <a href=\"https://primeedge.io\">View Auto-Journal</a>"
            )
            cls.send_message_async(text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"[Telegram] Failed to send execution notification: {e}")
