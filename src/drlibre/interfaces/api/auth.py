from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema, Status
from pydantic import ConfigDict

from drlibre.bootstrap.container import container
from drlibre.interfaces.web.auth import (
    HOMES,
    clear_session_cookie,
    session_token,
    set_session_cookie,
)

router = Router(tags=["auth"])


class LoginIn(Schema):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class LoginOut(Schema):
    role: str
    home: str


@router.post("/auth/login", response=LoginOut, auth=None)
def login(request: HttpRequest, payload: LoginIn, response: HttpResponse) -> LoginOut:
    signed = container().sign_in.execute(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("User-Agent", ""),
    )
    set_session_cookie(response, signed.token, signed.expires_at)
    return LoginOut(role=signed.role.value, home=HOMES[signed.role])


@router.post("/auth/logout", response={204: None}, auth=None)
def logout(request: HttpRequest, response: HttpResponse) -> Status[None]:
    token = session_token(request)
    if token:
        container().sign_out.execute(token=token)
    clear_session_cookie(response)
    return Status(204, None)
