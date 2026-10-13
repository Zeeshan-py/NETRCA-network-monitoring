"""Pure detection logic; no network I/O, database access, or invented observations."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median
from uuid import UUID

from app.anomaly.models import DetectionResult, SUPPORTED_METRICS
from app.core.config import Settings
from app.pipeline.models import MetricIn


def _same_scope(a: MetricIn, b: MetricIn) -> bool:
    return (a.device_id, a.link_id, a.metric_type, a.interface, a.target) == (
        b.device_id, b.link_id, b.metric_type, b.interface, b.target)


def _history(item: MetricIn, candidates: list[MetricIn], settings: Settings) -> list[MetricIn]:
    earliest = item.timestamp - timedelta(hours=settings.anomaly_history_hours)
    unique: dict[str, MetricIn] = {}
    for prior in candidates:
        if (prior.observation_key != item.observation_key and _same_scope(item, prior)
                and earliest <= prior.timestamp < item.timestamp):
            unique.setdefault(prior.observation_key, prior)
    by_time: dict[datetime, MetricIn | None] = {}
    for prior in sorted(unique.values(), key=lambda row: (row.timestamp, row.observation_key)):
        existing = by_time.get(prior.timestamp)
        if prior.timestamp not in by_time:
            by_time[prior.timestamp] = prior
        elif existing is not None and existing.value != prior.value:
            by_time[prior.timestamp] = None
    return [row for row in by_time.values() if row is not None][-settings.anomaly_max_history:]


def _result(item: MetricIn, metric_id: UUID | None, status: str, method: str, reason: str,
            *, severity: str | None = None, score: float | None = None,
            score_kind: str | None = None, support: dict | None = None,
            baseline_samples: int = 0) -> DetectionResult:
    return DetectionResult(metric_id=metric_id, observation_key=item.observation_key,
                           device_id=item.device_id, link_id=item.link_id, metric_type=item.metric_type,
                           value=item.value, unit=item.unit, observed_at=item.timestamp,
                           status=status, method=method, reason=reason, severity=severity,
                           score=score, score_kind=score_kind, support=support or {},
                           baseline_samples=baseline_samples)


def _severity(factor: float) -> str:
    if factor >= 5:
        return "CRITICAL"
    if factor >= 2:
        return "HIGH"
    if factor >= 1.5:
        return "MEDIUM"
    return "LOW"


def _threshold(item: MetricIn, settings: Settings):
    value = float(item.value)
    if item.metric_type == "LATENCY":
        limit = settings.anomaly_latency_ms
        if value > limit:
            return _severity(value / limit), min(1.0, (value - limit) / limit), {"limit": limit, "direction": "above"}
    elif item.metric_type == "PACKET_LOSS":
        limit = settings.anomaly_packet_loss_percent
        if value > limit:
            return _severity(value / limit), min(1.0, (value - limit) / limit), {"limit": limit, "direction": "above"}
    elif item.metric_type == "AVAILABILITY":
        limit = settings.anomaly_min_availability_percent
        if value < limit:
            factor = max(1, (100 - value) / max(1, 100 - limit))
            return _severity(factor), min(1.0, (limit - value) / limit), {"limit": limit, "direction": "below"}
    elif item.metric_type in {"INTERFACE_STATE", "LINK_STATE"} and value == 0:
        return "HIGH", 1.0, {"expected_state": 1, "observed_state": 0}
    return None


def _isolation(value: float, history: list[MetricIn], settings: Settings):
    if (not settings.anomaly_ml_enabled or len(history) < settings.anomaly_model_min_samples
            or len({row.value for row in history}) < 5):
        return None
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return None
    series = [[float(row.value)] for row in history]
    model = IsolationForest(n_estimators=64, contamination=settings.anomaly_model_contamination,
                            random_state=41, n_jobs=1).fit(series)
    margin = float(model.decision_function([[value]])[0])
    if margin >= 0:
        return None
    baseline_margins = model.decision_function(series)
    percentile = sum(float(other) >= margin for other in baseline_margins) / len(baseline_margins)
    return percentile, margin


def detect(item: MetricIn, candidates: list[MetricIn], settings: Settings, *, metric_id: UUID | None = None,
           now: datetime | None = None) -> DetectionResult:
    """Use only earlier distinct observations from the same resource and measurement scope."""
    now = now or datetime.now(timezone.utc)
    if item.metric_type not in SUPPORTED_METRICS:
        return _result(item, metric_id, "INSUFFICIENT_DATA", "NONE", "UNSUPPORTED_METRIC")
    if now - item.timestamp > timedelta(minutes=settings.anomaly_max_age_minutes):
        return _result(item, metric_id, "INSUFFICIENT_DATA", "NONE", "STALE_OBSERVATION")
    history = _history(item, candidates, settings)
    if item.metric_type in {"RX_ERRORS", "TX_ERRORS"}:
        if not history:
            return _result(item, metric_id, "INSUFFICIENT_DATA", "NONE", "COUNTER_PREDECESSOR_MISSING")
        previous = history[-1]
        delta = item.value - previous.value
        if delta < 0:
            return _result(item, metric_id, "INSUFFICIENT_DATA", "NONE", "COUNTER_RESET",
                           support={"previous_value": str(previous.value)}, baseline_samples=len(history))
        if delta >= settings.anomaly_error_delta:
            return _result(item, metric_id, "ANOMALY", "THRESHOLD", "ERROR_COUNTER_INCREASE",
                           severity=_severity(float(delta / settings.anomaly_error_delta)),
                           score=min(1.0, float(delta / (settings.anomaly_error_delta * 10))),
                           score_kind="ERROR_DELTA_RATIO_CAPPED", support={"delta": str(delta),
                           "limit": settings.anomaly_error_delta, "previous_value": str(previous.value)},
                           baseline_samples=len(history))
        return _result(item, metric_id, "NORMAL", "THRESHOLD", "ERROR_COUNTER_STABLE",
                       score=0, score_kind="ERROR_DELTA_RATIO_CAPPED", support={"delta": str(delta),
                       "limit": settings.anomaly_error_delta}, baseline_samples=len(history))

    violated = _threshold(item, settings)
    if violated is not None:
        severity, score, support = violated
        return _result(item, metric_id, "ANOMALY", "THRESHOLD", "LIMIT_VIOLATION", severity=severity,
                       score=score, score_kind="LIMIT_EXCEEDANCE_RATIO_CAPPED", support=support,
                       baseline_samples=len(history))
    if item.metric_type in {"INTERFACE_STATE", "LINK_STATE", "AVAILABILITY"}:
        return _result(item, metric_id, "NORMAL", "THRESHOLD", "WITHIN_LIMIT",
                       score=0, score_kind="LIMIT_EXCEEDANCE_RATIO_CAPPED", baseline_samples=len(history))

    if len(history) >= settings.anomaly_baseline_min_samples:
        values = [float(row.value) for row in history]
        center = float(median(values))
        mad = float(median([abs(value - center) for value in values]))
        floor = 5.0 if item.metric_type == "LATENCY" else 0.5
        allowance = max(4 * 1.4826 * mad, floor)
        upper = center + allowance
        if float(item.value) > upper:
            excess = (float(item.value) - upper) / allowance
            return _result(item, metric_id, "ANOMALY", "BASELINE", "ABOVE_ROBUST_BASELINE",
                           severity=_severity(1 + excess), score=min(1.0, excess),
                           score_kind="BASELINE_EXCEEDANCE_RATIO_CAPPED",
                           support={"median": center, "mad": mad, "upper_limit": upper},
                           baseline_samples=len(history))
        # Lower latency/loss is an improvement, not a harmful outlier.
        isolated = _isolation(float(item.value), history, settings) if float(item.value) > center else None
        if isolated is not None:
            percentile, margin = isolated
            return _result(item, metric_id, "ANOMALY", "ISOLATION_FOREST", "MODEL_OUTLIER",
                           severity="MEDIUM" if percentile < 0.95 else "HIGH", score=percentile,
                           score_kind="ISOLATION_TAIL_PERCENTILE",
                           support={"decision_margin": margin, "median": center},
                           baseline_samples=len(history))
        return _result(item, metric_id, "NORMAL", "BASELINE", "WITHIN_BASELINE",
                       score=0, score_kind="BASELINE_EXCEEDANCE_RATIO_CAPPED",
                       support={"median": center, "mad": mad, "upper_limit": upper},
                       baseline_samples=len(history))
    return _result(item, metric_id, "NORMAL", "THRESHOLD", "WITHIN_LIMIT_BASELINE_INSUFFICIENT",
                   score=0, score_kind="LIMIT_EXCEEDANCE_RATIO_CAPPED", baseline_samples=len(history),
                   support={"required_baseline_samples": settings.anomaly_baseline_min_samples})
