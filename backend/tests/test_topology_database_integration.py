"""Opt-in real PostgreSQL checks; all inserted records roll back."""
import os
from contextlib import contextmanager
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.topology.models import DeviceCreate, LinkCreate
from app.topology.store import TopologyConflict, TopologyNotFound, TopologyStore


pytestmark = pytest.mark.skipif(os.environ.get("NETRCA_RUN_TOPOLOGY_DB_TESTS") != "1",
                                reason="Requires explicit opt-in to real database rollback test")


def test_real_database_create_retrieve_validate_and_rollback(monkeypatch):
    settings = Settings()
    assert settings.database_url, "A database URL is required for the opt-in test"
    store = TopologyStore(settings)
    store.load()  # Read existing schema before the test transaction.
    with psycopg.connect(settings.database_url.get_secret_value(), sslmode="require", connect_timeout=10) as connection:
        @contextmanager
        def same_transaction(_settings, **_kwargs):
            yield connection

        original_transaction = __import__("app.topology.store", fromlist=["transaction"]).transaction
        monkeypatch.setattr("app.topology.store.transaction", same_transaction)
        snapshot = store.create_snapshot("Phase 4 rollback test")
        assert snapshot.reason == "Phase 4 rollback test"
        assert store.list_snapshots(1)[0].id == snapshot.id
        token = uuid4().hex[:12]
        first = store.create_device(DeviceCreate(name=f"phase4-{token}-a", device_type="SWITCH", status="HEALTHY",
                                                 ip_address=f"2001:db8::{int(token[:4], 16):x}"))
        second = store.create_device(DeviceCreate(name=f"phase4-{token}-b", device_type="HOST", status="HEALTHY"))
        assert store.get_device(first.id).name == first.name
        assert store.get_device(first.id).ip_address == first.ip_address
        link = store.create_link(LinkCreate(source_device_id=first.id, destination_device_id=second.id, status="UP"))
        assert store.get_link(link.id).destination_device_id == second.id
        with pytest.raises(TopologyConflict, match="DUPLICATE_LINK"):
            store.create_link(LinkCreate(source_device_id=second.id, destination_device_id=first.id, status="UP"))
        with pytest.raises(TopologyConflict, match="INVALID_LINK_ENDPOINT"):
            store.create_link(LinkCreate(source_device_id=first.id, destination_device_id=uuid4(), status="UP"))
        connection.rollback()
    monkeypatch.setattr("app.topology.store.transaction", original_transaction)
    with pytest.raises(TopologyNotFound):
        store.get_device(first.id)
    assert all(item.id != snapshot.id for item in store.list_snapshots(100))
