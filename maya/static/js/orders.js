/**
 * If editing this file then also update `StatusesUser` in `orders.py`
 * maya/database/utils_orders.py
 */

class OrderStatus {
    static ORDERED = 1;
    static COMPLETED = 2;
    static QUEUED = 3;
    static DELETED = 4;
    static APPLICATION = 5;
}

export {OrderStatus };
