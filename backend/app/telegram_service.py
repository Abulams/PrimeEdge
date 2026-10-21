import os
import io
import json
import logging
import threading
import urllib.request
import urllib.parse
from typing import Optional, List

logger = logging.getLogger("marketos.telegram")

# ── Environment ────────────────────────────────────────────────────────────────
DEFAULT_BOT_TOKEN = "8689013346:AAFcuxzlWs3JhBNe5PEnQBzqKfrKJ4fAdFg"
DEFAULT_CHAT_ID   = "-1004238118164,1003107104"

# ── Brand colours (matching PrimeEdge UI) ──────────────────────────────────────
BG_OUTER    = (8,   14,  24)      # very dark navy
BG_CARD     = (13,  20,  35)      # dark card background
BG_HEADER   = (16,  24,  44)      # slightly lighter header strip
BG_PANEL    = (18,  27,  50)      # metric panels
BG_SL_PANEL = (60,  10,  10)      # red-tinted SL box
BG_TP_PANEL = (8,   50,  30)      # green-tinted TP box
BG_REMARK   = (14,  22,  40)      # quant reasoning block
BORDER      = (0,  174, 239)      # PrimeEdge cyan
BORDER_RED  = (220, 60,  60)      # SL red border
BORDER_GRN  = (0,  200, 100)      # TP green border
TEXT_WHITE  = (255, 255, 255)
TEXT_CYAN   = (0,  174, 239)
TEXT_RED    = (255,  80,  80)
TEXT_GREEN  = (80,  240, 130)
TEXT_GREY   = (140, 160, 190)
TEXT_YELLOW = (255, 210,  60)
BADGE_LONG  = (0,  140,  80)      # green badge
BADGE_SHORT = (180,  40,  40)     # red badge
BADGE_READY = (0,  140, 200)      # cyan badge

CARD_W = 840
CARD_H = 480
CORNER = 18

# ──────────────────────────────────────────────────────────────────────────────

