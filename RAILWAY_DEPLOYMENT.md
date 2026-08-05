# Railway Deployment Plan

This guide prepares VELQARO for Railway without deploying automatically. Do not run production imports twice on the same PostgreSQL database unless you intentionally reset or recreate the target database first.

## Target Architecture

- Railway web service running Django with Gunicorn.
- Railway PostgreSQL connected through `DATABASE_URL`.
- HTTPS handled by Railway.
- Static files collected into `STATIC_ROOT` and served by WhiteNoise.
- Uploaded media stored on a Railway Volume mounted at `/data/media`.

## Required Railway Variables

Set these in Railway, never in Git:

```env
SECRET_KEY=replace-with-a-real-production-secret-key
DEBUG=False
ALLOWED_HOSTS=your-app.up.railway.app,www.example.com
CSRF_TRUSTED_ORIGINS=https://your-app.up.railway.app,https://www.example.com
DATABASE_URL=${{Postgres.DATABASE_URL}}
DATABASE_SSL_REQUIRE=True
DATABASE_CONN_MAX_AGE=600
DATABASE_CONN_HEALTH_CHECKS=True
STATIC_URL=/static/
STATIC_ROOT=staticfiles
MEDIA_URL=media/
MEDIA_ROOT=/data/media
VELQARO_DELIVERY_FEE=0.00
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY=strict-origin-when-cross-origin
X_FRAME_OPTIONS=DENY
USE_X_FORWARDED_PROTO=True
```

Also set the existing email, Telegram, and store customization variables from `.env.example`.

## Build Command

Railway/Nixpacks usually installs dependencies automatically from `requirements.txt`. If you configure explicit commands, use:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

## Start Command

The project includes a `Procfile`:

```bash
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

## Migration Command

Run migrations after the PostgreSQL database exists:

```bash
python manage.py migrate
```

For the first deployment, run this manually or as a Railway pre-deploy command after confirming `DATABASE_URL` points to the new Railway PostgreSQL database. Do not run `makemigrations` in production.

## Media Strategy

Railway's normal application filesystem should be treated as temporary. Uploaded product images must not depend on it.

Recommended first-deployment strategy:

- Add a Railway Volume to the web service.
- Mount it at `/data`.
- Set `MEDIA_ROOT=/data/media`.
- Copy the existing local `media/` contents into `/data/media`.

Long-term alternative:

- Move production media to external object storage.
- Keep local `media/` only for development.
- Update Django storage settings in a separate, dedicated change.

## Backup Local SQLite And Media

Run from the project root on Windows:

```powershell
New-Item -ItemType Directory -Force backups
Copy-Item -LiteralPath .\db.sqlite3 -Destination ".\backups\db-$(Get-Date -Format yyyyMMdd-HHmmss).sqlite3"
robocopy .\media ".\backups\media-$(Get-Date -Format yyyyMMdd-HHmmss)" /E
```

`robocopy` can return `1` when files copied successfully.

## Dump SQLite Data

Create a JSON dump from the current local SQLite database:

```powershell
New-Item -ItemType Directory -Force backups
.\venv\Scripts\python.exe manage.py dumpdata shop auth.User --natural-foreign --natural-primary --indent 2 > .\backups\sqlite-to-postgres-data.json
```

This includes categories, products, product images, orders, order items, and admin users. It excludes generated static files and uploaded media binaries.

## Create Railway PostgreSQL

1. Add a PostgreSQL service in Railway.
2. Connect it to the Django web service.
3. Confirm the web service has `DATABASE_URL`.
4. Confirm `DEBUG=False`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` are set.

## Run Migrations On PostgreSQL

After the Railway variables are configured:

```bash
python manage.py migrate
```

Verify migrations completed before loading data.

## Load Data Into PostgreSQL

Only load into an empty migrated PostgreSQL database:

```bash
python manage.py loaddata sqlite-to-postgres-data.json
```

Avoid duplicate data:

- Do not repeat `loaddata` on a database that already contains the imported rows.
- If you must retry, use a fresh PostgreSQL database or intentionally clear the target after taking a backup.
- Never clear the local SQLite database.

## Copy Or Upload Media

Copy local `media/` to the Railway Volume path `/data/media`.

Options depend on your Railway access workflow:

- Upload a zip/archive through an interactive shell or Railway-supported file transfer process.
- Use a one-time migration job or shell command after attaching the volume.
- For object storage later, upload the same files to the bucket and change storage settings separately.

After copying, verify that product image paths from the database exist under `/data/media`.

## Verification Checklist

After migrations, data load, and media copy:

```bash
python manage.py check
python manage.py check --deploy
python manage.py shell -c "from shop.models import Category, Product, ProductImage, Order, OrderItem; print(Category.objects.count(), Product.objects.count(), ProductImage.objects.count(), Order.objects.count(), OrderItem.objects.count())"
```

Then manually verify:

- Homepage
- Shop page
- Empty active categories
- Product detail images
- Cart
- Checkout
- Order success page
- Django Admin login
- Admin product/order search and filters
- Telegram notification after a controlled test order
- Email notification after a controlled test order

## HSTS

Keep `SECURE_HSTS_SECONDS=0` until the final Railway/custom HTTPS domain is confirmed. Increase it gradually only after HTTPS works for all required domains and subdomains.
