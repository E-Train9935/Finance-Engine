from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Iterable


def safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def pct(a, b):
    value = safe_div(a, b)
    return value * 100 if value is not None else None


def market_statistics(prices: list[dict]) -> dict:
    closes = []
    for row in prices:
        try:
            closes.append(float(row["close"]))
        except (KeyError, TypeError, ValueError):
            continue
    if not closes:
        return {}

    returns = [(closes[i] / closes[i - 1]) - 1 for i in range(1, len(closes)) if closes[i - 1] != 0]
    annualized_vol = pstdev(returns) * math.sqrt(252) * 100 if len(returns) > 1 else None
    peak = closes[0]
    max_drawdown = 0.0
    for value in closes:
        peak = max(peak, value)
        dd = value / peak - 1
        max_drawdown = min(max_drawdown, dd)

    return {
        "last": closes[-1],
        "period_return_pct": round((closes[-1] / closes[0] - 1) * 100, 2) if closes[0] else None,
        "annualized_volatility_pct": round(annualized_vol, 2) if annualized_vol is not None else None,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "high": max(closes),
        "low": min(closes),
    }


def company_metrics(snapshot: dict, price: float | None) -> dict:
    revenue = snapshot.get("revenue")
    net_income = snapshot.get("net_income")
    op_income = snapshot.get("operating_income")
    assets = snapshot.get("assets")
    liabilities = snapshot.get("liabilities")
    equity = snapshot.get("equity")
    cash = snapshot.get("cash")
    debt = snapshot.get("total_debt")
    fcf = snapshot.get("free_cash_flow")
    market_shares = snapshot.get("shares_outstanding") or snapshot.get("shares")

    market_cap = price * market_shares if price and market_shares and market_shares > 0 else None
    metrics = {
        "operating_margin_pct": pct(op_income, revenue),
        "net_margin_pct": pct(net_income, revenue),
        "return_on_assets_pct": pct(net_income, assets),
        "return_on_equity_pct": pct(net_income, equity),
        "debt_to_equity": safe_div(debt, equity),
        "liabilities_to_assets": safe_div(liabilities, assets),
        "fcf_margin_pct": pct(fcf, revenue),
        "market_cap": market_cap,
        "price_to_sales": safe_div(market_cap, revenue),
        "price_to_earnings": safe_div(market_cap, net_income),
        "price_to_fcf": safe_div(market_cap, fcf),
        "net_cash": (cash - debt) if isinstance(cash, (int, float)) and isinstance(debt, (int, float)) else None,
    }
    return {k: round(v, 4) if isinstance(v, float) and math.isfinite(v) else v for k, v in metrics.items()}


def diagnostics(snapshot: dict, metrics: dict) -> list[dict]:
    signals: list[dict] = []

    def add(level: str, code: str, title: str, detail: str):
        signals.append({"level": level, "code": code, "title": title, "detail": detail})

    fcf = snapshot.get("free_cash_flow")
    revenue = snapshot.get("revenue")
    net_income = snapshot.get("net_income")
    debt = snapshot.get("total_debt")
    cash = snapshot.get("cash")
    op_margin = metrics.get("operating_margin_pct")

    if isinstance(fcf, (int, float)):
        add("signal" if fcf >= 0 else "watch", "FCF", "Free cash flow", "Positive free cash flow in the latest normalized SEC period." if fcf >= 0 else "Latest normalized SEC period shows negative free cash flow.")
    if isinstance(net_income, (int, float)):
        add("signal" if net_income >= 0 else "watch", "NI", "Net income", "Latest normalized period is profitable." if net_income >= 0 else "Latest normalized period reports a net loss.")
    if isinstance(debt, (int, float)) and isinstance(cash, (int, float)):
        add("watch" if debt > cash else "signal", "LIQ", "Debt vs cash", "Reported debt exceeds cash." if debt > cash else "Cash meets or exceeds reported debt.")
    if isinstance(op_margin, (int, float)):
        add("info", "MARGIN", "Operating margin", f"Latest normalized operating margin is {op_margin:.1f}%.")
    if revenue is None:
        add("info", "DATA", "Revenue mapping", "A comparable revenue concept was not found in the latest SEC facts payload.")
    return signals


def dcf_scenario(snapshot: dict, shares: float | None, assumptions: dict) -> dict:
    """Transparent educational DCF scenario, not an investment recommendation."""
    base_fcf = snapshot.get("free_cash_flow")
    if not isinstance(base_fcf, (int, float)) or base_fcf <= 0:
        raise ValueError("A positive latest free cash flow is required for this scenario model.")
    if not shares or shares <= 0:
        raise ValueError("A positive diluted share count is required for per-share output.")

    growth = assumptions["growth_rate"] / 100
    discount = assumptions["discount_rate"] / 100
    terminal_growth = assumptions["terminal_growth_rate"] / 100
    years = assumptions["years"]
    if discount <= terminal_growth:
        raise ValueError("Discount rate must be greater than terminal growth rate.")

    flows = []
    fcf = base_fcf
    pv_sum = 0.0
    for year in range(1, years + 1):
        fcf *= 1 + growth
        pv = fcf / ((1 + discount) ** year)
        pv_sum += pv
        flows.append({"year": year, "fcf": fcf, "present_value": pv})

    terminal_value = fcf * (1 + terminal_growth) / (discount - terminal_growth)
    terminal_pv = terminal_value / ((1 + discount) ** years)
    enterprise_value = pv_sum + terminal_pv
    debt = snapshot.get("total_debt") or 0
    cash = snapshot.get("cash") or 0
    equity_value = enterprise_value + cash - debt
    per_share = equity_value / shares

    return {
        "base_fcf": base_fcf,
        "forecast": flows,
        "terminal_value": terminal_value,
        "terminal_present_value": terminal_pv,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "implied_value_per_share": per_share,
        "assumptions": assumptions,
        "disclaimer": "Scenario output is a mathematical model based on user-selected assumptions and SEC-reported inputs; it is not investment advice or a price target.",
    }
