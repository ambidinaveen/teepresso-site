# Teepresso — Web-to-Print & Corporate Gifting Platform

An enterprise **web-to-print + corporate-gifting e-commerce platform**, built to the
**PRINTPROX** specification and modelled on [printmine.in](https://printmine.in/).
It lets customers browse a multi-category catalog, personalise products with their
logo/text, order online, pay, request bulk quotations and track orders — backed by a
full admin dashboard for products, inventory, orders, leads, CMS, reports and analytics.

> **🔒 Safe by default.** Every paid/external integration (Razorpay, WhatsApp, SMS,
> E-Way Bill, OTP) is behind a feature flag that is **OFF** until you connect real,
> tested credentials. Checkout records an *unpaid enquiry* (or uses a clearly-labelled
> demo simulator) — it **never fakes a payment** or issues a fake government bill.

---

## Table of contents
1. [Tech stack](#tech-stack)
2. [Feature overview](#feature-overview)
3. [Architecture](#architecture)
4. [Project structure](#project-structure)
5. [Quick start (local)](#quick-start-local)
6. [Run with Docker](#run-with-docker)
7. [Environment variables](#environment-variables)
8. [Demo logins](#demo-logins)
9. [Key URLs](#key-urls)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)
12. [Deployment](#deployment)

---

## Tech stack
| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, Django 5/6, Django ORM & templates |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript (ES6), jQuery, AJAX |
| UI extras | Bootstrap Icons, Google Fonts, AOS (animations), Chart.js, Fabric.js |
| Database | PostgreSQL (prod) · SQLite (dev) |
| Cache / queue | Redis + Celery |
| Payments | Razorpay (safe-stub by default) |
| Serving | Gunicorn + Nginx + WhiteNoise |
| Deploy | Docker + Docker Compose |

## Feature overview
- **Storefront** — hero slider, category mega-menu, AJAX live search, product filters
  (category / price / brand / sort), product detail (gallery, variants, specs, reviews),
  quick-view, wishlist, "From ₹X" bulk pricing.
- **Customization studio** — upload logo + add text/font/size/colour/print-position on a
  Fabric.js canvas with live preview; admin design-approval workflow.
- **Cart & checkout** — AJAX cart, coupons, GST, shipping rules, quantity-slab discounts.
- **Orders** — workflow `Pending → Confirmed → Processing → Printing → Packaging →
  Shipped → Delivered`, GST invoice, tracking timeline, auto E-Way flag above ₹50,000.
- **Corporate module** — bulk quotation requests → lead pipeline (assign / status / notes).
- **Accounts** — email **or** mobile login, registration, OTP password reset, customer
  dashboard, orders, wishlist, saved designs, addresses, profile.
- **Admin dashboard** — analytics (revenue, orders, conversion, monthly sales, top
  products via Chart.js), product / inventory / customer / coupon CRUD, design approvals,
  CMS (banners, FAQ, testimonials, blog, pages), CSV reports (sales / GST / products /
  customers), audit log — all **role-gated (RBAC)**.
- **Notifications** — email (console backend in dev) + WhatsApp (wa.me links) + SMS
  (logged), every message recorded in a delivery log.
- **AI (rule-based, offline, no API cost)** — product recommendations + "Teebot" support
  chatbot over the FAQ knowledge base.
- **Security** — Django auth, CSRF, XSS/SQLi protection via ORM/templates, RBAC, audit
  log, password hashing, and auto-applied HTTPS/HSTS/secure-cookie hardening in production.

## Architecture
```
            ┌──────────────────────────────────────────────┐
  Browser ─►│  Nginx  (TLS, static /media, reverse proxy)   │
            └───────────────┬──────────────────────────────┘
                            │ http
            ┌───────────────▼──────────────────────────────┐
            │  web: Gunicorn → Django (config.wsgi)         │
            │  storefront · products · cart · orders ·      │
            │  payments · quotations · blogs · cms ·        │
            │  notifications · accounts · dashboard · core   │
            └───┬──────────────┬───────────────┬───────────┘
                │              │               │
        ┌───────▼──┐   ┌───────▼──┐    ┌───────▼─────────┐
        │ Postgres │   │  Redis   │◄───│ worker: Celery  │
        └──────────┘   └──────────┘    │ (async jobs)    │
                                        └─────────────────┘
   External (all OFF by default): Razorpay · WhatsApp · SMS · E-Way
```

## Project structure
```
teepresso_site/
├── config/         settings (safety flags), urls, wsgi/asgi, celery
├── core/           AuditLog, context processor, middleware, AI (recommend + chatbot)
├── accounts/       User + roles, addresses, wishlist, OTP, auth (email/mobile)
├── products/       Category/Brand/Product/variants/images/videos/reviews/inventory/customdesign
├── cart/           Cart, CartItem, Coupon (AJAX)
├── orders/         Order, OrderItem, status events, Invoice, checkout/tracking
├── payments/       Payment + Razorpay safe stub
├── quotations/     CorporateLead (bulk quote requests)
├── blogs/          Blog + categories
├── cms/            Banner, FAQ, Testimonial, Page, Newsletter, ContactMessage, chatbot
├── notifications/  Notification model + email/WhatsApp/SMS safe stubs
├── dashboard/      custom admin (analytics, CRUD, reports, audit) + RBAC
├── storefront/     home page
├── templates/      base, partials, store/*, account/*, auth/*, blogs/*, cms/*, dashboard/*
├── static/         css (style/responsive/animations), js (main/cart/products/chatbot), fabric.min.js
├── deploy/         Dockerfile entrypoint, nginx.conf, gunicorn.service, deploy notes
├── Dockerfile · docker-compose.yml · .dockerignore
├── requirements.txt · .env.example
└── _legacy/        previous t-shirt-only build, kept for reference
```

## Quick start (local)
```bash
cd teepresso_site
python -m venv venv
# Windows:  venv\Scripts\activate      Mac/Linux:  source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # demo catalog, banners, blogs, coupons, users
python manage.py runserver
```
Runs on SQLite with `DEBUG=1` — no database or credentials needed.

## Run with Docker
Full stack (`web` + `worker` + `db` + `redis` + `nginx`):
```bash
cp .env.example .env           # set DJANGO_SECRET_KEY, ALLOWED_HOSTS, POSTGRES_PASSWORD…
docker compose up --build      # site on http://localhost/
```
On first boot the entrypoint waits for Postgres, migrates, collects static and seeds the
catalog automatically. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for production details.

```bash
docker compose logs -f web                          # tail logs
docker compose exec web python manage.py createsuperuser
docker compose down                                 # stop (data persists in volumes)
```

## Environment variables
All are optional in dev (sane defaults); set them for production in `.env`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | dev key | **Set a long random value in prod.** |
| `DJANGO_DEBUG` | `1` | `0` in prod (enables security hardening). |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated domains. |
| `DJANGO_CSRF_TRUSTED` | — | `https://yourdomain.com,…` |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | — | Use Postgres when set; else SQLite. |
| `REDIS_URL` | — | Cache + Celery broker; else Celery runs inline (eager). |
| `EMAIL_HOST` (+ PORT/USER/PASSWORD/TLS) | — | Real SMTP; else emails print to console. |
| `RAZORPAY` + `RAZORPAY_KEY_ID/SECRET` | `0` | Live online payments. |
| `WHATSAPP_MODE` (+ token/phone id) | `link` | `link` = safe wa.me · `api` = Business API. |
| `SMS_API` | `0` | Real SMS gateway (else OTP/alerts are logged). |
| `EWAY_API` | `0` | E-Way Bill API (else over-₹50k orders are flagged). |
| `OTP_VERIFY` | `0` | Enforce OTP at register/reset (else code shown on screen). |

## Demo logins
Created by `python manage.py seed` — **change before production**.

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `admin@teepresso.in` | `admin12345` |
| Product Manager | `manager@teepresso.in` | `staff12345` |
| Support | `support@teepresso.in` | `staff12345` |
| Customer | `demo@teepresso.in` | `demo12345` |

## Key URLs
| Page | Path |
|------|------|
| Storefront | `/` |
| Shop / catalog | `/products/` |
| Corporate quote | `/quotations/` |
| Blog | `/blog/` |
| Track order | `/track/` |
| Customer login / account | `/accounts/login/`, `/accounts/` |
| Admin dashboard | `/dashboard/` |
| Django admin | `/django-admin/` |

## Testing
```bash
python manage.py test          # pricing, cart/coupons, order workflow, AI, RBAC (17 tests)
```

## Troubleshooting
- **`DisallowedHost` / 400** — add the host to `DJANGO_ALLOWED_HOSTS`.
- **Static files missing in prod** — run `python manage.py collectstatic` (the Docker
  entrypoint does this automatically).
- **Emoji crash in a management command on Windows** — the console is cp1252; keep
  command output ASCII (the project already does).
- **Payments don't charge** — that's intentional: set `RAZORPAY=1` + keys to enable.

## Deployment
See **[DEPLOYMENT.md](DEPLOYMENT.md)** for a full production guide (Docker on an Ubuntu
VPS, HTTPS, backups, scaling, monitoring, security checklist, zero-downtime updates) and
**[RUN_AND_DEPLOY.md](RUN_AND_DEPLOY.md)** for a plain-English quick version.
