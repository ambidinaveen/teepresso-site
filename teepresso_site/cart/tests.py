from decimal import Decimal

from django.test import TestCase

from products.models import Category, Product

from .models import Cart, Coupon


class CartTotalsTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Pens")
        self.p = Product.objects.create(name="Metal Pen", category=cat, base_price=Decimal("200"))
        self.cart = Cart.objects.create(session_key="abc")

    def test_subtotal_and_gst_and_shipping(self):
        self.cart.add(self.p, qty=2)
        self.assertEqual(self.cart.subtotal, Decimal("400.00"))
        # GST 18%
        self.assertEqual(self.cart.gst, Decimal("72.00"))
        # below free-ship threshold (999) => flat shipping 79
        self.assertEqual(self.cart.shipping, Decimal("79"))
        self.assertEqual(self.cart.total, Decimal("551.00"))

    def test_free_shipping_over_threshold(self):
        self.cart.add(self.p, qty=10)  # 2000 > 999
        self.assertEqual(self.cart.shipping, Decimal("0"))

    def test_percent_coupon(self):
        self.cart.add(self.p, qty=10)
        c = Coupon.objects.create(code="OFF10", kind=Coupon.Kind.PERCENT, value=Decimal("10"))
        self.cart.coupon = c
        self.assertEqual(self.cart.discount, Decimal("200.00"))  # 10% of 2000
        self.assertEqual(self.cart.taxable, Decimal("1800.00"))

    def test_coupon_min_order_validation(self):
        self.cart.add(self.p, qty=1)  # 200
        c = Coupon.objects.create(code="BIG", kind=Coupon.Kind.FLAT,
                                  value=Decimal("100"), min_order=Decimal("5000"))
        ok, _ = c.is_valid(self.cart.subtotal)
        self.assertFalse(ok)
