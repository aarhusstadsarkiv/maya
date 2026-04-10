# Order Workflows

This package contains the active order-domain implementation.

## Main modules

- `service.py`
  Owns the business workflows and public order operations.
- `repository.py`
  Owns low-level order queries and writes.
- `notifications.py`
  Owns outgoing order mails.
- `logging.py`
  Owns log writes related to notification side effects.
- `runtime.py`
  Owns shared runtime state such as `orders_url`, `log`, and `cron_log`.
- `types.py`
  Owns shared order types such as `OrderFilter`.
- `constants.py`
  Owns order log messages and mail text constants.

## Order creation

Entry point:
- `service.insert_order()`

Flow:
1. Check whether the user already has an active order on the record.
2. Upsert user and record data.
3. Determine initial status:
   `ORDERED`, `QUEUED`, or `APPLICATION`.
4. Insert the order.
5. If the order is immediately `ORDERED` and the material is already in `READING_ROOM`:
   set `expire_at`, send ready mail, and mark `message_sent=1`.
6. Write `ORDER_CREATED`.
7. If a ready mail was sent immediately, also write `MAIL_SENT`.

## Location update

Entry points:
- `service.update_location()`
- `service.bulk_update_locations()`

Single-order flow:
1. Load the order.
2. Validate that the record location may be changed.
3. Update the record location.
4. If location becomes `READING_ROOM` and the order is already `ORDERED`:
   set `expire_at`.
5. If mail should be sent immediately:
   send ready mail, mark `message_sent=1`, and log `MAIL_SENT`.
6. Always log `LOCATION_CHANGED`.

Bulk admin flow:
1. Update each order with `send_ready_mail=False`.
2. Collect orders that became ready.
3. Group them by `user_id`.
4. Send one ready mail per user via `notifications.send_ready_orders_message()`.
5. For each covered order:
   mark `message_sent=1` and write `MAIL_SENT`.

## Status update

Entry points:
- `service.update_order_status()`
- `service.update_order()`

Flow:
1. Update the order status, typically to `COMPLETED` or `DELETED`.
2. Log `STATUS_CHANGED`.
3. Look for the next queued order on the same record.
4. If found, promote it to `ORDERED`.
5. If the promoted order is already in `READING_ROOM`:
   set `expire_at`, send ready mail, mark `message_sent=1`, and log `MAIL_SENT`.
6. Log `STATUS_CHANGED` for the promoted order too.

## Application promotion

Entry point:
- `service.promote_application_order()`

Flow:
1. Load an `APPLICATION` order.
2. If another `ORDERED` order exists on the record:
   promote to `QUEUED`.
3. Otherwise promote to `ORDERED`.
4. If the promoted order is `ORDERED` and the material is in `READING_ROOM`:
   set `expire_at`, send ready mail, mark `message_sent=1`.
5. Log `STATUS_CHANGED`.
6. If mail was sent, also log `MAIL_SENT`.

## User renewal

Entry points:
- `service.renew_order()`
- `service.renew_orders_user()`

Renewal rules:
- the order must have `expire_at`
- the order must be close enough to expiry
- there must be no queued order on the same record

Flow:
1. Validate renewal eligibility with `is_order_renew_possible()`.
2. Update `expire_at`.
3. Log `ORDER_RENEWED`.

## Cron workflows

### Expire orders

Entry point:
- `service.cron_orders_expire()`

Flow:
1. Find `ORDERED` orders where `expire_at` has passed.
2. For each order:
   complete it through the normal status-update workflow.
3. That may also promote the next queued order and send a ready mail.

### Renewal emails

Entry point:
- `service.cron_renewal_emails()`

Flow:
1. Find `ORDERED` orders whose `expire_at` matches the renewal-mail date.
2. Re-check renewal eligibility.
3. Group renewable orders by `user_id`.
4. Send one renewal mail per user via `notifications.send_renew_order_message()`.
5. Write `RENEWAL_SENT` for each covered order.

## Read-side queries

Main entry points:
- `service.get_order()`
- `service.get_order_by_record_id()`
- `service.get_orders_user()`
- `service.get_orders_admin()`
- `service.get_logs()`
- `service.get_orders_user_count()`

These use `repository.py` for the SQL/query layer and apply display formatting in the service layer when needed.

## Notification rules

- Ready mails use `order_mail.html` and always take a list of orders for one user.
- Renewal mails use `order_renew_mail.html` and always take a list of orders for one user.
- Mixed-user lists are rejected in the notification layer.

## Logging rules

Logging is split by event.

Typical messages:
- `ORDER_CREATED`
- `LOCATION_CHANGED`
- `STATUS_CHANGED`
- `MAIL_SENT`
- `ORDER_RENEWED`
- `RENEWAL_SENT`

`MAIL_SENT` is always written as its own log entry, not combined with a state-change message.
