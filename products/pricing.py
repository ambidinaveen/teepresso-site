"""
Quantity-slab bulk pricing — carried over from the original Teepresso pricing
engine. Larger quantities earn a per-unit discount, which is what makes the
"From ₹X" corporate-gifting pricing work.
"""
from decimal import Decimal

# (min_qty, discount_pct off unit price)
SLABS = [(1, 0), (25, 5), (50, 10), (100, 15), (300, 20), (1000, 25)]


def unit_price_for_qty(base_unit, qty):
    base = Decimal(str(base_unit))
    disc = 0
    for min_qty, pct in SLABS:
        if qty >= min_qty:
            disc = pct
    return (base * (Decimal(100 - disc) / Decimal(100))).quantize(Decimal("0.01"))


def quote(base_unit, qty, variant_delta=0):
    """Return a pricing breakdown dict for `qty` units at `base_unit` (+ variant delta)."""
    qty = max(int(qty or 0), 0)
    unit = unit_price_for_qty(Decimal(str(base_unit)) + Decimal(str(variant_delta or 0)), qty)
    subtotal = (unit * qty).quantize(Decimal("0.01"))
    return {
        "qty": qty,
        "unit_price": float(unit),
        "subtotal": float(subtotal),
        "discount_pct": _disc_for(qty),
    }


def _disc_for(qty):
    disc = 0
    for min_qty, pct in SLABS:
        if qty >= min_qty:
            disc = pct
    return disc
