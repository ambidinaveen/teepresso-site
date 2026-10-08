"""Small safe helpers (no third-party calls)."""
from urllib.parse import quote_plus


def wa_link(phone, text=""):
    """Build a safe Click-to-WhatsApp (wa.me) link. No API, no automation,
    so there is zero risk of a number ban. Staff clicks it to message manually."""
    digits = "".join(c for c in str(phone) if c.isdigit())
    if digits and not digits.startswith("91") and len(digits) == 10:
        digits = "91" + digits  # default India country code
    base = f"https://wa.me/{digits}"
    return f"{base}?text={quote_plus(text)}" if text else base
