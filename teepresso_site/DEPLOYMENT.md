# Teepresso — Production Deployment Guide

This guide deploys Teepresso to a production server using **Docker Compose** (the
recommended path) on an **Ubuntu VPS**, with HTTPS, backups, monitoring, scaling and a
security checklist. For a gentler walkthrough see [RUN_AND_DEPLOY.md](RUN_AND_DEPLOY.md).

Stack deployed: **Nginx → Gunicorn/Django (`web`) + Celery (`worker`) + PostgreSQL +
Redis**, defined in [`docker-compose.yml`](docker-compose.yml).

---

## 0. Prerequisites
- A Linux server (Ubuntu 22.04/24.04 LTS, 2 vCPU / 2–4 GB RAM is plenty to start).
- A domain name with DNS **A / AAAA** records pointing at the server's IP.
- Docker Engine + Docker Compose plugin.
- Ports **80** and **443** open in the firewall.

```bash
# Install Docker + Compose (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
docker --version && docker compose version
```

---

## 1. Get the code & configure the environment
```bash
git clone <your-repo-url> teepresso && cd teepresso/teepresso_site
cp .env.example .env
nano .env
```

Set **at minimum** for production:
```ini
DJANGO_SECRET_KEY=<a long random string>      # python -c "import secrets;print(secrets.token_urlsafe(64))"
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=teepresso.in,www.teepresso.in
DJANGO_CSRF_TRUSTED=https://teepresso.in,https://www.teepresso.in
DJANGO_SSL_REDIRECT=1

POSTGRES_DB=teepresso
POSTGRES_USER=teepresso
POSTGRES_PASSWORD=<strong password>
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
DEFAULT_FROM_EMAIL=Teepresso <hello@teepresso.in>
```

> When `DJANGO_DEBUG=0`, Django **auto-enables** HSTS, secure cookies, content-type
> nosniff, `X-Frame-Options: DENY` and SSL redirect (see `config/settings.py`).
> Leave all integration flags (`RAZORPAY`, `WHATSAPP_MODE=api`, `SMS_API`, `EWAY_API`,
> `OTP_VERIFY`) off until you have real, tested credentials.

---

## 2. Build & launch
```bash
docker compose up --build -d
docker compose ps                 # all services healthy?
docker compose logs -f web        # watch first-boot migrate/collectstatic/seed
```
On first boot the `web` entrypoint:
1. waits for PostgreSQL, 2. runs `migrate`, 3. runs `collectstatic`,
4. seeds demo data **only if the catalog is empty**, 5. starts Gunicorn.

Create your own admin and remove the demo accounts:
```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell -c \
  "from accounts.models import User; User.objects.filter(email__endswith='@teepresso.in', is_superuser=False).delete()"
```

The site is now served by Nginx on **port 80**.

---

## 3. HTTPS / TLS
Pick one:

### Option A — Caddy (simplest, automatic certificates)
Replace the `nginx` service in `docker-compose.yml` with Caddy, or put Caddy in front:
```caddyfile
# /etc/caddy/Caddyfile
teepresso.in, www.teepresso.in {
    reverse_proxy localhost:80
}
```
Caddy fetches & renews Let's Encrypt certs automatically.

### Option B — Certbot with the existing Nginx
```bash
sudo apt install certbot python3-certbot-nginx
# point a host Nginx at the container, then:
sudo certbot --nginx -d teepresso.in -d www.teepresso.in
```
Certbot installs the cert and sets up auto-renewal (`certbot renew` via systemd timer).

After HTTPS is live, confirm `DJANGO_SSL_REDIRECT=1` and `DJANGO_CSRF_TRUSTED` use
`https://` URLs, then `docker compose restart web`.

---

## 4. Backups
**Database (daily):**
```bash
# add to crontab -e
0 2 * * * cd /home/USER/teepresso/teepresso_site && \
  docker compose exec -T db pg_dump -U teepresso teepresso | gzip > \
  /home/USER/backups/teepresso-$(date +\%F).sql.gz
```
Restore:
```bash
gunzip -c backup.sql.gz | docker compose exec -T db psql -U teepresso -d teepresso
```

