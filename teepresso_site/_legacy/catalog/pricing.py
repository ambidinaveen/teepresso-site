"""
Central pricing engine (REQ-CW-9/10/11).

Used by BOTH the live JS configurator (via a JSON endpoint) and server-side
order creation, so the price a customer sees is the price that gets stored —
there is a single source of truth.

All money is handled in whole rupees (int) to avoid floating-point drift.
"""
from django.conf import settings

from .models import PricingTier


def _rules():
    return settings.TEEPRESSO


def unit_price_for(qty, quality_delta=0):
    """Per-piece price for a given quantity and quality add-on."""
    qty = max(int(qty or 0), 0)
    tier = (
        PricingTier.objects.filter(min_qty__lte=qty).order_by("-min_qty").first()
        if qty > 0
        else None
    )
    base = tier.unit_price if tier else _fallback_base()
    return base + int(quality_delta or 0)


def _fallback_base():
    """If no tier matches (e.g. qty between 1 and the smallest tier), use the
    smallest defined tier price, else a safe default."""
    smallest = PricingTier.objects.order_by("min_qty").first()
    return smallest.unit_price if smallest else 250


def quote(qty, quality_delta=0, urgent=False):
    """Return a full price breakdown for an order line.

    Rules (see ANALYSIS_AND_TESTS.md):
      - urgent surcharge applies to the PRE-TAX subtotal (G2)
      - GST applies to (subtotal + urgent surcharge)
      - bulk follow-up flag when qty strictly > BULK_FOLLOWUP_QTY (BR-3)
      - E-Way flag when total (incl GST) strictly > EWAY_THRESHOLD (BR-2)
    """
    r = _rules()
    qty = max(int(qty or 0), 0)
    unit = unit_price_for(qty, quality_delta)
    subtotal = unit * qty

    urgent_charge = round(subtotal * r["URGENT_PCT"] / 100) if urgent else 0
    taxable = subtotal + urgent_charge
    gst = round(taxable * r["GST_RATE"] / 100)
    total = taxable + gst

    return {
        "qty": qty,
        "unit_price": unit,
        "subtotal": subtotal,
        "urgent": bool(urgent),
        "urgent_charge": urgent_charge,
        "gst": gst,
        "gst_rate": r["GST_RATE"],
        "total": total,
        "bulk_followup": qty > r["BULK_FOLLOWUP_QTY"],
        "needs_eway": total > r["EWAY_THRESHOLD"],
        "delivery_days": r["DELIVERY_DAYS"],
    }