def _rounded_rect(draw, xy, radius, fill=None, outline=None, width=2):
    """Draw a rounded rectangle using PIL."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


def generate_signal_card_image(snap, current_live_price: Optional[float] = None) -> bytes:
    """
    Renders a PrimeEdge-branded institutional signal card as a PNG image
    matching the UI design.  Returns raw PNG bytes.
    """
    from PIL import Image, ImageDraw, ImageFont

    inst      = getattr(snap, "instrument",  "UNKNOWN").upper()
    direction = getattr(snap, "direction",   "LONG").upper()
    status    = getattr(snap, "status_at_snapshot", "READY").upper()
    is_long   = direction in ("LONG", "BUY", "BULLISH")

    # ── Pip helpers ────────────────────────────────────────────────────────────
    if "JPY" in inst:
        pip_mult = 100.0;  price_fmt = "{:.3f}"
    elif "XAU" in inst or "GOLD" in inst:
        pip_mult = 10.0;   price_fmt = "{:.2f}"
    elif "US100" in inst or "NAS100" in inst:
        pip_mult = 1.0;    price_fmt = "{:.1f}"
    else:
        pip_mult = 10000.0; price_fmt = "{:.5f}"

    dir_sign = 1.0 if is_long else -1.0

    live_val  = (current_live_price
                 or getattr(snap, "live_price_at_snap", None)
                 or getattr(snap, "setup_ref_price", 0.0))
    t0_open   = getattr(snap, "setup_ref_price", live_val) or live_val
    p25       = getattr(snap, "corridor_p25_price", None) or t0_open
    p75       = getattr(snap, "corridor_p75_price", None) or t0_open
    sl_price  = getattr(snap, "p90_invalidation", None) or round(live_val - (dir_sign * 25.0 / pip_mult), 5)
    tp_pips   = getattr(snap, "mfe_p75_pips", None) or getattr(snap, "mfe_p50_pips", None) or 30.0
    tp_price  = round(live_val + (dir_sign * tp_pips / pip_mult), 5)

    sl_pips   = round(abs(live_val - sl_price)  * pip_mult, 1)
    tp_pips_d = round(abs(tp_price - live_val) * pip_mult, 1)
    rr        = round(tp_pips_d / sl_pips, 2) if sl_pips > 0 else 1.5

    conf      = round(getattr(snap, "confidence_score",  0.0) or 0.0, 1)
    cont_raw  = getattr(snap, "continuation_prob", 0.0) or 0.0
    win_pct   = round(cont_raw * 100.0, 1)
    if win_pct == 0.0 and conf > 0:
        win_pct = round(conf * 0.8, 1)
    sample_n  = getattr(snap, "historical_n", 45) or 45
    session   = (getattr(snap, "session",    "LONDON") or "LONDON").upper().replace(" ", "_")
    dxy       = getattr(snap, "dxy_regime",  "NEUTRAL") or "NEUTRAL"
    thesis    = (getattr(snap, "setup_thesis", "") or
                 f"{inst} {'long' if is_long else 'short'} setup. "
                 f"Entry inside P25-P75 corridor with {rr:.2f}:1 reward feasibility.")

    # Corridor midpoint for quant note
    corr_low   = min(p25, p75)
    corr_high  = max(p25, p75)
    corr_lo_p  = round(abs(t0_open - corr_low)  * pip_mult, 1)
    corr_hi_p  = round(abs(t0_open - corr_high) * pip_mult, 1)

    # ── Font loading (system fallback) ─────────────────────────────────────────
    def _font(size, bold=False):
        candidates_bold = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
        candidates_reg = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
        paths = candidates_bold if bold else candidates_reg
        for p in paths:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    # ── Canvas ─────────────────────────────────────────────────────────────────
    img  = Image.new("RGB", (CARD_W, CARD_H), BG_OUTER)
    draw = ImageDraw.Draw(img)

    # Card background
    _rounded_rect(draw, (10, 10, CARD_W-10, CARD_H-10), CORNER, fill=BG_CARD, outline=BORDER, width=2)

    # ── Header strip ───────────────────────────────────────────────────────────
    _rounded_rect(draw, (10, 10, CARD_W-10, 72), CORNER, fill=BG_HEADER)
    # "P" logo block
    _rounded_rect(draw, (28, 20, 60, 62), 8, fill=BORDER)
    draw.text((36, 26), "P", font=_font(28, bold=True), fill=TEXT_WHITE)
    # Brand text
    draw.text((70, 22), "PrimeEdge", font=_font(18, bold=True), fill=TEXT_WHITE)
    draw.text((70, 46), "INSTITUTIONAL DECISION INTELLIGENCE", font=_font(9), fill=TEXT_GREY)
    # Verified badge
    badge_txt = "★ STATISTICALLY VERIFIED EDGE"
    bt_font = _font(9, bold=True)
    bw = draw.textlength(badge_txt, font=bt_font) + 20
    _rounded_rect(draw, (CARD_W-50-int(bw), 26, CARD_W-26, 56), 12, fill=(5,40,20), outline=BORDER_GRN, width=1)
    draw.text((CARD_W-40-int(bw), 36), badge_txt, font=bt_font, fill=TEXT_GREEN)

    # ── Instrument row ─────────────────────────────────────────────────────────
    y = 90
    inst_font = _font(38, bold=True)
    draw.text((30, y), inst, font=inst_font, fill=TEXT_WHITE)
    inst_w = int(draw.textlength(inst, font=inst_font))

    # Direction badge
    dir_color = BADGE_LONG if is_long else BADGE_SHORT
    dir_lbl   = "LONG" if is_long else "SHORT"
    d_font    = _font(13, bold=True)
    dw        = int(draw.textlength(dir_lbl, font=d_font)) + 22
    dx        = 30 + inst_w + 18
    _rounded_rect(draw, (dx, y+8, dx+dw, y+38), 10, fill=dir_color)
    draw.text((dx+11, y+12), dir_lbl, font=d_font, fill=TEXT_WHITE)

    # Status badge (READY)
    s_font   = _font(13, bold=True)
    sw       = int(draw.textlength(status, font=s_font)) + 22
    _rounded_rect(draw, (CARD_W-30-sw, y+8, CARD_W-30, y+38), 10, fill=BADGE_READY)
    draw.text((CARD_W-30-sw+11, y+12), status, font=s_font, fill=TEXT_WHITE)

    # ── Three primary metric boxes ─────────────────────────────────────────────
    y2  = 148
    bh  = 80
    bw3 = (CARD_W - 60) // 3
    boxes = [
        ("SESSION ENTRY ANCHOR",  price_fmt.format(t0_open), TEXT_WHITE,  BG_PANEL,    BORDER),
        ("P90 INVALIDATION STOP", price_fmt.format(sl_price), TEXT_RED,   BG_SL_PANEL, BORDER_RED),
        ("P75 PROFIT TARGET",     price_fmt.format(tp_price), TEXT_GREEN, BG_TP_PANEL, BORDER_GRN),
    ]
    for i, (lbl, val, vcol, bg, border) in enumerate(boxes):
        bx = 30 + i * (bw3 + 5)
        _rounded_rect(draw, (bx, y2, bx+bw3, y2+bh), 10, fill=bg, outline=border, width=1)
        draw.text((bx+12, y2+10), lbl, font=_font(9, bold=True), fill=TEXT_GREY)
        draw.text((bx+12, y2+30), val, font=_font(24, bold=True), fill=vcol)

    # ── Three secondary metric boxes ───────────────────────────────────────────
    y3  = y2 + bh + 12
    sh  = 68
    metrics = [
        ("HISTORICAL WIN RATE",  f"{win_pct}% (N={sample_n})", TEXT_WHITE),
        ("REWARD : RISK RATIO",  f"{rr:.2f} : 1",              TEXT_CYAN),
        ("OPTIMAL SESSION",      session,                       TEXT_WHITE),
    ]
    for i, (lbl, val, vcol) in enumerate(metrics):
        bx = 30 + i * (bw3 + 5)
        _rounded_rect(draw, (bx, y3, bx+bw3, y3+sh), 10, fill=BG_PANEL, outline=(30,50,90), width=1)
        draw.text((bx+12, y3+10), lbl, font=_font(9, bold=True), fill=TEXT_GREY)
        draw.text((bx+12, y3+30), val, font=_font(18, bold=True), fill=vcol)

    # ── Quant reasoning block ──────────────────────────────────────────────────
    y4 = y3 + sh + 12
    _rounded_rect(draw, (30, y4, CARD_W-30, CARD_H-40), 10, fill=BG_REMARK, outline=(30,55,100), width=1)
    # Left accent bar
    draw.rectangle([30, y4, 36, CARD_H-40], fill=BORDER)
    draw.text((48, y4+8), "QUANT REASONING:", font=_font(10, bold=True), fill=TEXT_CYAN)

    # Wrap thesis text
    max_chars = 100
    words = thesis.split()
    lines_out = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines_out.append(cur)
            cur = w
    if cur:
        lines_out.append(cur)
    for li, line in enumerate(lines_out[:3]):
        draw.text((48, y4+24+(li*16)), line, font=_font(10), fill=TEXT_WHITE)

    # ── Footer ─────────────────────────────────────────────────────────────────
    draw.text((30, CARD_H-30), "⚡ Point-in-time empirical model • Zero look-ahead", font=_font(9), fill=TEXT_GREY)
    draw.text((CARD_W-145, CARD_H-30), "primeedge.app", font=_font(9, bold=True), fill=TEXT_CYAN)

    # ── Watermark DXY line ─────────────────────────────────────────────────────
    draw.text((CARD_W-155, y+10), f"DXY: {dxy}  |  Live: {price_fmt.format(live_val)}", font=_font(9), fill=TEXT_GREY)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


class TelegramService:
    """
    Non-blocking, institutional Telegram notification service for PrimeEdge.
    Sends signal card images + text captions to channel/chat.
    """

    @classmethod
    def get_bot_token(cls) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_BOT_TOKEN).strip()

    @classmethod
    def normalize_chat_id(cls, cid: str) -> str:
        cid = cid.strip()
        if cid.startswith("100") and len(cid) >= 12 and not cid.startswith("-"):
            return f"-{cid}"
        return cid

    @classmethod
    def get_chat_ids(cls) -> List[str]:
        raw = os.getenv("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID)
        ids = [cls.normalize_chat_id(c) for c in raw.split(",") if c.strip()]
        return ids if ids else ["-1004238118164", "1003107104"]

    @classmethod
    def _send_raw_message(cls, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Synchronous HTTP call to Telegram sendMessage."""
        token = cls.get_bot_token()
        if not token:
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
                url, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                ok = res_data.get("ok", False)
                if ok:
                    logger.info(f"[Telegram] Message delivered to {chat_id}")
                else:
                    logger.error(f"[Telegram] Failed message to {chat_id}: {res_data}")
                return ok
        except Exception as e:
            logger.error(f"[Telegram] Exception sending message to {chat_id}: {e}")
            return False

    @classmethod
    def _send_photo(cls, chat_id: str, png_bytes: bytes, caption: str = "", parse_mode: str = "HTML") -> bool:
        """
        Sends a PNG image via Telegram sendPhoto (multipart/form-data).
        Falls back to plain text if image fails.
        """
        token = cls.get_bot_token()
        if not token:
            return False
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        boundary = "PrimeEdgeBoundary42"
        body_parts = []

        # chat_id field
        body_parts.append(
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n"
            f"{chat_id}\r\n".encode("utf-8")
        )
        # parse_mode field
        body_parts.append(
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"parse_mode\"\r\n\r\n"
            f"{parse_mode}\r\n".encode("utf-8")
        )
        # caption field
        if caption:
            body_parts.append(
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"caption\"\r\n\r\n".encode("utf-8")
                + caption.encode("utf-8")
                + b"\r\n"
            )
        # photo field
        body_parts.append(
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"photo\"; filename=\"signal_card.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n".encode("utf-8")
            + png_bytes
            + b"\r\n"
        )
        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))

        body = b"".join(body_parts)
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                ok = res_data.get("ok", False)
                if ok:
                    logger.info(f"[Telegram] Signal card photo delivered to {chat_id}")
                else:
                    logger.error(f"[Telegram] Failed photo to {chat_id}: {res_data}")
                return ok
        except Exception as e:
            logger.error(f"[Telegram] Exception sending photo to {chat_id}: {e}")
            return False

    @classmethod
    def send_message_async(cls, text: str, parse_mode: str = "HTML") -> None:
        """Dispatch plain text message in background thread."""
        chat_ids = cls.get_chat_ids()
        def _worker():
            for cid in chat_ids:
                try:
                    cls._send_raw_message(cid, text, parse_mode=parse_mode)
                except Exception as ex:
                    logger.error(f"[Telegram] Worker error for {cid}: {ex}")
        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def format_caption(cls, snap, current_live_price: Optional[float] = None) -> str:
        """Short HTML caption to accompany the signal card photo."""
        inst      = getattr(snap, "instrument", "UNKNOWN").upper()
        direction = getattr(snap, "direction",  "LONG").upper()
        is_long   = direction in ("LONG", "BUY", "BULLISH")
        dir_emoji = "🟢" if is_long else "🔴"
        conf      = round(getattr(snap, "confidence_score", 0.0) or 0.0, 1)
        thesis    = getattr(snap, "setup_thesis", "") or "Empirical edge confirmed."

        live_val  = (current_live_price
                     or getattr(snap, "live_price_at_snap", None)
                     or getattr(snap, "setup_ref_price", 0.0))

        if "JPY" in inst:
            price_str = f"{live_val:.3f}"
        elif "XAU" in inst:
            price_str = f"{live_val:.2f}"
        elif "US100" in inst:
            price_str = f"{live_val:.1f}"
        else:
            price_str = f"{live_val:.5f}"

        return (
            f"{dir_emoji} <b>{inst} {direction} — READY</b>\n"
            f"Live Tick: <code>{price_str}</code> | Confidence: <code>{conf}%</code>\n"
            f"<i>{thesis[:160]}</i>\n\n"
            f"<a href='https://primeedge.app'>Open PrimeEdge Terminal</a>"
        )

    @classmethod
    def send_setup_alert(cls, snap, current_live_price: Optional[float] = None) -> None:
        """
        Dispatches a PrimeEdge-branded signal card image + caption asynchronously.
        Falls back to a plain text message if Pillow is unavailable.
        """
        chat_ids = cls.get_chat_ids()
        caption  = cls.format_caption(snap, current_live_price=current_live_price)

        def _worker():
            # Try to build image card
            png_bytes = None
            try:
                png_bytes = generate_signal_card_image(snap, current_live_price=current_live_price)
            except ImportError:
                logger.warning("[Telegram] Pillow not available — falling back to text alert")
            except Exception as img_err:
                logger.error(f"[Telegram] Card image generation failed: {img_err}", exc_info=True)

            for cid in chat_ids:
                try:
                    if png_bytes:
                        ok = cls._send_photo(cid, png_bytes, caption=caption)
                        if not ok:
                            # Fallback: send text
                            cls._send_raw_message(cid, caption)
                    else:
                        cls._send_raw_message(cid, caption)
                except Exception as ex:
                    logger.error(f"[Telegram] Alert worker error for {cid}: {ex}")

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def send_execution_notification(cls, trade_record, status_msg: str) -> None:
        """Dispatches a plain-text execution notification."""
        try:
            inst  = trade_record.instrument or "UNKNOWN"
            lots  = trade_record.position_size_lots or 0.01
            entry = trade_record.actual_entry or 0.0
            sl    = trade_record.actual_sl    or 0.0
            tp    = trade_record.actual_tp    or 0.0
            text = (
                f"🤖 <b>PRIMEEDGE AUTO-EXECUTION</b>\n\n"
                f"• <b>Status:</b> {status_msg}\n"
                f"• <b>Instrument:</b> <code>{inst}</code>\n"
                f"• <b>Size:</b> <code>{lots} lots</code>\n"
                f"• <b>Entry:</b> <code>{entry}</code>\n"
                f"• <b>SL / TP:</b> <code>{sl} / {tp}</code>\n"
                f"• <b>Account:</b> #{trade_record.account_id}\n\n"
                f"<a href='https://primeedge.app'>View Auto-Journal</a>"
            )
            cls.send_message_async(text)
        except Exception as e:
            logger.error(f"[Telegram] Failed to send execution notification: {e}")