**Uploaded media** lives in the `media` Docker volume — back it up too:
```bash
docker run --rm -v teepresso_site_media:/data -v $PWD:/out alpine \
  tar czf /out/media-$(date +%F).tgz -C /data .
```
Store backups off-server (S3, another host). Test a restore periodically.

---

## 5. Updating (near zero-downtime)
```bash
git pull
docker compose build web worker
docker compose up -d web worker          # recreates only changed services
docker compose exec web python manage.py migrate --noinput
```
Migrations and `collectstatic` also run automatically via the entrypoint on container
start. For schema changes that aren't backward-compatible, take a maintenance window.

---

## 6. Scaling & performance
- **More web workers:** the Gunicorn `CMD` runs `3 workers × 2 threads`. Rule of thumb:
  `workers = 2 × CPU + 1`. Tune in the `Dockerfile` CMD or override in compose.
- **Horizontal scale:** `docker compose up -d --scale web=3` and let Nginx load-balance
  (add the replicas to the `upstream` block, or use a Swarm/Kubernetes ingress).
- **Caching:** `REDIS_URL` enables Django's Redis cache and the Celery broker.
- **Static/media:** served by Nginx with far-future cache headers; move media to S3 /
  Cloudinary for multi-node setups (swap the storage backend in `config/settings.py`).
- **Database:** use a managed Postgres (or a tuned standalone) for production load.

---

## 7. Monitoring & logs
```bash
docker compose logs -f --tail=200 web worker nginx
docker stats                              # live CPU/memory per container
docker inspect --format '{{.State.Health.Status}}' $(docker compose ps -q web)
```
- Gunicorn access/error logs stream to stdout (captured by `docker compose logs`).
- The in-app **Audit Log** (`/dashboard/audit/`) records sensitive POSTs + a notification
  delivery log.
- Add **Sentry** for error tracking: `pip` already isolated — set `SENTRY_DSN` and wire
  `sentry_sdk.init()` in `config/settings.py` if desired.

---

## 8. Production security checklist
- [ ] `DJANGO_DEBUG=0` and a strong unique `DJANGO_SECRET_KEY`.
- [ ] `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED` set to your real domain(s).
- [ ] HTTPS enabled; `DJANGO_SSL_REDIRECT=1` (HSTS + secure cookies auto-on).
- [ ] Default demo logins removed; real admin created with a strong password.
- [ ] Strong `POSTGRES_PASSWORD`; DB **not** exposed publicly (no host port mapping on `db`).
- [ ] Firewall allows only 80/443 (+ SSH); fail2ban or key-only SSH.
- [ ] Daily DB + media backups verified by a test restore.
- [ ] Integrations enabled only with real, tested credentials (Razorpay in live mode,
      WhatsApp API approved, SMS/E-Way accounts provisioned).
- [ ] `client_max_body_size` in `deploy/nginx.conf` matches your max upload (default 25M).
- [ ] Container runs as non-root (already configured in the Dockerfile).

---

## 9. Bare-metal alternative (no Docker)
If you prefer Gunicorn + systemd directly on the host:
1. Create a venv, `pip install -r requirements.txt`, set env vars (e.g. in
   `/etc/teepresso.env`).
2. `python manage.py migrate && python manage.py collectstatic --noinput`.
3. Use **`deploy/gunicorn.service`** (systemd unit, Unix socket) and point
   **`deploy/nginx.conf`** at the socket (swap the `proxy_pass` and `alias` paths as noted
   in that file's header comments).
4. `sudo certbot --nginx` for HTTPS.

---

## 10. Common issues
| Symptom | Fix |
|---------|-----|
| `502 Bad Gateway` from Nginx | `web` not up yet / crashed — `docker compose logs web`. |
| `DisallowedHost` (400) | Add the domain to `DJANGO_ALLOWED_HOSTS`. |
| CSRF "Origin checking failed" | Add `https://yourdomain` to `DJANGO_CSRF_TRUSTED`. |
| CSS/JS 404 in prod | Ensure `collectstatic` ran and Nginx serves `/static/`. |
| Uploads rejected (413) | Raise `client_max_body_size` in `deploy/nginx.conf`. |
| Celery tasks not running | Ensure `REDIS_URL` is set and the `worker` service is up. |
