"""
Utils used to handle import bookmarks and emails from CSV files.
This is only used with the sites/aarhus hooks.
"""

import csv
from maya.core.dynamic_settings import get_base_dir_path


def bookmarks_by_email(email):
    """ "
    Get bookmarks by email from csv file
    """
    bookmarks_file = get_base_dir_path("data", "csv", "bookmarks_with_emails.csv")
    resource_ids = []
    with open(bookmarks_file, "r") as bookmarks_file:
        reader = csv.DictReader(bookmarks_file)
        for row in reader:
            if row["email"] == email:
                resource_ids.append(row["resource_id"])
    return resource_ids


def email_exists(email):
    """
    Check if email exists in user file
    """
    users_emails_file = get_base_dir_path("data", "csv", "emails.csv")
    with open(users_emails_file, "r") as users_emails_file:
        reader = csv.DictReader(users_emails_file)
        for row in reader:
            if row["email"] == email:
                return True
    return False
