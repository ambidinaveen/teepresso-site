"""
Seed Teepresso with demo data: roles, categories, products (mirroring a
PrintMine-style corporate-gifting catalog), banners, FAQs, testimonials, blogs,
coupons and CMS pages. Idempotent — safe to run multiple times.

    python manage.py seed
"""
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from blogs.models import Blog, BlogCategory
from cart.models import Coupon
from cms.models import FAQ, Banner, Page, Testimonial
from products.models import (Brand, Category, Inventory, Product,
                             ProductVariant, Review)

User = get_user_model()


CATEGORIES = [
    ("Corporate Gifts", "gift", "Curated gifting for teams & clients", [
        "Gift Sets", "Premium Hampers"]),
    ("Apparel", "bag", "Custom t-shirts, polos & caps", [
        "Round Neck T-Shirts", "Polo T-Shirts", "Caps"]),
    ("Drinkware", "cup-straw", "Bottles, mugs & tumblers", [
        "Bottles", "Mugs"]),
    ("Office Essentials", "briefcase", "Notebooks, pens & desk items", [
        "Notebooks", "Pens", "Mobile Stands"]),
    ("Accessories", "key", "Keychains, badges & more", [
        "Metal Keychains", "Magnetic Badges"]),
    ("Printing Services", "printer", "Cards, banners & marketing print", [
        "Visiting Cards", "Standees"]),
]

# name, category(child or parent), base, sale, customizable, flags(F=featured,T=trending,B=best)
PRODUCTS = [
    ("Premium 2-in-1 Corporate Gift Set", "Gift Sets", 1099, 699, True, "FTB"),
    ("Executive Leather Diary + Pen Set", "Premium Hampers", 899, 549, True, "FB"),
    ("Diwali Premium Gift Hamper", "Premium Hampers", 1499, 999, False, "T"),
    ("Cotton Round Neck T-Shirt", "Round Neck T-Shirts", 399, 249, True, "FTB"),
    ("Dry-Fit Polo T-Shirt", "Polo T-Shirts", 549, 349, True, "FB"),
    ("Embroidered Promotional Cap", "Caps", 299, 199, True, "T"),
    ("Stainless Steel Vacuum Bottle", "Bottles", 699, 499, True, "FB"),
    ("Copper Water Bottle", "Bottles", 799, 599, True, "T"),
    ("Magic Color-Changing Mug", "Mugs", 349, 229, True, "FTB"),
    ("Ceramic Coffee Mug", "Mugs", 249, 179, True, "B"),
    ("A5 Hardbound Notebook", "Notebooks", 299, 199, True, "FT"),
    ("Eco Kraft Notebook Set", "Notebooks", 399, 279, True, ""),
    ("Metal Roller Ball Pen", "Pens", 199, 129, True, "FB"),
    ("Wooden Eco Pen", "Pens", 149, 99, True, "T"),
    ("Bamboo Mobile & Pen Stand", "Mobile Stands", 449, 299, True, "F"),
    ("Personalised Metal Keychain", "Metal Keychains", 149, 89, True, "TB"),
    ("Custom Magnetic Name Badge", "Magnetic Badges", 129, 79, True, "FT"),
    ("Premium Visiting Cards (500 pcs)", "Visiting Cards", 599, 399, True, "B"),
    ("Roll-up Standee Banner", "Standees", 1299, 899, True, "T"),
    ("Infinity Desk Calendar", "Gift Sets", 499, 349, True, "F"),
]

BANNERS = [
    ("Corporate gifting, reimagined", "Custom hampers, apparel & desk gifts with your logo — delivered PAN-India.",
     "linear-gradient(135deg,#6d28d9,#db2777)"),
    ("Bulk orders? Big savings.", "Up to 25% off on volume. Free mockups & a dedicated account manager.",
     "linear-gradient(135deg,#2563eb,#0ea5e9)"),
    ("Every gift tells a story", "From 1 to 10,000 pieces — premium quality, on time, every time.",
     "linear-gradient(135deg,#0f766e,#16a34a)"),
]

