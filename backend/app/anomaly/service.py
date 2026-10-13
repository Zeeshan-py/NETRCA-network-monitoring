"""Bounded orchestration of local and stored Phase 6 observations."""
from app.anomaly.engine import detect
from app.anomaly.models import DetectionRequest, DetectionResult
from app.anomaly.store import AnomalyStore, MetricNotFound
from app.core.config import Settings
from app.db.connection import DatabaseUnavailable


class DuplicateObservation(ValueError):
    pass


class AnomalyService:
    def __init__(self, settings: Settings, store: AnomalyStore):
        self.settings = settings
        self.store = store

    def run(self, request: DetectionRequest) -> dict:
        findings: list[DetectionResult] = []
        if request.observations is not None:
            unique = {}
            for item in request.observations:
                previous = unique.get(item.observation_key)
                if previous is not None and previous != item:
                    raise DuplicateObservation("Observation key has conflicting measurements")
                unique[item.observation_key] = item
            by_measurement = {}
            for item in unique.values():
                fingerprint = (item.device_id, item.link_id, item.metric_type, item.value,
                               item.unit, item.timestamp, item.interface, item.target)
                by_measurement.setdefault(fingerprint, item)
            observations = list(by_measurement.values())
            for item in observations:
                findings.append(detect(item, observations, self.settings))
        else:
            for identifier, item, history in self.store.load(request.metric_ids):
                finding = detect(item, history, self.settings, metric_id=identifier)
                if request.persist:
                    if finding.status == "ANOMALY":
                        try:
                            finding.anomaly_id, created = self.store.save(finding)
                            finding.persistence = "PERSISTED" if created else "EXISTING"
                        except (DatabaseUnavailable, MetricNotFound):
                            finding.persistence = "UNAVAILABLE"
                    else:
                        finding.persistence = "NOT_ELIGIBLE"
                findings.append(finding)
        return {"items": findings, "anomalies_detected": sum(item.status == "ANOMALY" for item in findings),
                "insufficient_data": sum(item.status == "INSUFFICIENT_DATA" for item in findings),
                "persisted": sum(item.persistence == "PERSISTED" for item in findings)}
