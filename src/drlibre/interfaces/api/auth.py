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
from drlibre.interfaces.web.presenters.auth import LINK_SENT_MESSAGE

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


class LinkRequestIn(Schema):
    model_config = ConfigDict(extra="forbid")

    email: str


class LinkRequestOut(Schema):
    message: str


class LinkVerifyIn(Schema):
    model_config = ConfigDict(extra="forbid")

    token: str


@router.post("/auth/link", response={202: LinkRequestOut}, auth=None)
def request_link(request: HttpRequest, payload: LinkRequestIn) -> Status[LinkRequestOut]:
    container().request_sign_in_link.execute(
        email=payload.email, network=request.META.get("REMOTE_ADDR", "")
    )
    return Status(202, LinkRequestOut(message=LINK_SENT_MESSAGE))


@router.post("/auth/link/verify", response=LoginOut, auth=None)
def verify_link(request: HttpRequest, payload: LinkVerifyIn, response: HttpResponse) -> LoginOut:
    signed = container().use_sign_in_link.execute(
        token=payload.token, user_agent=request.headers.get("User-Agent", "")
    )
    set_session_cookie(response, signed.token, signed.expires_at)
    return LoginOut(role=signed.role.value, home=HOMES[signed.role])