FAQS = [
    ("What is the minimum order quantity?", "Most products can be ordered from a single piece, but bulk pricing kicks in from 25+ pieces.", "Orders"),
    ("How long does delivery take?", "We deliver PAN-India in 5–7 working days. Urgent timelines available for bulk orders.", "Shipping"),
    ("Can I add my company logo?", "Yes! Open any customizable product and click Customize to upload your logo and add text.", "Customization"),
    ("Do you provide GST invoices?", "Absolutely. Add your GSTIN at checkout and you'll receive a compliant GST invoice.", "Payments"),
    ("What payment methods are accepted?", "UPI, credit/debit cards and net banking via Razorpay. Bulk orders can pay on invoice.", "Payments"),
    ("How do I get a bulk quotation?", "Use the Corporate / Request a Quotation page and our team will send a custom proposal.", "Orders"),
    ("Can I track my order?", "Yes, use the Track Order page or your account dashboard with your order number.", "Shipping"),
    ("Do you ship across India?", "Yes, we ship to all serviceable pincodes across India.", "Shipping"),
]

TESTIMONIALS = [
    ("Ananya Sharma", "HR Lead, TechCorp", "Ordered 500 welcome kits — fantastic quality and bang on time. Our new hires loved them!", True),
    ("Rohit Verma", "Founder, BrandLabs", "The customization studio made it so easy to preview our logo. Highly recommend.", True),
    ("Priya Nair", "Marketing, FinEdge", "Beautiful Diwali hampers for our clients. The team handled everything end-to-end.", True),
    ("Karan Mehta", "Event Manager", "Bulk t-shirts for our conference arrived perfectly printed. Great pricing too.", False),
    ("Sneha Iyer", "Office Admin", "Reliable, responsive and premium products. Our go-to for corporate gifting.", True),
    ("Arjun Rao", "Startup CEO", "From quote to delivery in under a week. Impressive service.", False),
]

BLOGS = [
    ("Top 10 Corporate Gifting Ideas for 2026", "Corporate Gifting",
     "Discover the most-loved corporate gifts that strengthen client and employee relationships."),
    ("Why Personalised Gifts Win Every Time", "Tips",
     "Personalisation turns an ordinary gift into a memorable brand experience. Here's the data."),
    ("A Buyer's Guide to Custom T-Shirt Printing", "Printing Guides",
     "Fabric, GSM, print methods and sizing — everything you need before placing a bulk order."),
    ("Sustainable Gifting: Eco-Friendly Picks", "Trends",
     "Bamboo, recycled paper and reusable bottles — gifts your team and the planet will thank you for."),
    ("Diwali Gifting: Plan Like a Pro", "Corporate Gifting",
     "Lead times, budgets and crowd-pleasing hampers for a stress-free festive season."),
]

PAGES = [
    ("About", "about", "<p>Teepresso is a corporate gifting & web-to-print platform helping brands "
     "delight their teams and clients. From a single custom tee to 10,000-piece orders, we handle "
     "design, print, QC, GST invoicing and PAN-India delivery.</p><p>Every gift tells a story.</p>"),
    ("Privacy Policy", "privacy-policy", "<p>We respect your privacy. We collect only the data needed "
     "to process your orders and never sell it. You can request deletion anytime.</p>"),
    ("Terms & Conditions", "terms", "<p>By using Teepresso you agree to our standard terms of sale. "
     "Personalised items are made-to-order and non-returnable unless defective.</p>"),
    ("Shipping Policy", "shipping-policy", "<p>We deliver PAN-India in 5–7 working days. Free shipping "
     "on orders above ₹999. Tracking is shared once your order is dispatched.</p>"),
]


