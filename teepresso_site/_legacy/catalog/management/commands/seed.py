"""Seed demo data: catalog, pricing tiers, stock, staff users, sample orders.

Run:  python manage.py seed
Safe to re-run (uses get_or_create). Staff passwords are demo-only — change them.
"""
from django.core.management.base import BaseCommand

from accounts.models import User, Customer
from catalog.models import Quality, Color, Size, Product, PricingTier
from catalog.pricing import quote
from inventory.models import StockItem
from orders.models import Order, OrderItem, OrderStatusEvent, Mockup, PaymentRecord


class Command(BaseCommand):
    help = "Seed demo data for Teepresso."

    def handle(self, *args, **opts):
        # --- catalog -------------------------------------------------------
        qualities = [
            Quality.objects.get_or_create(name="140 GSM – Economy", defaults={"gsm": 140, "price_delta": 0, "sort": 1})[0],
            Quality.objects.get_or_create(name="180 GSM – Premium", defaults={"gsm": 180, "price_delta": 0, "sort": 2})[0],
            Quality.objects.get_or_create(name="240 GSM – Heavy", defaults={"gsm": 240, "price_delta": 25, "sort": 3})[0],
        ]
        colors = [
            Color.objects.get_or_create(name="Teal", defaults={"hex": "#0FB5A6"})[0],
            Color.objects.get_or_create(name="Coral", defaults={"hex": "#FF5A3C"})[0],
            Color.objects.get_or_create(name="Navy", defaults={"hex": "#2A3550"})[0],
            Color.objects.get_or_create(name="Black", defaults={"hex": "#1B2230"})[0],
            Color.objects.get_or_create(name="White", defaults={"hex": "#F4F6FA"})[0],
        ]
        sizes = []
        for i, code in enumerate(["S", "M", "L", "XL", "XXL"]):
            sizes.append(Size.objects.get_or_create(code=code, defaults={"sort": i})[0])
        products = [
            Product.objects.get_or_create(name="Round Neck", defaults={"description": "Classic everyday tee"})[0],
            Product.objects.get_or_create(name="Polo", defaults={"description": "Collared polo"})[0],
            Product.objects.get_or_create(name="Oversized", defaults={"description": "Relaxed streetwear fit"})[0],
            Product.objects.get_or_create(name="Full Sleeve", defaults={"description": "Full-sleeve tee"})[0],
        ]
        for min_qty, price in [(1, 250), (50, 210), (100, 190), (300, 175), (500, 160)]:
            PricingTier.objects.get_or_create(min_qty=min_qty, defaults={"unit_price": price})

        # --- stock ---------------------------------------------------------
        import random
        for p in products[:2]:
            for q in qualities:
                for c in colors[:3]:
                    for s in sizes:
                        StockItem.objects.get_or_create(
                            product=p, quality=q, color=c, size=s,
                            defaults={"in_stock": random.choice([0, 80, 250, 420, 600]),
                                      "reorder_level": 100},
                        )

        # --- staff users (demo) -------------------------------------------
        staff = [
            ("admin", User.Role.ADMIN, True),
            ("manager", User.Role.MANAGER, False),
            ("editor", User.Role.EDITOR, False),
            ("dispatch", User.Role.DISPATCH, False),
        ]
        for username, role, is_super in staff:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "is_staff": True, "is_superuser": is_super},
            )
            if created:
                u.set_password(username + "123")  # demo password
                u.role = role
                u.is_staff = True
                u.is_superuser = is_super
                u.save()

        # --- sample customers + orders ------------------------------------
        demo = [
            ("Rohit Sharma", "9812345678", 90, True, False, Order.Status.NEW),
            ("Priya Nair", "9876543210", 40, False, False, Order.Status.PRODUCTION),
            ("Startup Crew", "9900112233", 420, False, True, Order.Status.QC),   # bulk
            ("Anjali Mehta", "9811122233", 250, False, False, Order.Status.PRODUCTION),  # eway-ish
        ]
        for name, phone, qty, urgent, mockup, status in demo:
            cust, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
            if Order.objects.filter(customer=cust).exists():
                continue
            q = quote(qty, qualities[1].price_delta, urgent)
            o = Order(customer=cust, channel=Order.Channel.ONLINE,
                      product=products[0], quality=qualities[1], color=colors[0],
                      urgent=urgent, address="123 MG Road, Bengaluru, KA 560001",
                      wants_mockup=mockup, status=status,
                      payment_status=Order.Payment.ENQUIRY)
            o.apply_quote(q)
            o.save()
            OrderItem.objects.create(order=o, size=sizes[2], qty=qty, unit_price=q["unit_price"])
            PaymentRecord.objects.create(order=o, method="upi", status="unpaid", amount=q["total"])
            OrderStatusEvent.objects.create(order=o, status=status, note="Seed order")
            if mockup:
                Mockup.objects.create(order=o, kind="teepresso", title="Mockup requested")

        self.stdout.write(self.style.SUCCESS(
            "Seeded catalog, stock, staff (admin/manager/editor/dispatch — pw: <user>123) and sample orders."
        ))
