from urllib.parse import quote


def money(value):
    """₹ formatting with Indian thousands grouping."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "₹0"
    s = str(abs(n))
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    return ("-" if n < 0 else "") + "₹" + s


def wa_link(phone, text=""):
    digits = "".join(c for c in str(phone) if c.isdigit())
    return f"https://wa.me/{digits}" + (f"?text={quote(text)}" if text else "")
