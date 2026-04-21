# """
# V2 API interactions with the external web service.
# """

# from starlette.requests import Request

# from maya.core import user
# from maya.core.api import _get_async_client, base_url_v2
# from maya.core.api_error import (
#     OpenAwsException,
#     raise_openaws_exception,
#     validate_captcha,
#     validate_passwords,
#     validate_user_name,
# )
# from maya.core.hooks import get_hooks
# from maya.core.logging import get_log
# from maya.core.translate import translate

# log = get_log()


# V2_SESSION_COOKIE_NAMES = ("session", "client", "domain")


# def _get_name(form) -> str:
#     first_name = str(form.get("first_name")).strip()
#     last_name = str(form.get("last_name")).strip()
#     return f"{first_name} {last_name}".strip()


# def _get_user_agent(request: Request) -> str:
#     user_agent = request.headers.get("user-agent", "").strip()
#     if not user_agent:
#         raise OpenAwsException(400, translate("User-Agent header is required to login."))
#     return user_agent


# def _store_v2_session_cookies(request: Request, response) -> None:
#     for cookie_name in V2_SESSION_COOKIE_NAMES:
#         cookie_value = response.cookies.get(cookie_name)
#         if cookie_value:
#             request.session[cookie_name] = cookie_value


# async def auth_login_post(request: Request) -> dict:
#     """
#     Log in through the v2 `/users/login` endpoint.
#     """
#     hooks = get_hooks(request=request)
#     form = await request.form()
#     email = str(form.get("email", "")).strip()
#     password = str(form.get("password", ""))

#     if not email or not password:
#         raise OpenAwsException(400, translate("Email and password are required to login."))

#     user_agent = _get_user_agent(request)

#     async with _get_async_client() as client:
#         url = f"{base_url_v2}/users/login"
#         headers = {
#             "Content-Type": "application/json",
#             "Accept": "application/json",
#             "User-Agent": user_agent,
#         }
#         json_post = {"email": email, "password": password}

#         log.info(f"Logging in user {email} through v2 API at {url}")
#         response = await client.post(url, json=json_post, headers=headers)
#         json_response = response.json()

#         if response.is_success:
#             _store_v2_session_cookies(request, response)

#             access_token = json_response.get("access_token")
#             token_type = json_response.get("token_type")
#             if access_token and token_type:
#                 user.set_user_jwt(request, access_token, token_type)

#             await hooks.after_login_success(json_response)
#             return json_response

#         log.info(f"Failed to login user {email} through v2 API: {json_response}")
#         await hooks.after_login_failure(json_response)
#         raise_openaws_exception(response.status_code, json_response)


# async def auth_register_post(request: Request) -> dict:
#     """
#     Register a new user through the v2 `/users/register` endpoint.
#     """
#     await validate_captcha(request)
#     await validate_user_name(request)
#     await validate_passwords(request)

#     form = await request.form()
#     name = _get_name(form)
#     email = str(form.get("email")).strip()
#     password = str(form.get("password"))

#     async with _get_async_client() as client:
#         url = f"{base_url_v2}/users/register"

#         log.info(f"Registering user {email} through v2 API at {url}")
#         headers = {"Content-Type": "application/json", "Accept": "application/json"}
#         json_post = {"name": name, "email": email, "password": password}
#         response = await client.post(url, json=json_post, headers=headers)

#         if not response.is_success:
#             json_response = response.json()
#             log.info(f"Failed to register user {email} through v2 API: {json_response}")
#             raise_openaws_exception(response.status_code, json_response)

#         return response.json()
