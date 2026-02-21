from dataclasses import dataclass

@dataclass
class RiskResult:
    health_score: float
    do_risk: float
    nh3_risk: float
    messages: list[tuple[str, str]]  # (severity, message)

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def calculate_risk(do: float, temp: float, ammonia: float, ph: float) -> RiskResult:
    """
    Demo-grade but explainable risk scoring:
    - DO risk rises sharply below 5 mg/L; critical below 3.5
    - NH3 risk approximated by ammonia + pH + temp interaction (proxy)
    """
    do_risk = 0.0
    if do < 5.0:
        do_risk = _clamp((5.0 - do) / 1.5 * 60.0, 0.0, 100.0)  # up to ~60-100 range

    # Simple unionized ammonia proxy (not scientifically exact; demo proxy)
    nh3_proxy = ammonia * (1.0 + (ph - 7.0) * 0.35) * (1.0 + (temp - 28.0) * 0.04)
    nh3_proxy = max(0.0, nh3_proxy)

    nh3_risk = _clamp(nh3_proxy * 40.0, 0.0, 100.0)

    risk_total = 0.6 * do_risk + 0.4 * nh3_risk
    health_score = _clamp(100.0 - risk_total, 0.0, 100.0)

    messages: list[tuple[str, str]] = []

    # Alerts
    if do < 3.5:
        messages.append(("HIGH", "Critical: Dissolved Oxygen dangerously low"))
    elif do < 4.5:
        messages.append(("MEDIUM", "Warning: Dissolved Oxygen low"))

    if nh3_proxy > 0.8:
        messages.append(("HIGH", "Critical: Ammonia stress risk high"))
    elif nh3_proxy > 0.4:
        messages.append(("MEDIUM", "Warning: Ammonia stress risk rising"))

    return RiskResult(
        health_score=health_score,
        do_risk=do_risk,
        nh3_risk=nh3_risk,
        messages=messages,
    )

def status_from_health(score: float) -> str:
    if score >= 75:
        return "GOOD"
    if score >= 50:
        return "WATCH"
    return "CRITICAL"
