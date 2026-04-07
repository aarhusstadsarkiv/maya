#!/usr/bin/env python
"""
Set one or more orders' expire_at inside the renewal window for manual testing.
"""

import os
import sqlite3
import sys

import arrow

sys.path.append(".")

from maya.core.dynamic_settings import settings
from maya.database.utils_orders import DEADLINE_DAYS_RENEWAL


def main() -> int:
    if "BASE_DIR" not in os.environ:
        print("Environment variable BASE_DIR is not set. E.g. set it like this:")
        print("export BASE_DIR=sites/aarhus")
        return 1

    if len(sys.argv) < 2:
        print("Usage: python bin/move_order_within_renewal.py <order_id> [<order_id> ...]")
        return 1

    try:
        order_ids = [int(order_id) for order_id in sys.argv[1:]]
    except ValueError:
        print("All order_id values must be integers")
        return 1

    db_path = settings["sqlite3"]["orders"]
    print(f"Using database path: {db_path}")
    new_expire_at = arrow.utcnow().floor("day").shift(days=DEADLINE_DAYS_RENEWAL + 1).format("YYYY-MM-DD HH:mm:ss")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        exit_code = 0
        for order_id in order_ids:
            current_order = connection.execute(
                "SELECT order_id, expire_at FROM orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()

            if current_order is None:
                print(f"Order {order_id} was not found")
                exit_code = 1
                continue

            connection.execute(
                "UPDATE orders SET expire_at = ? WHERE order_id = ?",
                (new_expire_at, order_id),
            )

            print(f"Order {order_id} expire_at updated")
            print(f"Old expire_at: {current_order['expire_at']}")
            print(f"New expire_at: {new_expire_at}")

        connection.commit()
        return exit_code
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
