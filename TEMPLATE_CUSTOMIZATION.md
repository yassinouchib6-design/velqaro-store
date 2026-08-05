# VELQARO Template Customization

Use this project as a small Django cash-on-delivery storefront starter. Product, category, order, and media data live in the database and uploaded files; do not move that content into settings.

## Quick Local Run

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

## Store Identity

Set these values in `.env` for a new store:

```env
STORE_NAME=VELQARO
STORE_TAGLINE=Accessoires masculins en acier 316L, livres partout au Maroc. Presence forte, details precis.
STORE_META_DESCRIPTION=VELQARO - Accessoires masculins premium en acier 316L, livres partout au Maroc.
STORE_CURRENCY_LABEL=DH
STORE_FREE_DELIVERY_LABEL=Gratuite
STORE_WHATSAPP_URL=https://wa.me/212000000000
STORE_INSTAGRAM_URL=https://www.instagram.com/example/
STORE_INSTAGRAM_HANDLE=@example
VELQARO_DELIVERY_FEE=0.00
```

The shared template context exposes these values as `store_config`.

## Logo, Colors, And Images

- Text logo: change `STORE_NAME`.
- Colors and typography: edit `static/css/style.css`.
- Admin colors: edit `static/css/admin-velqaro.css`.
- Hero image: replace `static/img/velqaro-hero.png` or update `templates/shop/home.html`.
- Category card images: replace files in `static/img/` or update `shop/catalog.py`.

## Products And Categories

Manage products, categories, stock, prices, active status, featured status, and product images in Django Admin.

Current storefront behavior:

- Only active categories are public.
- Active empty categories remain visible.
- Empty category pages show the French coming-soon state.
- Products must be active and belong to an active category to be purchasable.

## Delivery

Shipping is currently free:

- `VELQARO_DELIVERY_FEE=0.00`
- `STORE_FREE_DELIVERY_LABEL=Gratuite`

Delivery page copy lives in `templates/shop/delivery.html`.

## WhatsApp And Instagram

Set:

- `STORE_WHATSAPP_URL`
- `STORE_INSTAGRAM_URL`
- `STORE_INSTAGRAM_HANDLE`

These feed the navbar/footer/contact areas where reusable.

## Telegram Notifications

Set:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Notification code lives in `shop/notifications.py`. It keeps checkout working even if Telegram fails.

## Email Notifications

Set:

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_USE_SSL`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `ORDER_NOTIFICATION_EMAIL`

Use the safe SMTP test command only after `.env` is configured:

```powershell
.\venv\Scripts\python.exe manage.py test_order_email
```

## Legal Pages

No dedicated legal pages are currently implemented. Add them as normal Django views/templates and link them from `templates/components/footer.html`.

## Normally Customized Files For A New Client

- `.env`
- `static/css/style.css`
- `static/css/admin-velqaro.css`
- `static/img/`
- `templates/shop/home.html`
- `templates/shop/delivery.html`
- `templates/components/footer.html`
- `shop/catalog.py`
- Products, categories, and images in Django Admin

## Project Structure Map

- `config/`: Django settings, root URLs, ASGI/WSGI.
- `shop/`: active ecommerce app with models, cart, checkout, notifications, admin, tests, and catalog helpers.
- `templates/base.html`: shared HTML shell.
- `templates/components/`: reusable navbar, footer, product card, cart card, summary card, forms, and empty states.
- `templates/shop/`: storefront pages.
- `templates/admin/`: Django Admin override.
- `static/css/style.css`: storefront CSS.
- `static/css/admin-velqaro.css`: admin theme CSS.
- `static/js/main.js`: mobile menu, gallery, quantity controls, sliders, reveal animations.
- `media/`: uploaded product images.
- `core/`, `products/`, `orders/`, `accounts/`: empty starter apps. Keep them temporarily or remove them in a separate dedicated cleanup after confirming they are not needed.
