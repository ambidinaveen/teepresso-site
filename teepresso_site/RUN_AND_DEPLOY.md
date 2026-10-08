# Teepresso — How to Run & Deploy

A plain-English guide, in three parts:

- **Part A** — run on your computer (to see/test it).
- **Part B** — run the full stack with **Docker** (web + worker + Postgres + Redis + Nginx).
- **Part C** — put it live on an **Ubuntu VPS** with HTTPS.

> 💡 **Safe by default.** Until you connect a real payment gateway, checkout records an
> *enquiry* (no money taken) or uses a clearly-labelled demo simulator; WhatsApp uses
> safe click-links; SMS is logged; no fake E-Way bill is ever created. Safe to launch
> before those accounts are ready.

---

# PART A — Run on your computer (Windows / Mac / Linux)

```bash
cd teepresso_site
python -m venv venv
# Windows:  venv\Scripts\activate      Mac/Linux:  source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver
```

- Storefront: **http://127.0.0.1:8000/**
- Customer account: **/accounts/login/** (`demo@teepresso.in` / `demo12345`)
- Admin dashboard: **/dashboard/** (`admin@teepresso.in` / `admin12345`)
- Django admin: **/django-admin/**

Run the tests anytime: `python manage.py test`.

---

# PART B — Docker (recommended for staging/production)

1. Install Docker Desktop / Docker Engine + Compose.
2. Copy and edit the environment file:
   ```bash
   cp .env.example .env       # set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, POSTGRES_PASSWORD…
   ```
3. Build & start everything:
   ```bash
   docker compose up --build -d
   ```
   The entrypoint waits for Postgres, runs migrations, collects static, and seeds the
   catalog the first time. Site is served by Nginx on **http://localhost/**.
4. Useful commands:
   ```bash
   docker compose logs -f web
   docker compose exec web python manage.py createsuperuser
   docker compose down            # stop (data persists in volumes)
   ```

Containers: `web` (Gunicorn), `worker` (Celery), `db` (PostgreSQL 16),
`redis`, `nginx`.

---

# PART C — Ubuntu VPS go-live

1. Point your domain's DNS A-records to the server IP.
2. Install Docker + Compose, clone the repo, create `.env` (set real
   `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED`, `DJANGO_DEBUG=0`, secrets).
3. `docker compose up --build -d`.
4. **HTTPS:** put a TLS-terminating proxy in front (e.g. Caddy, or add Certbot to the
   Nginx container) and forward to port 80. Once HTTPS is on, Django's production
   hardening (HSTS, secure cookies, SSL redirect) auto-activates because `DEBUG=0`.
5. **Backups:** schedule `pg_dump` of the `db` volume daily; back up the `media` volume.
6. **Monitoring:** tail `docker compose logs`, and add Sentry via env if desired.

### Turning integrations on (only when ready)
Set these in `.env` and restart:
- `RAZORPAY=1` + `RAZORPAY_KEY_ID/SECRET` → live online payments.
- `WHATSAPP_MODE=api` + tokens → automatic WhatsApp messages.
- `SMS_API=1`, `EWAY_API=1`, `OTP_VERIFY=1` → real SMS / E-Way / OTP.
- `EMAIL_HOST=…` → real transactional email (otherwise emails print to the log).

Each stays safely off until you set it.
