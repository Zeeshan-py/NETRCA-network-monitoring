"""Opt-in WSL Mininet observations persisted through real PostgreSQL, then rolled back."""
import json
import os
import shutil
import subprocess
from contextlib import contextmanager

import psycopg
import pytest

from app.core.config import Settings
from app.monitoring.models import MonitoringSnapshot, ProbeReading
from app.pipeline.store import EvidenceStore


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_PIPELINE_LAB_TESTS") != "1",
                                reason="Requires explicit opt-in to WSL Mininet and PostgreSQL rollback test")


def test_real_phase5_mininet_output_reaches_postgresql_and_rolls_back(monkeypatch):
    if not shutil.which("wsl"):
        pytest.skip("WSL launcher unavailable")
    script = """import json
from app.network.manager import NetworkManager
m = NetworkManager(enabled=True)
try:
    m.start_network().result(timeout=60)
    snapshot = m.monitor_snapshot().result(timeout=30)
    probe = m.probe_hosts('h1','h2',count=2,timeout_seconds=2).result(timeout=20)
    print('NETRCA_RESULT:' + json.dumps({'snapshot': snapshot.model_dump(mode='json'), 'probe': probe.model_dump(mode='json')}))
finally:
    m.close(timeout=30)
"""
    result = subprocess.run(
        ["wsl", "-d", "Ubuntu", "-u", "root", "--", "/home/zeeshan/netrca-venv/bin/python", "-c", script],
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stderr[-1000:]
    lines = [line for line in result.stdout.splitlines() if line.startswith("NETRCA_RESULT:")]
    assert len(lines) == 1, result.stdout[-1000:]
    payload = json.loads(lines[0].split(":", 1)[1])
    snapshot = MonitoringSnapshot.model_validate(payload["snapshot"])
    probe = ProbeReading.model_validate(payload["probe"])
    assert snapshot.collection_status == "COMPLETE", snapshot.errors
    assert probe.status == "REACHABLE"

    settings = Settings()
    assert settings.database_url, "Database URL required for opt-in test"
    store = EvidenceStore(settings)
    with psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10) as connection:
        @contextmanager
        def same_transaction(_settings):
            yield connection
        monkeypatch.setattr("app.pipeline.store.transaction", same_transaction)
        with connection.cursor() as cursor:
            for device in snapshot.devices:
                cursor.execute("INSERT INTO public.devices (name, device_type, status) "
                               "VALUES (%s,%s,'HEALTHY') ON CONFLICT (name) DO NOTHING",
                               (device.name, device.device_type))
            cursor.execute("SELECT id, name FROM public.devices WHERE name = ANY(%s)",
                           ([device.name for device in snapshot.devices],))
            device_ids = {name: identifier for identifier, name in cursor.fetchall()}
            for link in snapshot.links:
                cursor.execute("INSERT INTO public.links (source_device_id, destination_device_id, status, "
                               "interface_source, interface_destination) VALUES (%s,%s,'UP',%s,%s)",
                               (device_ids[link.source], device_ids[link.destination],
                                link.interface_source, link.interface_destination))
        stored_snapshot = store.ingest_snapshot(snapshot)
        stored_probe = store.ingest_probe(probe)
        assert stored_snapshot["metrics"] > 0
        assert stored_snapshot["unmapped_links"] == 0
        assert stored_probe["metrics"] == 3
        assert stored_snapshot["events"] == 0
        connection.rollback()
