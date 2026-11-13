import os
from dataclasses import dataclass

from fastapi import Header, HTTPException, Query, status


ACTORS = {
    "depot_operations_controller",
    "truck_driver",
    "yard_depot_clerk",
    "border_liaison",
    "port_agent",
    "management_compliance",
    "customer_service_client",
}


DEFAULT_API_KEYS = {
    "depot-controller-demo-key": "depot_operations_controller",
    "truck-driver-demo-key": "truck_driver",
    "yard-clerk-demo-key": "yard_depot_clerk",
    "border-liaison-demo-key": "border_liaison",
    "port-agent-demo-key": "port_agent",
    "management-demo-key": "management_compliance",
    "client-demo-key": "customer_service_client",
}


INTERNAL_READERS = {
    "depot_operations_controller",
    "truck_driver",
    "yard_depot_clerk",
    "border_liaison",
    "port_agent",
    "management_compliance",
}

CONTROL_TOWER_READERS = {
    "depot_operations_controller",
    "management_compliance",
}

TRACKING_READERS = {
    "depot_operations_controller",
    "management_compliance",
    "customer_service_client",
}

EVENT_CREATORS = {
    "depot_operations_controller",
    "truck_driver",
    "yard_depot_clerk",
    "border_liaison",
    "port_agent",
}


ACTOR_EVENT_RULES = {
    "depot_operations_controller": {"*"},
    "truck_driver": {"STATUS_CONFIRMED", "PICKED_UP", "AT_CHECKPOINT", "DELIVERED"},
    "yard_depot_clerk": {"GATE_IN", "GATE_OUT", "SEAL_CHECK", "YARD_RECEIVED"},
    "border_liaison": {"ARRIVED_BORDER", "QUEUED_BORDER", "CLEARED_BORDER", "HANDOVER"},
    "port_agent": {"PORT_ARRIVED", "PORT_GATE_IN", "PORT_RELEASED", "PORT_DEPARTED"},
}


@dataclass(frozen=True)
class AuthContext:
    api_key: str
    actor: str


def load_api_keys():
    raw_value = os.getenv("BORDERFLOW_API_KEYS", "")
    api_keys = dict(DEFAULT_API_KEYS)

    if raw_value.strip():
        api_keys = {}
        for entry in raw_value.split(","):
            entry = entry.strip()
            if not entry:
                continue
            try:
                api_key, actor = entry.split(":", 1)
            except ValueError as exc:
                raise RuntimeError(
                    "BORDERFLOW_API_KEYS entries must use api_key:actor format"
                ) from exc
            normalized_actor = actor.strip().lower()
            if normalized_actor not in ACTORS:
                raise RuntimeError(f"Unsupported RBAC actor: {actor}")
            api_keys[api_key.strip()] = normalized_actor

    return api_keys


def require_actors(*allowed_actors: str):
    normalized_allowed = {actor.lower() for actor in allowed_actors}
    unknown_actors = normalized_allowed - ACTORS
    if unknown_actors:
        raise RuntimeError(f"Unsupported RBAC actors requested: {sorted(unknown_actors)}")

    def dependency(
        x_api_key: str = Header(default="", alias="X-API-Key"),
        api_key: str = Query(default=""),
    ):
        api_keys = load_api_keys()
        effective_api_key = x_api_key or api_key
        actor = api_keys.get(effective_api_key)

        if actor is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid API key",
            )

        if actor not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Actor is not permitted for this action",
            )

        return AuthContext(api_key=effective_api_key, actor=actor)

    return dependency


def validate_event_permission(actor: str, event_type: str):
    if actor not in EVENT_CREATORS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor cannot create operational events",
        )

    normalized_event_type = event_type.strip().upper()
    allowed_events = ACTOR_EVENT_RULES[actor]

    if "*" not in allowed_events and normalized_event_type not in allowed_events:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Actor {actor} cannot create event type {normalized_event_type}",
        )

    return normalized_event_type
