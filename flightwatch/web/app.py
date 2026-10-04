"""Panel webowy FlightWatch (FastAPI + Jinja). Uruchomienie: `uv run flightwatch-panel`.

Panel tylko czyta, z jednym wyjątkiem: formularz reguł taryf zapisuje `data/fare_rules.yaml`.
Brak logowania – nasłuchuje na 127.0.0.1, dostęp przez tunel SSH (jak bot: zero portów publicznych).
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from flightwatch.alerts import preview
from flightwatch.fare_rules import DEFAULT_PATH, FareRule, FareRuleError, FareRuleStore
from flightwatch.web import demo, views

HERE = Path(__file__).parent

NAV = (
    ("overview", "Przegląd", "/"),
    ("offers", "Oferty", "/oferty"),
    ("scans", "Skany", "/skany"),
    ("rules", "Reguły taryf", "/reguly"),
    ("config", "Konfiguracja", "/konfiguracja"),
)


def tg_html(text: str) -> Markup:
    """Tekst wiadomości (HTML Telegrama, już escapowany przez formatery) → HTML strony."""
    return Markup(text.replace("\n", "<br>"))


def create_app(fare_rules_path: Path | None = None, today: date | None = None) -> FastAPI:
    app = FastAPI(title="FlightWatch", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.tests["day"] = lambda x: isinstance(x, preview.Day)
    templates.env.tests["user"] = lambda x: isinstance(x, preview.UserMsg)
    templates.env.filters["tg_html"] = tg_html
    store = FareRuleStore(fare_rules_path or Path(os.environ.get("FLIGHTWATCH_FARE_RULES", DEFAULT_PATH)))

    def render(request: Request, name: str, active: str, ctx: dict[str, object], status: int = 200) -> Response:
        base = {
            "nav": NAV,
            "active": active,
            "watch_tag": demo.WATCH_TAG,
            "header_status": demo.HEADER_STATUS,
        }
        return templates.TemplateResponse(request, name, {**base, **ctx}, status_code=status)

    def params(request: Request) -> dict[str, str | None]:
        return dict(request.query_params)

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request) -> Response:
        return render(request, "overview.html", "overview", {"v": views.overview_view(params(request))})

    @app.get("/oferty", response_class=HTMLResponse)
    def offers(request: Request) -> Response:
        return render(request, "offers.html", "offers", {"v": views.offers_view(params(request))})

    @app.get("/skany", response_class=HTMLResponse)
    def scans(request: Request) -> Response:
        return render(request, "scans.html", "scans", {"v": views.scans_view(params(request))})

    @app.get("/reguly", response_class=HTMLResponse)
    def rules(request: Request) -> Response:
        return render(request, "rules.html", "rules", {"v": views.rules_view(store.load(), params(request))})

    @app.post("/reguly", response_class=HTMLResponse)
    def save_rule(
        request: Request,
        code: Annotated[str, Form()],
        brand: Annotated[str, Form()],
        airline: Annotated[str, Form()] = "",
        bag: Annotated[str, Form()] = "",
        carry: Annotated[str, Form()] = "",
        seat: Annotated[str, Form()] = "",
        change: Annotated[str, Form()] = "",
        refund: Annotated[str, Form()] = "",
    ) -> Response:
        rule = FareRule(code, airline or code.upper(), brand, bag, carry, seat, change, refund)
        try:
            saved = store.upsert(rule, today or date.today())
        except FareRuleError as e:
            form = {"code": code, "brand": brand, "airline": airline, "bag": bag, "carry": carry, "seat": seat,
                    "change": change, "refund": refund}  # fmt: skip
            v = views.rules_view(store.load(), {}, error=str(e), form=form)
            return render(request, "rules.html", "rules", {"v": v}, status=422)
        return RedirectResponse(f"/reguly?rule={saved.id}&saved=1#rule-form", status_code=303)

    @app.get("/konfiguracja", response_class=HTMLResponse)
    def config(request: Request) -> Response:
        return render(request, "config.html", "config", {"v": views.config_view()})

    @app.get("/telegram", response_class=HTMLResponse)
    def telegram(request: Request) -> Response:
        return render(request, "telegram.html", "telegram", {"screens": preview.screens(), "preview": preview})

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=os.environ.get("FLIGHTWATCH_PANEL_HOST", "127.0.0.1"), port=8080)
