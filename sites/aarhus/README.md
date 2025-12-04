# AarhusArkivet

In order to run this site, create a `.env` file in the `sites/aarhus` directory with the following content:

```
API_KEY=some_api_key
```

You should also override some default settings by creating a `settings_local.py` file in the `sites/aarhus` directory with content similar to the following:

```python
import typing


settings: dict[str, typing.Any] = {
    "api_base_url": "https://dev.openaws.dk/v1",
    "sqlite3": {
        "default": "sites/aarhus/data/database.db",
        "orders": "sites/aarhus/data/orders.db",
    },
    "cron_orders": True
}
```

Run some database migrations in order to use bookmarks and orders:

```bash
export BASE_DIR=sites/aarhus

./bin/migrate_default.py
./bin/migrate_orders.py
```

Cronjob

```
sudo crontab -u www-data -e
```

Add the following line (runs two hours past midnight every day): 

     0 2 * * * cd /var/www/aarhus-client && .venv/bin/maya cron local
