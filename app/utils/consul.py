"""Consul service registration — runs once on startup in a background thread."""

import logging
import os
import socket
import threading
import time

import requests

logger = logging.getLogger(__name__)

_CONSUL_URL = os.environ.get("CONSUL_URL", "http://consul:8500")

_USER_TAGS = [
    "traefik.enable=true",
    "traefik.http.routers.user.rule=Host(`users.universidad.localhost`)",
    "traefik.http.routers.user.entryPoints=https",
    "traefik.http.routers.user.tls=true",
    "traefik.http.routers.user.middlewares=user,bulkhead-user,cors-user",
    "traefik.http.middlewares.cors-user.headers.accesscontrolalloworiginlist=*",
    "traefik.http.middlewares.cors-user.headers.accesscontrolallowmethods=GET,POST,OPTIONS",
    "traefik.http.middlewares.cors-user.headers.accesscontrolallowheaders=Content-Type,Authorization",
    "traefik.http.middlewares.cors-user.headers.addvaryheader=true",
    "traefik.http.services.user.loadbalancer.server.port=5000",
    "traefik.http.middlewares.user.circuitbreaker.expression=LatencyAtQuantileMS(50.0) > 2000 || ResponseCodeRatio(500, 600, 0, 600) > 0.30 || NetworkErrorRatio() > 0.10",
    "traefik.http.middlewares.bulkhead-user.inflightreq.amount=10",
]


def register_user(port: int = 5000) -> None:
    """Register the User service with Consul on startup."""
    _start(service_name="user", port=port, tags=_USER_TAGS)


def _start(service_name: str, port: int, tags: list) -> None:
    threading.Thread(
        target=_register_with_retry,
        args=(service_name, port, tags),
        daemon=True,
    ).start()


def _register_with_retry(service_name: str, port: int, tags: list) -> None:
    hostname = socket.gethostname()
    service_id = f"{service_name}-{hostname}"
    payload = {
        "ID": service_id,
        "Name": service_name,
        "Address": hostname,
        "Port": port,
        "Tags": tags,
        "Check": {
            "HTTP": f"http://{hostname}:{port}/health",
            "Interval": "15s",
            "Timeout": "5s",
            "DeregisterCriticalServiceAfter": "30s",
        },
    }

    for attempt in range(10):
        try:
            resp = requests.put(
                f"{_CONSUL_URL}/v1/agent/service/register",
                json=payload,
                timeout=5,
            )
            if resp.status_code == 200:
                logger.info("Registered with Consul as %s", service_id)
                return
            logger.warning("Consul registration HTTP %s", resp.status_code)
        except Exception as exc:
            logger.warning("Consul registration attempt %d failed: %s", attempt + 1, exc)
        time.sleep(5)

    logger.error("Failed to register with Consul after %d attempts", 10)
