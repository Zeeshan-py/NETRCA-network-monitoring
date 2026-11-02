"""Validated, file-backed network scenarios shared with the frontend."""
from functools import lru_cache
from ipaddress import IPv4Interface, ip_interface
import json
from pathlib import Path
import re
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, Field, field_validator, model_validator


SCENARIO_DIRECTORY = Path(__file__).resolve().parents[3] / "scenarios"
DEFAULT_SCENARIO_NAME = "netrca_lab_v1"
RUNTIME_NAMESPACE = UUID("09dfd2df-838b-4dd7-91fb-39b1970aa86f")
_SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
_SAFE_SCENARIO = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")


def stable_device_id(scenario_name: str, key: str) -> UUID:
    return uuid5(RUNTIME_NAMESPACE, f"{scenario_name}:device:{key}")


def stable_link_id(scenario_name: str, key: str) -> UUID:
    return uuid5(RUNTIME_NAMESPACE, f"{scenario_name}:link:{key}")


class ScenarioNode(BaseModel):
    id: UUID
    key: str
    name: str
    device_type: Literal["SWITCH", "HOST", "SERVER"]
    ip_address: str | None = None

    @field_validator("key", "name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _SAFE_NAME.fullmatch(value):
            raise ValueError("Node names must be safe Mininet identifiers")
        return value

    @field_validator("ip_address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        address = ip_interface(value)
        if not isinstance(address, IPv4Interface):
            raise ValueError("Mininet scenario addresses must be IPv4 interfaces")
        return str(address)


class ScenarioLink(BaseModel):
    id: UUID
    key: str
    source: str
    destination: str
    interface_source: str
    interface_destination: str

    @field_validator("source", "destination")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        if not _SAFE_NAME.fullmatch(value):
            raise ValueError("Link endpoints must be safe Mininet identifiers")
        return value

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        parts = value.split("--")
        if len(parts) != 2 or any(not _SAFE_NAME.fullmatch(part) for part in parts):
            raise ValueError("Link keys must use source--destination identifiers")
        return value

    @field_validator("interface_source", "interface_destination")
    @classmethod
    def validate_interface(cls, value: str) -> str:
        if not re.fullmatch(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$", value):
            raise ValueError("Interface names must use safe Linux identifiers")
        return value


class NetworkScenario(BaseModel):
    schema_version: Literal[1]
    name: str
    description: str = Field(min_length=1, max_length=500)
    nodes: list[ScenarioNode] = Field(min_length=2, max_length=64)
    links: list[ScenarioLink] = Field(min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_scenario_name(cls, value: str) -> str:
        if not _SAFE_SCENARIO.fullmatch(value):
            raise ValueError("Scenario names must use lowercase safe identifiers")
        return value

    @model_validator(mode="after")
    def validate_relationships(self):
        keys = [node.key for node in self.nodes]
        names = [node.name for node in self.nodes]
        node_ids = [node.id for node in self.nodes]
        if len(set(keys)) != len(keys) or len(set(names)) != len(names) or len(set(node_ids)) != len(node_ids):
            raise ValueError("Scenario nodes must have unique keys, names, and IDs")
        if any(node.key != node.name for node in self.nodes):
            raise ValueError("Canonical Mininet node keys and names must match")

        addresses = [str(ip_interface(node.ip_address).ip) for node in self.nodes if node.ip_address]
        if len(set(addresses)) != len(addresses):
            raise ValueError("Scenario node addresses must be unique")
        if any(node.ip_address is not None for node in self.nodes if node.device_type == "SWITCH"):
            raise ValueError("Switches must not claim host IP addresses")
        if any(node.ip_address is None for node in self.nodes if node.device_type in {"HOST", "SERVER"}):
            raise ValueError("Hosts and servers require IPv4 interface addresses")
        if any(node.id != stable_device_id(self.name, node.key) for node in self.nodes):
            raise ValueError("Scenario node IDs must match the deterministic ID contract")

        known = set(keys)
        link_ids: set[UUID] = set()
        link_keys: set[str] = set()
        interface_names: set[str] = set()
        pairs: set[frozenset[str]] = set()
        for link in self.links:
            if link.id in link_ids or link.key in link_keys:
                raise ValueError("Scenario links must have unique keys and IDs")
            if link.source not in known or link.destination not in known:
                raise ValueError("Scenario links must reference known endpoints")
            if link.source == link.destination:
                raise ValueError("Scenario links cannot connect a node to itself")
            if link.key != f"{link.source}--{link.destination}":
                raise ValueError("Scenario link keys must match their ordered endpoints")
            if link.id != stable_link_id(self.name, link.key):
                raise ValueError("Scenario link IDs must match the deterministic ID contract")
            if link.interface_source in interface_names or link.interface_destination in interface_names:
                raise ValueError("Scenario interface names must be unique")
            if not link.interface_source.startswith(f"{link.source}-") or not link.interface_destination.startswith(f"{link.destination}-"):
                raise ValueError("Scenario interfaces must belong to their declared endpoints")
            pair = frozenset((link.source, link.destination))
            if pair in pairs:
                raise ValueError("Scenario cannot contain duplicate undirected links")
            link_ids.add(link.id)
            link_keys.add(link.key)
            interface_names.update((link.interface_source, link.interface_destination))
            pairs.add(pair)
        return self

    @property
    def host_names(self) -> tuple[str, ...]:
        return tuple(node.key for node in self.nodes if node.device_type in {"HOST", "SERVER"})

    def components(self) -> list[list[str]]:
        adjacency = {node.key: set() for node in self.nodes}
        for link in self.links:
            adjacency[link.source].add(link.destination)
            adjacency[link.destination].add(link.source)
        remaining = set(adjacency)
        result: list[list[str]] = []
        while remaining:
            start = min(remaining)
            component: set[str] = set()
            frontier = [start]
            while frontier:
                current = frontier.pop()
                if current in component:
                    continue
                component.add(current)
                frontier.extend(adjacency[current] - component)
            remaining -= component
            result.append(sorted(component))
        return sorted(result, key=lambda group: group[0])


@lru_cache(maxsize=8)
def load_scenario(name: str = DEFAULT_SCENARIO_NAME) -> NetworkScenario:
    if not _SAFE_SCENARIO.fullmatch(name):
        raise ValueError("Invalid scenario name")
    path = SCENARIO_DIRECTORY / f"{name}.json"
    if not path.is_file():
        raise ValueError("Unknown network scenario")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Network scenario could not be loaded") from error
    return NetworkScenario.model_validate(payload)


DEFAULT_SCENARIO = load_scenario(DEFAULT_SCENARIO_NAME)
