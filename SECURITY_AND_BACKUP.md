# VELQARO Security And Backup Notes

This project is not deployed yet. Keep `db.sqlite3`, `.env`, and uploaded files private unless the hosting plan explicitly requires a different workflow.

## Back up the local SQLite database

Run from the project root:

```powershell
New-Item -ItemType Directory -Force backups
Copy-Item -LiteralPath .\db.sqlite3 -Destination ".\backups\db-$(Get-Date -Format yyyyMMdd-HHmmss).sqlite3"
```

## Back up uploaded media

Run from the project root:

```powershell
New-Item -ItemType Directory -Force backups
robocopy .\media ".\backups\media-$(Get-Date -Format yyyyMMdd-HHmmss)" /E
```

`robocopy` may return `1` when files were copied successfully. That is normal for this command.

## Restore the database

Stop the Django server first, then restore the selected backup:

```powershell
Copy-Item -LiteralPath .\backups\db-YYYYMMDD-HHMMSS.sqlite3 -Destination .\db.sqlite3
```

## Restore media

Stop the Django server first, then restore the selected media backup:

```powershell
robocopy ".\backups\media-YYYYMMDD-HHMMSS" .\media /E
```

## Where not to store backups

Do not store backups inside public web roots, shared static folders, cloud-synced public folders, or Git commits. Keep `.env` out of Git and do not paste secret values into tickets, chats, or screenshots.

## Environment checklist

Before production, set real values in the hosting environment:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- email settings
- Telegram settings
- `VELQARO_DELIVERY_FEE=0.00`

## Static and media

Local development serves uploaded media through Django only when `DEBUG=True`. Production should not serve media through Django; configure the hosting provider, web server, or object storage to serve uploaded files safely.

Run before deployment:

```powershell
.\venv\Scripts\python.exe manage.py collectstatic
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py check --deploy
```

## HTTPS, proxy, and HSTS

`SECURE_PROXY_SSL_HEADER` is prepared for common reverse-proxy hosting where HTTPS terminates before Django and the platform sends `X-Forwarded-Proto: https`.

Keep `SECURE_HSTS_SECONDS=0` until the final HTTPS domain is working correctly. After HTTPS is confirmed, increase it gradually. Only enable `SECURE_HSTS_INCLUDE_SUBDOMAINS=True` and `SECURE_HSTS_PRELOAD=True` when every subdomain is permanently HTTPS-ready.
