# Deploying Teepresso to a GoDaddy VPS (Ubuntu)

This is the safe, standard Python production setup: **PostgreSQL + Gunicorn + Nginx + HTTPS**.
Everything risky (payments, WhatsApp, E-Way, courier) stays OFF until you switch it on.

> Prerequisite: a **GoDaddy VPS** (Ubuntu 22.04) with SSH access and your domain's
> DNS **A-record** pointed at the VPS IP.

## 1. One-time server setup
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql nginx git
sudo -u postgres psql -c "CREATE DATABASE teepresso;"
sudo -u postgres psql -c "CREATE USER teepresso WITH PASSWORD 'change-me';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE teepresso TO teepresso;"
sudo adduser --disabled-password --gecos "" teepresso
```

## 2. Get the code + virtualenv
```bash
sudo su - teepresso
git clone <your-repo> teepresso_site      # or upload the folder via scp/SFTP
cd teepresso_site
python3 -m venv ~/venv
~/venv/bin/pip install -r requirements.txt
~/venv/bin/pip install gunicorn psycopg2-binary
```

## 3. Configure environment (secrets stay here, never in code)
```bash
cp .env.example .env
nano .env        # set DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS,
                 # POSTGRES_* . Leave ONLINE_PAYMENTS / EWAY_API / COURIER_API = 0.
```

## 4. Database + static
```bash
set -a; source .env; set +a
~/venv/bin/python manage.py migrate
~/venv/bin/python manage.py collectstatic --noinput
~/venv/bin/python manage.py createsuperuser     # your real admin login
# optional first-time demo data: ~/venv/bin/python manage.py seed
```

## 5. Gunicorn service + Nginx
```bash
exit                                  # back to a sudo user
sudo cp /home/teepresso/teepresso_site/deploy/gunicorn.service /etc/systemd/system/teepresso.service
sudo systemctl daemon-reload && sudo systemctl enable --now teepresso

sudo cp /home/teepresso/teepresso_site/deploy/nginx.conf /etc/nginx/sites-available/teepresso
sudo ln -s /etc/nginx/sites-available/teepresso /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

## 6. HTTPS (free, automatic)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
Your site is now live at `https://yourdomain.com`.

## 7. Backups (do this!)
```bash
# nightly DB dump via cron
0 2 * * * pg_dump teepresso | gzip > /home/teepresso/backups/teepresso-$(date +\%F).sql.gz
```

---

## Turning integrations ON later (safely)
1. Sign up + get credentials (Razorpay/Cashfree, WhatsApp BSP, GSP, courier).
2. **Test in the provider's sandbox first.**
3. Implement the real call at the single marked swap-in point in the code:
   - payments → `storefront/views.py` `place_order()` (the `ONLINE_PAYMENTS` branch)
   - E-Way → `panels/views.py` `dispatch_process()` (the `EWAY_API` branch)
   - WhatsApp → `storefront/utils.py` (`wa_link` → real API send)
4. Flip the flag in `.env` (e.g. `ONLINE_PAYMENTS=1`), `systemctl restart teepresso`.

Until you do all four, the site stays safe: no fake payments, no fake bills, no bans.

## Updating after code changes
```bash
sudo su - teepresso
cd teepresso_site && git pull
~/venv/bin/pip install -r requirements.txt
set -a; source .env; set +a
~/venv/bin/python manage.py migrate
~/venv/bin/python manage.py collectstatic --noinput
exit
sudo systemctl restart teepresso
```
