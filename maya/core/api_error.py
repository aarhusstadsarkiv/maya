"""
Exception handling and input validation utilities for the OpenAws application.

This module defines a custom exception class (`OpenAwsException`) used to represent
user-facing errors that occur during request handling. It includes helper functions
to extract and translate error messages from API responses, and several asynchronous
validation functions to check client-side form data such as passwords, display names,
and captchas.

The `OpenAwsException` class is designed to be used used with expected errors
such as authentication failures, validation errors, and API response errors.

Functions:
- raise_openaws_exception: Raises an `OpenAwsException` based on status code and error content.
- validate_passwords: Ensures provided passwords match and meet minimum requirements.
- validate_display_name: Ensures display name meets length constraints.
- validate_captcha: Validates the submitted captcha against an expected value.

Internal helpers:
- _extract_validation_error: Parses validation errors from error dictionaries.
- _extract_model_error: Parses model-related errors from error dictionaries.
- _get_error_string: Maps error codes to translated user-friendly error messages.
"""

from starlette.requests import Request
from maya.core.translate import translate
from maya.core.logging import get_log


log = get_log()


class OpenAwsException(Exception):
    """
    OpenAwsException is used as an exception that is expected.
    E.g. the user is not logged in, or the user tries to register with an invalid password.
    Or for raising an error when the API returns an error.

    raise OpenAwsException(
                422,
                translate("You need to be logged in to view this page."),
    )

    """

    def __init__(self, status_code: int, message: str, text: str = ""):
        self.status_code = status_code
        self.message = message
        self.text = text
        super().__init__(message, status_code, text)

    def __str__(self) -> str:
        return self.message


def raise_openaws_exception(status_code: int, error: dict):
    """
    This is used to raise an OpenAwsException when the API returns an error.
    Raise OpenAwsException based on status_code and error from the API error message.
    """

    raise_message = translate("Unknown error. Please try again later.")

    if status_code == 400:
        error_code = _extract_model_error(error)
        raise_message = _get_error_string(error_code)

    if status_code == 422:
        error_code = _extract_validation_error(error)
        raise_message = _get_error_string(error_code)

    raise OpenAwsException(status_code, raise_message)


def _extract_validation_error(error_dict: dict) -> str:
    try:
        error_detail = error_dict["detail"]
        if isinstance(error_detail, list) and len(error_detail) > 0:
            first_error = error_detail[0]
            error_type = first_error["type"]
            return error_type
    except (KeyError, IndexError):
        pass

    try:
        error_detail = error_dict["detail"]
        return error_detail
    except KeyError:
        pass

    return "value_error.unknown_error"


def _extract_model_error(error_dict: dict) -> str:
    try:
        if isinstance(error_dict.get("detail"), dict):
            error_code = error_dict["detail"]["code"]
        else:
            error_code = error_dict["detail"]
    except KeyError:
        error_code = "UNKNOWN_MODEL_ERROR"

    return error_code


def _get_error_string(error: str) -> str:
    # register errors
    if error == "REGISTER_INVALID_PASSWORD":
        return translate("Password should be at least 8 characters long")
    if error == "REGISTER_USER_ALREADY_EXISTS":
        return translate("User already exists. Try to login instead.")
    if error == "value_error.email":
        return translate("Email needs to be correct.")
    if error == "value_error.missing":
        return translate("Username is required.")

    # verify errors
    if error == "VERIFY_USER_BAD_TOKEN":
        return translate("The token is not valid. You will need to a new token to verify your email.")
    if error == "VERIFY_USER_ALREADY_VERIFIED":
        return translate("User is already verified.")

    # login errors
    if error == "LOGIN_BAD_CREDENTIALS":
        return translate("Email or password is not correct.")
    if error == "LOGIN_USER_NOT_VERIFIED":
        return translate("User is not verified. Please verify your email.")

    # reset password errors
    if error == "RESET_PASSWORD_BAD_TOKEN":
        return translate("The token is not valid. You need to request a new mail with a new token.")
    if error == "RESET_PASSWORD_INVALID_PASSWORD":
        return translate("Password should be at least 8 characters long")

    if error == "Invalid domain url":
        return translate("Invalid settings: Invalid domain url")

    # unknow errors
    if error == "value_error.unknown_error":
        return translate("Unknown error. Please try again later.")
    if error == "UNKNOWN_MODEL_ERROR":
        return translate("Unknown error. Please try again later.")

    return translate("Unknown error. Please try again later.")


async def validate_passwords(request: Request):
    """
    Validate that the passwords match and are at least 8 characters long.
    This is also validated on the API side. But in some cases we want to
    validate it on the client side as well.
    """

    form = await request.form()
    password_1 = str(form.get("password"))
    password_2 = str(form.get("password_2"))

    if password_1 != password_2:
        raise OpenAwsException(
            400,
            translate("Passwords do not match."),
        )

    if len(password_1) < 8:
        raise OpenAwsException(
            400,
            translate("Password should be at least 8 characters long"),
        )


async def validate_display_name(request: Request):
    """
    Validate that the display name is at least 3 characters long.
    """

    form = await request.form()
    display_name = str(form.get("display_name"))

    if len(display_name) < 3:
        raise OpenAwsException(
            400,
            translate("Display name should be at least 3 characters long"),
        )


async def validate_captcha(request: Request):
    """
    Very simple captcha test.
    """

    form = await request.form()
    captcha = str(form.get("captcha"))

    # Remove all non-digit characters
    captcha = "".join(filter(str.isdigit, captcha))

    if captcha != "8000":
        raise OpenAwsException(
            400,
            translate("Captcha is not correct"),
        )
