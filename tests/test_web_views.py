from flightwatch.fare_rules import FareRule
from flightwatch.web import demo, views


def test_effective_cost_matches_design() -> None:
    k = {o.id: o.k for o in demo.RANKING}
    assert k == {"qr": 12757, "ek": 13505, "qr2": 13850, "lh": 14370, "tk": 14805}


def test_ranking_sorted_by_k_and_defaults_to_compromise() -> None:
    v = views.ranking_view(None, {})
    assert [r["o"].id for r in v["rows"]] == ["qr", "ek", "qr2", "lh", "tk"]
    assert v["sel"]["o"].id == "qr"
    assert v["sel"]["qualifies"] == "Kwalifikuje się do KUP, ale 420 zł nad progiem."
    assert views.ranking_view("tk", {})["sel"]["qualifies"].startswith("Nie może wywołać KUP")


def test_offer_filters() -> None:
    assert views.offers_view({})["count"] == 12
    v = views.offers_view({"origin": "WAW", "qual": "1"})
    assert {r["o"].origin for r in v["rows"]} == {"WAW"}
    assert all(r["o"].status == "ok" for r in v["rows"])
    assert v["count"] == 2
    assert views.offers_view({"origin": "XXX"})["count"] == 12


def test_heatmap_ring_marks_near_band() -> None:
    v = views.heatmap_view("kwota")
    ringed = [(r["code"], c["label"]) for r in v["rows"] for c in r["cells"] if c["ring"]]
    assert ringed == [("WAW", "11,2"), ("WAW", "11,4"), ("BER", "11,7"), ("BER", "11,5"), ("BER", "11,6")]
    k = views.heatmap_view("K")
    assert k["ring_legend"].startswith("w granicach 600 zł")


def test_rolling_median() -> None:
    assert views.rolling_median([5, 1, 3], window=2) == [5, 5, 3]


def test_href_keeps_other_params() -> None:
    assert views.href("/", {"metric": "K", "sel": "qr"}, sel="tk") == "/?metric=K&sel=tk"
    assert views.href("/oferty", {"qual": "1"}, qual=None) == "/oferty"


def test_rules_view_hides_missing_rule_once_added() -> None:
    rules = [FareRule("TK", "Turkish Airlines", "EcoFly", "1×23 kg", "8 kg", "60 zł/os.", "500 zł/os.", "nie")]
    v = views.rules_view(rules, {})
    assert [m["m"].code for m in v["missing"]] == ["KL"]


def test_new_rule_form_prefills_code_and_brand() -> None:
    v = views.rules_view([], {"rule": "TK-ecofly"})
    vals = {fld["name"]: fld["value"] for fld in v["form"]["fields"]}
    assert vals["code"] == "TK" and vals["brand"] == "EcoFly" and vals["bag"] == ""
    assert v["form"]["kicker"] == "Nowa reguła"
    assert "14 ofert" in v["form"]["hint"]
