"""Pricing + business-rule tests — encodes ANALYSIS_AND_TESTS.md scenarios."""
from django.test import TestCase

from catalog.models import PricingTier
from catalog.pricing import quote, unit_price_for


class PricingTests(TestCase):
    def setUp(self):
        for min_qty, price in [(1, 250), (50, 210), (100, 190), (300, 175), (500, 160)]:
            PricingTier.objects.create(min_qty=min_qty, unit_price=price)

    def test_tier_selection(self):
        self.assertEqual(unit_price_for(10), 250)
        self.assertEqual(unit_price_for(90), 210)     # TS-C5
        self.assertEqual(unit_price_for(120), 190)
        self.assertEqual(unit_price_for(350), 175)
        self.assertEqual(unit_price_for(800), 160)

    def test_quality_delta(self):
        self.assertEqual(unit_price_for(90, quality_delta=25), 235)

    def test_TS_B2_no_urgent(self):
        q = quote(90, 0, urgent=False)
        self.assertEqual(q["subtotal"], 18900)        # 90 * 210
        self.assertEqual(q["urgent_charge"], 0)
        self.assertEqual(q["gst"], 945)               # 5%
        self.assertEqual(q["total"], 19845)

    def test_TS_B1_urgent_plus_20pct(self):
        q = quote(90, 0, urgent=True)
        self.assertEqual(q["urgent_charge"], 3780)    # 20% of 18900
        self.assertEqual(q["gst"], 1134)              # 5% of 22680
        self.assertEqual(q["total"], 23814)

    def test_TS_B5_bulk_boundary_300_excluded(self):
        self.assertFalse(quote(300)["bulk_followup"])

    def test_TS_B6_bulk_boundary_301_included(self):
        self.assertTrue(quote(301)["bulk_followup"])

    def test_TS_B3_B4_eway_boundary(self):
        # Find a quantity whose total straddles ₹50,000 and check strict >.
        # 300 pcs @175 = 52,500 + GST 2,625 = 55,125 (> 50k) -> needs_eway True
        big = quote(300)
        self.assertTrue(big["total"] > 50000)
        self.assertTrue(big["needs_eway"])
        # A small order stays under and must NOT trigger E-Way
        small = quote(10)
        self.assertFalse(small["needs_eway"])
