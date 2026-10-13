"""Opt-in fault lifecycle persistence against PostgreSQL; all writes roll back."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.faults.models import FaultRecord
from app.faults.store import FaultStore, FaultUnmapped


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_FAULT_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real database rollback test")


def test_real_database_fault_lifecycle_mapping_and_rollback(monkeypatch):
    settings = Settings()
    assert settings.database_url, "Database URL required for opt-in test"
    store = FaultStore(settings)
    suffix = uuid4().hex[:12]
    start = datetime.now(timezone.utc)
    try:
        connection = psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10)
    except psycopg.Error:
        pytest.fail("Configured PostgreSQL endpoint is unavailable for the opt-in fault test", pytrace=False)
    with connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection

        monkeypatch.setattr("app.faults.store.transaction", same_transaction)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.devices (name,device_type,status) "
                           "VALUES (%s,'HOST','HEALTHY'),(%s,'SWITCH','HEALTHY')",
                           (f"phase7-{suffix}-a", f"phase7-{suffix}-b"))
            cursor.execute("SELECT id,name FROM public.devices WHERE name IN (%s,%s)",
                           (f"phase7-{suffix}-a", f"phase7-{suffix}-b"))
            ids = {name: identifier for identifier, name in cursor.fetchall()}
            cursor.execute("INSERT INTO public.links (source_device_id,destination_device_id,status,"
                           "interface_source,interface_destination) VALUES (%s,%s,'UP','h1-eth0','s1-eth1')",
                           (ids[f"phase7-{suffix}-a"], ids[f"phase7-{suffix}-b"]))

        state = {"mode": "admin", "targets": [
            {"device": f"phase7-{suffix}-a", "interface": "h1-eth0", "was_up": True},
            {"device": f"phase7-{suffix}-b", "interface": "s1-eth1", "was_up": True}]}
        record = FaultRecord(id=uuid4(), fault_type="LINK_FAILURE", status="ACTIVE",
                             target={"source": f"phase7-{suffix}-a", "destination": f"phase7-{suffix}-b"},
                             parameters={"duration_seconds": 30}, severity="MEDIUM", started_at=start,
                             expires_at=start + timedelta(seconds=30))
        store.save(record, state)
        assert store.get(record.id)["status"] == "ACTIVE"
        record.status = "COMPLETED"
        record.ended_at = datetime.now(timezone.utc)
        record.end_reason = "RECOVERED"
        record.restoration_result = "SUCCEEDED"
        store.save(record, state)
        stored = store.get(record.id)
        assert stored["status"] == "COMPLETED"
        assert stored["parameters"]["restoration_result"] == "SUCCEEDED"
        assert any(row["id"] == record.id for row in store.list(page=1, limit=100)["data"])
        wrong_state = {"mode": "admin", "targets": [dict(state["targets"][0]),
                                                   dict(state["targets"][1], interface="s1-eth9")]}
        with pytest.raises(FaultUnmapped):
            store.save(record.model_copy(update={"id": uuid4()}), wrong_state)
        connection.rollback()

    with psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10) as connection:
        assert connection.execute("SELECT 1 FROM public.fault_injections WHERE id=%s", (record.id,)).fetchone() is None
