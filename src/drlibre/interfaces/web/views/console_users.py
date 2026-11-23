import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role, User
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.forms.base import INVALID
from drlibre.interfaces.web.forms.console import UserForm
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.reference import Column, confirm_view, list_view, yes_no
from drlibre.interfaces.web.presenters.staff import role_label
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest

BASE = "/console/users/"
COLUMNS = (
    Column("Nom", lambda u: u.full_name),
    Column("Email", lambda u: u.email.value),
    Column("Rôle", lambda u: role_label(u.role)),
    Column("Actif", lambda u: yes_no(u.active)),
)
_FORM_REFUSALS = {ErrorCode.INVALID_INPUT, ErrorCode.HAS_DEPENDENTS}


def _user(record_id: uuid.UUID) -> User:
    user = container().user_queries.user(Id(record_id))
    if user is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Utilisateur introuvable.")
    return user


def _form(request: HttpRequest, form: UserForm, *, title: str, status: int = 200) -> HttpResponse:
    page = FormPage(title, request.path, "Enregistrer", form, cancel_url=BASE)
    context = {"page": page, "section_nav": console_nav(request.path)}
    return render(request, "console/form.html", context, status=status)


def _save(request: HttpRequest, title: str, user_id: Id | None) -> HttpResponse:
    form = UserForm(request.POST, creating=user_id is None)
    if not form.is_valid():
        return _form(request, form, title=title, status=INVALID)
    data = form.cleaned_data
    try:
        container().save_user.execute(
            actor=current_identity(request).user_id,
            user_id=user_id,
            full_name=data["full_name"],
            email=data["email"],
            role=data["role"],
            active=data["active"],
            temporary_password=data.get("temporary_password", ""),
        )
    except DomainError as error:
        if error.code not in _FORM_REFUSALS:
            raise
        form.refuse(error)
        return _form(request, form, title=title, status=error.code.http_status)
    return redirect(f"{BASE}?done={'updated' if user_id else 'created'}")


@require_GET
@require_role(Role.ADMIN)
def list_users(request: HttpRequest) -> HttpResponse:
    page_request = PageRequest.from_query(
        page=request.GET.get("page"), search=request.GET.get("search")
    )
    view = list_view(
        title="Utilisateurs",
        base_url=BASE,
        columns=COLUMNS,
        page=container().user_queries.users(page_request),
        request=page_request,
        label=lambda u: u.full_name,
        done=request.GET.get("done"),
    )
    context = {
        "view": view,
        "search_label": "Rechercher par nom ou email",
        "section_nav": console_nav(request.path),
    }
    return render(request, "console/list.html", context)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def create_user(request: HttpRequest) -> HttpResponse:
    title = "Ajouter un utilisateur"
    if request.method == "POST":
        return _save(request, title, None)
    return _form(request, UserForm(initial={"active": True}, creating=True), title=title)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def edit_user(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    user = _user(record_id)
    title = f"Modifier « {user.full_name} »"
    if request.method == "POST":
        return _save(request, title, user.id)
    initial = {
        "full_name": user.full_name,
        "email": user.email.value,
        "role": user.role.value,
        "active": user.active,
    }
    return _form(request, UserForm(initial=initial, creating=False), title=title)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def delete_user(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    user = _user(record_id)
    error: DomainError | None = None
    if request.method == "POST":
        try:
            container().delete_user.execute(
                actor=current_identity(request).user_id, user_id=user.id
            )
        except DomainError as refused:
            if refused.code not in {ErrorCode.HAS_DEPENDENTS, ErrorCode.FORBIDDEN}:
                raise
            error = refused
        else:
            return redirect(f"{BASE}?done=deleted")
    confirm = confirm_view(label=user.full_name, action=request.path, cancel_url=BASE, error=error)
    context = {"confirm": confirm, "section_nav": console_nav(request.path)}
    status = error.code.http_status if error else 200
    return render(request, "console/confirm_delete.html", context, status=status)