class Command(BaseCommand):
    help = "Seed Teepresso with demo data."

    def handle(self, *args, **opts):
        random.seed(7)
        self._users()
        cat_map = self._categories()
        self._products(cat_map)
        self._cms()
        self._blogs()
        self._coupons()
        self.stdout.write(self.style.SUCCESS(
            "\n[OK] Seed complete!\n"
            "   Admin login:    admin@teepresso.in / admin12345  (dashboard at /dashboard/)\n"
            "   Customer login: demo@teepresso.in  / demo12345\n"))

    def _users(self):
        if not User.objects.filter(username="admin@teepresso.in").exists():
            u = User.objects.create_superuser(
                username="admin@teepresso.in", email="admin@teepresso.in", password="admin12345")
            u.role = User.Role.SUPER_ADMIN
            u.first_name = "Site"; u.last_name = "Admin"
            u.save()
        for email, role, name in [
            ("manager@teepresso.in", User.Role.PRODUCT_MANAGER, "Product Manager"),
            ("support@teepresso.in", User.Role.SUPPORT, "Support Exec"),
        ]:
            if not User.objects.filter(username=email).exists():
                u = User.objects.create_user(username=email, email=email, password="staff12345",
                                             role=role, first_name=name)
                u.is_staff = True; u.save()
        if not User.objects.filter(username="demo@teepresso.in").exists():
            User.objects.create_user(username="demo@teepresso.in", email="demo@teepresso.in",
                                     password="demo12345", role=User.Role.CUSTOMER,
                                     first_name="Demo", last_name="Customer", phone="9876543210")
        self.stdout.write("· users ready")

    def _categories(self):
        cat_map = {}
        for i, (name, icon, desc, children) in enumerate(CATEGORIES):
            parent, _ = Category.objects.get_or_create(
                name=name, parent=None,
                defaults={"icon": icon, "description": desc, "sort": i})
            cat_map[name] = parent
            for j, child in enumerate(children):
                c, _ = Category.objects.get_or_create(
                    name=child, parent=parent, defaults={"sort": j})
                cat_map[child] = c
        self.stdout.write(f"· {Category.objects.count()} categories")
        return cat_map

    def _products(self, cat_map):
        brand, _ = Brand.objects.get_or_create(name="Teepresso")
        for name, cat_name, base, sale, custom, flags in PRODUCTS:
            cat = cat_map.get(cat_name)
            if not cat:
                continue
            p, created = Product.objects.get_or_create(
                name=name,
                defaults=dict(
                    category=cat, brand=brand, base_price=base, sale_price=sale,
                    is_customizable=custom, min_order_qty=1 if "Card" not in name else 1,
                    short_description=f"{name} — premium quality, fully customisable with your branding.",
                    description=f"{name}. Add your company logo and text. Ideal for corporate gifting, "
                                f"events and promotions. Bulk discounts up to 25%.",
                    specifications="Material: Premium\nBranding: Logo + Text\nMOQ: 1 pc\nDelivery: 5-7 days",
                    featured="F" in flags, trending="T" in flags, best_seller="B" in flags,
                    sold_count=random.randint(5, 400), view_count=random.randint(50, 2000),
                ))
            if created:
                Inventory.objects.get_or_create(product=p, defaults={"quantity": random.randint(0, 300)})
                if "T-Shirt" in name or "Polo" in name:
                    for s in ["S", "M", "L", "XL", "XXL"]:
                        ProductVariant.objects.create(product=p, name="Size", value=s)
                    for c in ["Black", "Navy", "White", "Maroon"]:
                        ProductVariant.objects.create(product=p, name="Color", value=c)
                for _ in range(random.randint(1, 4)):
                    Review.objects.create(
                        product=p, name=random.choice(["Amit", "Neha", "Raj", "Pooja", "Vikram"]),
                        rating=random.randint(4, 5),
                        comment=random.choice([
                            "Great quality, will order again!", "Logo print was crisp and clean.",
                            "Fast delivery and good packaging.", "Loved it, team was happy."]))
        self.stdout.write(f"· {Product.objects.count()} products")

    def _cms(self):
        for i, (title, sub, grad) in enumerate(BANNERS):
            Banner.objects.get_or_create(title=title, defaults={
                "subtitle": sub, "bg_gradient": grad, "sort": i,
                "cta_text": "Shop Now", "cta_link": "/products/"})
        for i, (q, a, cat) in enumerate(FAQS):
            FAQ.objects.get_or_create(question=q, defaults={"answer": a, "category": cat, "sort": i})
        for i, (name, role, quote, corp) in enumerate(TESTIMONIALS):
            Testimonial.objects.get_or_create(name=name, defaults={
                "role": role, "quote": quote, "is_corporate": corp, "rating": 5, "sort": i})
        for title, slug, body in PAGES:
            Page.objects.get_or_create(slug=slug, defaults={"title": title, "body": body})
        self.stdout.write("· banners, FAQs, testimonials, pages")

    def _blogs(self):
        for title, cat_name, excerpt in BLOGS:
            cat, _ = BlogCategory.objects.get_or_create(name=cat_name)
            Blog.objects.get_or_create(title=title, defaults={
                "category": cat, "excerpt": excerpt,
                "body": excerpt + "\n\n" + ("Corporate gifting is one of the most effective ways to "
                "build lasting relationships. In this article we explore practical, budget-friendly "
                "ideas your team and clients will love.\n\n") * 3})
        self.stdout.write(f"· {Blog.objects.count()} blog posts")

    def _coupons(self):
        Coupon.objects.get_or_create(code="WELCOME10", defaults={
            "kind": Coupon.Kind.PERCENT, "value": 10, "min_order": 500,
            "description": "10% off your first order over ₹500"})
        Coupon.objects.get_or_create(code="BULK500", defaults={
            "kind": Coupon.Kind.FLAT, "value": 500, "min_order": 5000,
            "description": "₹500 off orders above ₹5000"})
        self.stdout.write("· coupons")
