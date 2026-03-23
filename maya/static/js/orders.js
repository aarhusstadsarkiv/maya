/**
 * If editing this file then also update `OrderStatus` or `RecordLocation` in `orders.py` 
 * maya/database/utils_orders.py
 */

class OrderStatus {
    static ORDERED = 1;
    static COMPLETED = 2;
    static QUEUED = 3;
    static DELETED = 4;
    static APPLICATION = 5;
}

class RecordLocation {
    static IN_STORAGE = 1;
    static PACKED_STORAGE = 2;
    static READING_ROOM = 4;
    static RETURN_TO_STORAGE = 5;
}

export {OrderStatus, RecordLocation };
