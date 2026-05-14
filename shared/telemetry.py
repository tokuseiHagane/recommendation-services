"""Logfire-based telemetry for Litestar services.

Uses logfire.configure(send_to_logfire=False) to export traces via standard
OTEL_EXPORTER_OTLP_ENDPOINT / OTEL_EXPORTER_OTLP_PROTOCOL env vars.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar.plugins import PluginProtocol


def configure_telemetry() -> list[PluginProtocol]:
    """Initialize Logfire, return Litestar plugins list (empty if OTel not configured)."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        print("[telemetry] OTEL_EXPORTER_OTLP_ENDPOINT not set, skipping", flush=True)
        return []

    import logfire
    from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
    from logfire._internal.integrations.asgi import tweak_asgi_spans_tracer_provider

    service_name = os.environ.get("OTEL_SERVICE_NAME", "unknown")
    logfire_instance = logfire.configure(
        send_to_logfire=False,
        service_name=service_name,
    )

    plugin = OpenTelemetryPlugin(
        OpenTelemetryConfig(
            tracer_provider=tweak_asgi_spans_tracer_provider(
                logfire_instance, record_send_receive=False
            )
        )
    )

    print(f"[telemetry] logfire+OTelPlugin configured: service={service_name} endpoint={endpoint}", flush=True)
    return [plugin]
