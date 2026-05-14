"""Programmatic OpenTelemetry SDK configuration for Litestar services."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar.contrib.opentelemetry import OpenTelemetryConfig


def configure_otel() -> OpenTelemetryConfig | None:
    """Set up TracerProvider and return Litestar OpenTelemetryConfig, or None if not configured."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        print("[telemetry] OTEL_EXPORTER_OTLP_ENDPOINT not set, skipping", flush=True)
        return None

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service_name = os.environ.get("OTEL_SERVICE_NAME", "unknown")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
    if protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    from litestar.contrib.opentelemetry import OpenTelemetryConfig as OTelCfg

    print(f"[telemetry] OTel configured: service={service_name} endpoint={endpoint}", flush=True)
    return OTelCfg(tracer_provider=provider, exclude=["/health", "/metrics"])
