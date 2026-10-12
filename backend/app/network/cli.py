"""Explicit local lab commands: python -m app.network.cli environment|smoke."""
import argparse
import json

from app.core.config import get_settings
from app.network.environment import check_environment
from app.network.errors import NetworkError
from app.network.manager import NetworkManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or smoke-test the owned Mininet lab")
    parser.add_argument("command", choices=("environment", "smoke"))
    args = parser.parse_args()
    report = check_environment()
    if args.command == "environment":
        print(json.dumps(report.model_dump()))
        return 0 if report.available else 1
    settings = get_settings()
    manager = NetworkManager(enabled=settings.simulation_enabled)
    try:
        manager.start_network().result(timeout=60)
        topology = manager.get_topology()
        result = manager.test_connectivity().result(timeout=30)
        if not result.connected:
            print(json.dumps({"connected": False, "packet_loss_percent": result.packet_loss_percent}))
            return 1
        manager.reset_network().result(timeout=60)
        after_reset = manager.test_connectivity().result(timeout=30)
        if not after_reset.connected:
            print(json.dumps({"connected_after_reset": False, "packet_loss_percent": after_reset.packet_loss_percent}))
            return 1
        manager.stop_network().result(timeout=30)
        print(json.dumps({
            "topology_name": topology.topology_name,
            "nodes": [node.name for node in topology.nodes],
            "links": [{"source": link.source, "destination": link.destination, "status": link.status} for link in topology.links],
            "connected": True,
            "connected_after_reset": True,
            "final_state": manager.get_status().state,
        }))
        return 0
    except NetworkError as error:
        print(json.dumps({"success": False, "error": {"code": error.code, "message": str(error)}}))
        return 1
    finally:
        try:
            manager.close(timeout=30)
        except Exception:
            print("Owned Mininet cleanup failed; inspect this lab before retrying")


if __name__ == "__main__":
    raise SystemExit(main())
