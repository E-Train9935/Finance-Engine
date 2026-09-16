import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.services.analytics import company_metrics, dcf_scenario, market_statistics


def test_market_statistics():
    rows = [{"close": "100"}, {"close": "110"}, {"close": "105"}]
    out = market_statistics(rows)
    assert out["last"] == 105
    assert out["period_return_pct"] == 5.0
    assert out["max_drawdown_pct"] < 0


def test_company_metrics():
    snapshot = {
        "revenue": 1000,
        "net_income": 100,
        "operating_income": 150,
        "assets": 2000,
        "liabilities": 1000,
        "equity": 1000,
        "cash": 300,
        "total_debt": 200,
        "free_cash_flow": 120,
        "shares": 10,
    }
    out = company_metrics(snapshot, 50)
    assert out["operating_margin_pct"] == 15
    assert out["market_cap"] == 500
    assert out["net_cash"] == 100


def test_dcf_scenario():
    snapshot = {"free_cash_flow": 100, "cash": 20, "total_debt": 10}
    result = dcf_scenario(snapshot, 10, {"growth_rate": 5, "discount_rate": 10, "terminal_growth_rate": 2, "years": 5})
    assert result["enterprise_value"] > 0
    assert result["implied_value_per_share"] > 0
