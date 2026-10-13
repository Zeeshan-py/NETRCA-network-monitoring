"""Best-effort persistence in the existing fault_injections table."""
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.db.connection import transaction
from app.faults.models import FaultRecord


class FaultUnmapped(LookupError):
    """No exact stored device/link exists; the live lab remains authoritative."""


class FaultStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def save(self, record: FaultRecord, pre_state: dict) -> None:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                device_id = link_id = None
                if record.fault_type == "LINK_FAILURE":
                    cursor.execute("SELECT l.id, l.interface_source, l.interface_destination, "
                                   "a.name AS source, b.name AS destination FROM public.links l "
                                   "JOIN public.devices a ON a.id=l.source_device_id "
                                   "JOIN public.devices b ON b.id=l.destination_device_id "
                                   "WHERE a.is_active AND b.is_active AND "
                                   "((a.name=%s AND b.name=%s) OR (a.name=%s AND b.name=%s))",
                                   (record.target["source"], record.target["destination"],
                                    record.target["destination"], record.target["source"]))
                    interfaces = {entry["device"]: entry["interface"] for entry in pre_state["targets"]}
                    matches = [row for row in cursor.fetchall()
                               if row["interface_source"] == interfaces.get(row["source"])
                               and row["interface_destination"] == interfaces.get(row["destination"])]
                    if len(matches) != 1:
                        raise FaultUnmapped("Stored link is absent or ambiguous")
                    link_id = matches[0]["id"]
                else:
                    cursor.execute("SELECT id FROM public.devices WHERE name=%s AND is_active",
                                   (record.target["device"],))
                    row = cursor.fetchone()
                    if row is None:
                        raise FaultUnmapped("Stored device is absent")
                    device_id = row["id"]
                parameters = {"target": record.target, "validated_parameters": record.parameters,
                              "pre_state": pre_state, "expires_at": record.expires_at.isoformat(),
                              "end_reason": record.end_reason,
                              "restoration_result": record.restoration_result,
                              "error_code": record.error_code}
                cursor.execute(
                    "INSERT INTO public.fault_injections "
                    "(id, fault_type, device_id, link_id, severity, parameters, started_at, ended_at, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (id) DO UPDATE SET parameters=EXCLUDED.parameters, "
                    "ended_at=EXCLUDED.ended_at, status=EXCLUDED.status",
                    (record.id, record.fault_type, device_id, link_id, record.severity,
                     Jsonb(parameters), record.started_at, record.ended_at, record.status),
                )

    def get(self, identifier: UUID) -> dict | None:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id, fault_type, severity, parameters, started_at, ended_at, status "
                               "FROM public.fault_injections WHERE id=%s", (identifier,))
                return cursor.fetchone()

    def list(self, *, page: int, limit: int) -> dict:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT count(*) AS total FROM public.fault_injections")
                total = cursor.fetchone()["total"]
                cursor.execute("SELECT id, fault_type, severity, parameters, started_at, ended_at, status "
                               "FROM public.fault_injections ORDER BY started_at DESC, id DESC LIMIT %s OFFSET %s",
                               (limit, (page - 1) * limit))
                rows = cursor.fetchall()
        return {"data": rows, "pagination": {"page": page, "limit": limit, "total": total,
                                             "pages": (total + limit - 1) // limit}}
