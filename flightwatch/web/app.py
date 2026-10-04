"""Panel webowy FlightWatch (FastAPI + Jinja). Uruchomienie: `uv run flightwatch-panel`.

Zapisuje tylko dwa pliki: reguły taryf (`data/fare_rules.yaml`) i sekrety (`.env`, ADR-007).
`config.yaml` pozostaje tylko do odczytu. Brak logowania – nasłuchuje na 127.0.0.1, dostęp przez
tunel SSH. Każdy formularz POST niesie token CSRF, żeby obca strona nie mogła nadpisać kluczy.
"""

from __future__ import annotations

import hmac
import os
import secrets
from datetime import date
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from flightwatch import checks, settings
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
    ("settings", "Ustawienia", "/ustawienia"),
)


def tg_html(text: str) -> Markup:
    """Tekst wiadomości (HTML Telegrama, już escapowany przez formatery) → HTML strony."""
    return Markup(text.replace("\n", "<br>"))


def create_app(
    fare_rules_path: Path | None = None,
    today: date | None = None,
    env_path: Path | None = None,
    config_path: Path | None = None,
    http: httpx.Client | None = None,
) -> FastAPI:
    app = FastAPI(title="FlightWatch", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.csrf = csrf = secrets.token_urlsafe(32)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.tests["day"] = lambda x: isinstance(x, preview.Day)
    templates.env.tests["user"] = lambda x: isinstance(x, preview.UserMsg)
    templates.env.filters["tg_html"] = tg_html
    store = FareRuleStore(fare_rules_path or Path(os.environ.get("FLIGHTWATCH_FARE_RULES", DEFAULT_PATH)))
    env = settings.EnvFile(env_path or Path(os.environ.get("FLIGHTWATCH_ENV_FILE", settings.DEFAULT_ENV_PATH)))
    cfg_path = config_path or Path(os.environ.get("FLIGHTWATCH_CONFIG", settings.DEFAULT_CONFIG_PATH))

    def check_csrf(token: str) -> None:
        if not hmac.compare_digest(token, csrf):
            raise HTTPException(403, "Nieważny formularz – odśwież stronę.")

    def render(request: Request, name: str, active: str, ctx: dict[str, object], status: int = 200) -> Response:
        base = {
            "nav": NAV,
            "active": active,
            "watch_tag": demo.WATCH_TAG,
            "header_status": demo.HEADER_STATUS,
            "csrf": csrf,
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
        csrf_token: Annotated[str, Form(alias="csrf")],
        code: Annotated[str, Form()],
        brand: Annotated[str, Form()],
        airline: Annotated[str, Form()] = "",
        bag: Annotated[str, Form()] = "",
        carry: Annotated[str, Form()] = "",
        seat: Annotated[str, Form()] = "",
        change: Annotated[str, Form()] = "",
        refund: Annotated[str, Form()] = "",
    ) -> Response:
        check_csrf(csrf_token)
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

    def settings_page(
        request: Request,
        status: int = 200,
        errors: dict[str, str] | None = None,
        error_group: str | None = None,
        saved: str | None = None,
        result: tuple[str, checks.Result] | None = None,
        submitted: dict[str, str] | None = None,
    ) -> Response:
        checks_list = settings.file_checks(env, cfg_path, len(store.load()), store.path.parent)
        v = views.settings_view(
            env.read(), checks_list, errors=errors, error_group=error_group, saved=saved, result=result,
            submitted=submitted, env_path=str(env.path),
        )  # fmt: skip
        return render(request, "settings.html", "settings", {"v": v}, status=status)

    @app.get("/ustawienia", response_class=HTMLResponse)
    def settings_get(request: Request) -> Response:
        return settings_page(request, saved=request.query_params.get("saved"))

    @app.post("/ustawienia", response_class=HTMLResponse)
    async def settings_post(request: Request) -> Response:
        form = await request.form()
        check_csrf(str(form.get("csrf", "")))
        group = str(form.get("group", ""))
        if group not in {g.id for g in settings.GROUPS}:
            raise HTTPException(400, "Nieznana sekcja")
        values = {k: str(v) for k, v in form.items() if k in settings.BY_KEY}
        clear = [str(c) for c in form.getlist("clear") if str(c) in settings.BY_KEY]
        try:
            _, errors = settings.apply_form(env, group, values, clear)
        except settings.SettingsError as e:
            errors = {"_": str(e)}
        if errors:
            return settings_page(request, status=422, errors=errors, error_group=group, submitted=values)
        return RedirectResponse(f"/ustawienia?saved={group}#g-{group}", status_code=303)

    @app.post("/ustawienia/test", response_class=HTMLResponse)
    def settings_test(
        request: Request, csrf_token: Annotated[str, Form(alias="csrf")], name: Annotated[str, Form()]
    ) -> Response:
        check_csrf(csrf_token)
        values = env.read()
        client = http or httpx.Client()
        try:
            if name in ("telegram", "telegram_send"):
                result = checks.telegram(values, client, send_test=name == "telegram_send")
            elif name == "serpapi":
                result = checks.serpapi(values, client)
            elif name == "hc":
                result = checks.healthchecks(values, client)
            else:
                raise HTTPException(400, "Nieznany test")
        finally:
            if http is None:
                client.close()
        return settings_page(request, result=(name, result))

    @app.get("/telegram", response_class=HTMLResponse)
    def telegram(request: Request) -> Response:
        return render(request, "telegram.html", "telegram", {"screens": preview.screens(), "preview": preview})

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=os.environ.get("FLIGHTWATCH_PANEL_HOST", "127.0.0.1"), port=8080)
