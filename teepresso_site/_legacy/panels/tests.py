"""RBAC + flow tests — encodes TS-R*, TS-C*, TS-O* from ANALYSIS_AND_TESTS.md."""
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, Customer
from catalog.models import Quality, Color, Size, Product, PricingTier
from orders.models import Order


def make_user(username, role, superuser=False):
    u = User.objects.create(username=username, role=role, is_staff=True, is_superuser=superuser)
    u.set_password("pw")
    u.save()
    return u


class RBACTests(TestCase):
    def setUp(self):
        make_user("adm", User.Role.ADMIN, superuser=True)
        make_user("mgr", User.Role.MANAGER)
        make_user("edt", User.Role.EDITOR)
        make_user("dsp", User.Role.DISPATCH)

    def login(self, username):
        c = Client()
        self.assertTrue(c.login(username=username, password="pw"))
        return c

    def test_TS_R1_each_role_reaches_own_panel(self):
        self.assertEqual(self.login("adm").get("/panel/admin/").status_code, 200)
        self.assertEqual(self.login("mgr").get("/panel/manager/").status_code, 200)
        self.assertEqual(self.login("edt").get("/panel/editor/").status_code, 200)
        self.assertEqual(self.login("dsp").get("/panel/dispatch/").status_code, 200)

    def test_TS_R3_manager_denied_admin(self):
        self.assertEqual(self.login("mgr").get("/panel/admin/").status_code, 403)
        self.assertEqual(self.login("mgr").get("/panel/orders/").status_code, 403)

    def test_TS_R4_editor_denied_dispatch(self):
        self.assertEqual(self.login("edt").get("/panel/dispatch/").status_code, 403)

    def test_TS_R5_loggedout_redirected(self):
        resp = Client().get("/panel/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/panel/login/", resp.url)


class CustomerFlowTests(TestCase):
    def setUp(self):
        for mq, pr in [(1, 250), (50, 210), (100, 190), (300, 175), (500, 160)]:
            PricingTier.objects.create(min_qty=mq, unit_price=pr)
        self.product = Product.objects.create(name="Round Neck")
        self.quality = Quality.objects.create(name="180 GSM", gsm=180)
        self.color = Color.objects.create(name="Teal", hex="#0FB5A6")
        self.size = Size.objects.create(code="L", sort=2)

    def test_TS_C6_place_order_is_safe_enquiry(self):
        """Online order in safe mode must be an unpaid enquiry, never fake-paid."""
        c = Client()
        # register
        c.post("/register/", {"name": "Rohit", "phone": "9812345678"})
        # configure -> checkout (builds draft)
        c.post("/checkout/", {
            "product_id": self.product.id, "quality_id": self.quality.id,
            "color_id": self.color.id, f"size_{self.size.id}": "90",
        })
        # place order
        resp = c.post("/place-order/", {
            "name": "Rohit", "phone": "9812345678", "address": "MG Road, Bengaluru",
        })
        self.assertEqual(resp.status_code, 302)
        order = Order.objects.latest("created_at")
        self.assertEqual(order.qty_total, 90)
        self.assertEqual(order.payment_status, Order.Payment.ENQUIRY)  # SAFE: not paid
        self.assertEqual(order.subtotal, 18900)

    def test_design_saved_and_visible_to_staff(self):
        """Customer's text+photo design is stored and visible to editor & admin."""
        design = '{"objects":[{"type":"i-text","text":"RIDE OR DIE","fill":"#fff","fontSize":28}]}'
        preview = "data:image/png;base64,iVBORw0KGgoAAAANS"  # stand-in dataURL
        c = Client()
        c.post("/register/", {"name": "Rohit", "phone": "9812345678"})
        c.post("/checkout/", {
            "product_id": self.product.id, "quality_id": self.quality.id,
            "color_id": self.color.id, f"size_{self.size.id}": "40",
            "design_json": design, "design_preview": preview,
        })
        c.post("/place-order/", {"name": "Rohit", "phone": "9812345678", "address": "MG Road"})
        order = Order.objects.latest("created_at")
        self.assertIn("RIDE OR DIE", order.design_json)
        self.assertTrue(order.design_preview.startswith("data:image/png"))

        # admin + editor can open it
        admin = make_user("adm", User.Role.ADMIN, superuser=True)
        editor = make_user("edt", User.Role.EDITOR)
        ac = Client(); ac.login(username="adm", password="pw")
        resp = ac.get(f"/panel/orders/{order.order_no}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "RIDE OR DIE")
        ec = Client(); ec.login(username="edt", password="pw")
        self.assertEqual(ec.get("/panel/editor/").status_code, 200)

    def test_bill_auto_sent_to_whatsapp(self):
        """Placing an order auto-creates a WhatsApp bill message (queued in safe mode)."""
        from messaging.models import WhatsAppMessage
        c = Client()
        c.post("/register/", {"name": "Rohit", "phone": "9812345678"})
        c.post("/checkout/", {
            "product_id": self.product.id, "quality_id": self.quality.id,
            "color_id": self.color.id, f"size_{self.size.id}": "40",
        })
        c.post("/place-order/", {"name": "Rohit", "phone": "9812345678", "address": "MG Road"})
        order = Order.objects.latest("created_at")
        msg = WhatsAppMessage.objects.filter(order=order, kind="bill").first()
        self.assertIsNotNone(msg)                          # bill was generated
        self.assertEqual(msg.status, "queued")            # safe mode: not auto-sent
        self.assertIn("wa.me/919812345678", msg.wa_link)  # one-click send link ready
        self.assertIn(order.order_no, msg.body)
        # the public bill page renders
        self.assertEqual(c.get(f"/bill/{order.order_no}/").status_code, 200)

    def test_TS_B7_zero_qty_rejected(self):
        c = Client()
        resp = c.post("/checkout/", {
            "product_id": self.product.id, "quality_id": self.quality.id,
            "color_id": self.color.id, f"size_{self.size.id}": "0",
        })
        # bounced back to configurator (redirect), no order created
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)
