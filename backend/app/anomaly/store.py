"""Read Phase 6 metrics and write only detected findings to the existing table."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from app.anomaly.models import DetectionResult
from app.core.config import Settings
from app.db.connection import transaction
from app.pipeline.models import MetricIn


class MetricNotFound(LookupError):
    pass


class StoredMetricInvalid(ValueError):
    pass


def _metric(row: dict) -> MetricIn:
    metadata = row["metadata"] or {}
    try:
        return MetricIn(device_id=row["device_id"], link_id=row["link_id"],
                        metric_type=row["metric_type"], value=row["value"], unit=row["unit"],
                        timestamp=row["timestamp"], source=metadata.get("source"),
                        observation_key=metadata.get("observation_key"),
                        interface=metadata.get("interface"), target=metadata.get("target"))
    except (ValidationError, TypeError, AttributeError):
        raise StoredMetricInvalid("Stored metric lacks validated Phase 6 provenance or values") from None


def model_version(settings: Settings) -> str:
    fields = (settings.anomaly_latency_ms, settings.anomaly_packet_loss_percent,
              settings.anomaly_min_availability_percent, settings.anomaly_error_delta,
              settings.anomaly_max_age_minutes, settings.anomaly_history_hours,
              settings.anomaly_max_history, settings.anomaly_baseline_min_samples,
              settings.anomaly_model_min_samples,
              settings.anomaly_model_contamination, settings.anomaly_ml_enabled)
    return "v1-" + sha256(json.dumps(fields).encode()).hexdigest()[:12]


class AnomalyStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def load(self, identifiers: list[UUID]) -> list[tuple[UUID, MetricIn, list[MetricIn]]]:
        unique_ids = list(dict.fromkeys(identifiers))
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id,device_id,link_id,metric_type,value,unit,timestamp,metadata "
                               "FROM public.metrics WHERE id = ANY(%s)", (unique_ids,))
                found = {row["id"]: row for row in cursor.fetchall()}
                if len(found) != len(unique_ids):
                    raise MetricNotFound("One or more stored metrics were not found")
                results = []
                for identifier in unique_ids:
                    item = _metric(found[identifier])
                    cursor.execute(
                        "SELECT id,device_id,link_id,metric_type,value,unit,timestamp,metadata "
                        "FROM public.metrics WHERE device_id IS NOT DISTINCT FROM %s "
                        "AND link_id IS NOT DISTINCT FROM %s AND metric_type=%s AND unit=%s "
                        "AND metadata->>'interface' IS NOT DISTINCT FROM %s "
                        "AND metadata->>'target' IS NOT DISTINCT FROM %s "
                        "AND timestamp >= %s AND timestamp < %s "
                        "ORDER BY timestamp DESC,id DESC LIMIT %s",
                        (item.device_id, item.link_id, item.metric_type, item.unit,
                         item.interface, item.target,
                         item.timestamp - timedelta(hours=self.settings.anomaly_history_hours),
                         item.timestamp, self.settings.anomaly_max_history),
                    )
                    history = []
                    for row in cursor.fetchall():
                        try:
                            history.append(_metric(row))
                        except StoredMetricInvalid:
                            continue
                    results.append((identifier, item, history))
        return results

    def save(self, finding: DetectionResult) -> tuple[UUID, bool]:
        if finding.metric_id is None or finding.status != "ANOMALY" or finding.score is None or finding.severity is None:
            raise ValueError("Only detected stored-metric anomalies can be persisted")
        name = "NETRCA_" + finding.method
        version = model_version(self.settings)
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                # Lock the source row so concurrent detections serialize without a new schema index.
                cursor.execute("SELECT id FROM public.metrics WHERE id=%s FOR UPDATE", (finding.metric_id,))
                if cursor.fetchone() is None:
                    raise MetricNotFound("Source metric was removed")
                cursor.execute("SELECT id FROM public.anomalies WHERE metric_id=%s AND model_name=%s "
                               "AND model_version=%s ORDER BY detected_at DESC LIMIT 1",
                               (finding.metric_id, name, version))
                existing = cursor.fetchone()
                if existing:
                    return existing["id"], False
                cursor.execute(
                    "INSERT INTO public.anomalies (metric_id,device_id,model_name,model_version,"
                    "anomaly_score,is_anomaly,severity,detected_at,features,metadata) "
                    "VALUES (%s,%s,%s,%s,%s,true,%s,%s,%s,%s) RETURNING id",
                    (finding.metric_id, finding.device_id, name, version, finding.score,
                     finding.severity, datetime.now(timezone.utc),
                     Jsonb({"metric_type": finding.metric_type, "value": str(finding.value),
                            "unit": finding.unit, "baseline_samples": finding.baseline_samples,
                            "support": finding.support}),
                     Jsonb({"reason": finding.reason, "score_kind": finding.score_kind,
                            "observation_key": finding.observation_key,
                            "observed_at": finding.observed_at.isoformat()})),
                )
                return cursor.fetchone()["id"], True

    def get(self, identifier: UUID) -> dict | None:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id,device_id,metric_id,event_id,model_name,model_version,"
                               "anomaly_score,is_anomaly,severity,detected_at,features,metadata "
                               "FROM public.anomalies WHERE id=%s", (identifier,))
                return cursor.fetchone()

    def list(self, *, page: int, limit: int, device_id: UUID | None, is_anomaly: bool | None) -> dict:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                where = "WHERE (%s::uuid IS NULL OR device_id=%s) AND (%s::boolean IS NULL OR is_anomaly=%s)"
                params = (device_id, device_id, is_anomaly, is_anomaly)
                cursor.execute("SELECT count(*) AS total FROM public.anomalies " + where, params)
                total = cursor.fetchone()["total"]
                cursor.execute("SELECT id,device_id,metric_id,event_id,model_name,model_version,"
                               "anomaly_score,is_anomaly,severity,detected_at,features,metadata "
                               "FROM public.anomalies " + where +
                               " ORDER BY detected_at DESC,id DESC LIMIT %s OFFSET %s",
                               (*params, limit, (page - 1) * limit))
                rows = cursor.fetchall()
        return {"data": rows, "pagination": {"page": page, "limit": limit, "total": total,
                                               "pages": (total + limit - 1) // limit}}

    def statistics(self) -> dict:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT count(*) AS total, count(*) FILTER (WHERE is_anomaly) AS detected "
                               "FROM public.anomalies")
                return cursor.fetchone()
