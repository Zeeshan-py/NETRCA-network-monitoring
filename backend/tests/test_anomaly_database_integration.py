"""Opt-in real PostgreSQL rollback test; does not change remote schema."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from app.anomaly.engine import detect
from app.anomaly.store import AnomalyStore
from app.core.config import Settings


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_ANOMALY_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real database rollback test")


def test_real_metric_history_and_anomaly_idempotence_rollback(monkeypatch):
    settings = Settings()
    assert settings.database_url, "A configured database is required"
    try:
        connection = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable", pytrace=False)
    with connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection

        monkeypatch.setattr("app.anomaly.store.transaction", same_transaction)
        name = f"phase8-{uuid4().hex[:12]}"
        observed = datetime.now(timezone.utc).replace(microsecond=0)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.devices (name,device_type,status) "
                           "VALUES (%s,'HOST','HEALTHY') RETURNING id", (name,))
            device_id = cursor.fetchone()[0]
            for index in range(20):
                cursor.execute("INSERT INTO public.metrics "
                               "(device_id,metric_type,value,unit,timestamp,metadata) "
                               "VALUES (%s,'LATENCY',%s,'ms',%s,%s)",
                               (device_id, 20 + index % 3, observed - timedelta(minutes=index + 1),
                                Jsonb({"source": "manual", "observation_key": f"phase8:{name}:{index}"})))
            cursor.execute("INSERT INTO public.metrics "
                           "(device_id,metric_type,value,unit,timestamp,metadata) "
                           "VALUES (%s,'LATENCY',%s,'ms',%s,%s) RETURNING id",
                           (device_id, 80, observed,
                            Jsonb({"source": "manual", "observation_key": f"phase8:{name}:candidate"})))
            candidate_id = cursor.fetchone()[0]
        store = AnomalyStore(settings)
        loaded = store.load([candidate_id])
        assert len(loaded) == 1 and len(loaded[0][2]) == 20
        finding = detect(loaded[0][1], loaded[0][2], settings, metric_id=candidate_id)
        assert finding.status == "ANOMALY" and finding.method == "BASELINE"
        anomaly_id, created = store.save(finding)
        assert created and store.get(anomaly_id)["metric_id"] == candidate_id
        assert store.save(finding) == (anomaly_id, False)
        connection.rollback()
        assert connection.execute("SELECT 1 FROM public.anomalies WHERE id=%s", (anomaly_id,)).fetchone() is None
