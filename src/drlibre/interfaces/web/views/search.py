from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from drlibre.bootstrap.container import container
from drlibre.interfaces.web.presenters.search import Kind, kind_of, search_view
from drlibre.search.application.ports.inbound import SearchCriteria


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """The landing page is the public search; its state lives in the query string."""
    app = container()
    criteria = SearchCriteria.parse(request.GET.dict())
    kind = kind_of(request.GET.get("list"))
    match kind:
        case Kind.PROVIDERS:
            page = app.search_providers.execute(criteria)
        case Kind.HOSPITALS:
            page = app.search_hospitals.execute(criteria)
        case Kind.SPECIALTIES:
            page = app.search_specialties.execute(criteria)
    view = search_view(
        criteria=criteria,
        kind=kind,
        page=page,
        counts=app.count_search_results.execute(criteria),
        options=app.list_filter_options.execute(),
    )
    return render(request, "search/home.html", {"view": view})
