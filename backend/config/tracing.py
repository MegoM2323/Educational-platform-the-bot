"""
OpenTelemetry Distributed Tracing Configuration for THE_BOT Platform

This module configures:
1. OpenTelemetry SDK initialization
2. Jaeger exporter setup
3. Django instrumentation (requests, database, Celery)
4. Custom span processors
5. Correlation ID propagation
6. Sampling configuration based on environment

Usage:
    from config.tracing import init_tracing

    # In Django settings initialization:
    if not settings.DEBUG or settings.ENVIRONMENT == 'test':
        init_tracing()
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace.sampling import (
    Sampler,
    SamplingResult,
    Decision,
)
from opentelemetry.trace import SpanKind
from opentelemetry.api.baggage import set_baggage
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.trace.propagation.jaeger import JaegerPropagator
from opentelemetry.trace.propagation.b3 import B3Format
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Sampler for Environment-Specific Sampling
# =============================================================================

class EnvironmentBasedSampler(Sampler):
    """
    Custom sampler that adjusts sampling percentage based on:
    - Environment (development, staging, production)
    - Span kind (always sample errors)
    - Operation type (always sample critical operations)
    - User role (sample higher for admin operations)
    """

    def __init__(self, default_rate: float = 0.1):
        """
        Initialize sampler with default sampling rate.

        Args:
            default_rate: Default sampling probability (0.0-1.0)
                - Development: 1.0 (100%)
                - Staging: 0.5 (50%)
                - Production: 0.1 (10%)
        """
        self.default_rate = default_rate

    def should_sample(
        self,
        parent_context,
        trace_id,
        name,
        kind: SpanKind = None,
        attributes=None,
        links=None,
        trace_state=None,
    ) -> SamplingResult:
        """
        Determine whether to sample this span.

        Always sample:
        - Errors and exceptions
        - Critical paths (authentication, payments)
        - Admin operations
        - Setup/teardown operations

        Default sample:
        - Other requests based on default_rate
        """
        attributes = attributes or {}

        # Always sample errors
        if attributes.get("error", False) or attributes.get("error.kind"):
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Always sample critical operations
        critical_paths = {
            "POST /api/auth/login",
            "POST /api/auth/logout",
            "POST /api/auth/token/refresh",
            "POST /api/payments/",
            "POST /api/payments/webhook",
            "POST /api/chat/rooms/",
            "POST /api/chat/messages/",
        }

        http_method = attributes.get("http.method", "")
        http_target = attributes.get("http.target", "")
        http_url = attributes.get("http.url", "")

        full_path = f"{http_method} {http_target or http_url}"

        if full_path in critical_paths:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Admin endpoints: higher sampling
        if "/admin/" in http_url:
            sampling_rate = min(self.default_rate * 10, 1.0)
            should_sample = trace_id % 100 < (sampling_rate * 100)
        else:
            # Default sampling rate
            should_sample = trace_id % 100 < (self.default_rate * 100)

        decision = Decision.RECORD_AND_SAMPLE if should_sample else Decision.DROP
        return SamplingResult(decision)


# =============================================================================
# Initialization Functions
# =============================================================================

def get_sampling_rate() -> float:
    """
    Get sampling rate based on environment.

    Returns:
        float: Sampling probability (0.0-1.0)
            - Development: 1.0 (100%)
            - Staging: 0.5 (50%)
            - Production/other: 0.1 (10%)
    """
    environment = os.getenv("ENVIRONMENT", "production").lower()

    if environment == "development":
        return 1.0
    elif environment == "staging":
        return 0.5
    else:
        return float(os.getenv("TRACING_SAMPLE_PERCENTAGE", "0.1")) / 100.0


def get_jaeger_exporter(
    agent_host: str = "localhost",
    agent_port: int = 6831,
    collector_endpoint: Optional[str] = None,
) -> JaegerExporter:
    """
    Create Jaeger exporter for trace export.

    Supports two modes:
    1. Agent mode: UDP to local Jaeger agent (faster, but limited)
    2. Collector mode: HTTP/gRPC to Jaeger collector (recommended)

    Args:
        agent_host: Jaeger agent hostname
        agent_port: Jaeger agent UDP port
        collector_endpoint: Jaeger collector HTTP endpoint
                          (uses agent mode if None)

    Returns:
        JaegerExporter instance
    """
    # Use environment variables if provided
    agent_host = os.getenv("JAEGER_AGENT_HOST", agent_host)
    agent_port = int(os.getenv("JAEGER_AGENT_PORT", agent_port))
    collector_endpoint = os.getenv(
        "JAEGER_COLLECTOR_ENDPOINT",
        collector_endpoint or f"http://{agent_host}:14250"
    )

    try:
        # Try collector endpoint first (gRPC)
        exporter = JaegerExporter(
            collector_endpoint=collector_endpoint,
        )
        logger.info(f"Using Jaeger collector at {collector_endpoint}")
        return exporter
    except Exception as e:
        logger.warning(f"Failed to create collector exporter: {e}")
        logger.warning(f"Falling back to Jaeger agent at {agent_host}:{agent_port}")

        # Fallback to agent mode (UDP)
        exporter = JaegerExporter(
            agent_host_name=agent_host,
            agent_port=agent_port,
        )
        return exporter


def get_resource() -> Resource:
    """
    Create OpenTelemetry Resource with service metadata.

    Includes:
    - Service name and version
    - Environment
    - Container/pod metadata (if running in container)
    - Git commit hash (if available)
    """
    attributes = {
        SERVICE_NAME: "thebot-platform",
        SERVICE_VERSION: os.getenv("SERVICE_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
    }

    # Add container metadata if available
    if os.path.exists("/.dockerenv"):
        attributes["container.runtime"] = "docker"

    # Add hostname
    import socket
    attributes["host.name"] = socket.gethostname()

    # Add git commit if available
    git_commit = os.getenv("GIT_COMMIT")
    if git_commit:
        attributes["vcs.revision"] = git_commit

    return Resource.create(attributes)


def init_tracing(
    enabled: bool = True,
    service_name: str = "thebot-platform",
    jaeger_enabled: bool = True,
    otlp_enabled: bool = False,
    sample_rate: Optional[float] = None,
) -> Optional[TracerProvider]:
    """
    Initialize OpenTelemetry tracing for Django application.

    This function:
    1. Creates TracerProvider with custom sampler
    2. Initializes Jaeger exporter
    3. Instruments Django, requests, database, Redis, Celery
    4. Sets up correlation ID propagation
    5. Configures span processors

    Args:
        enabled: Enable tracing (default True)
        service_name: Service name for traces
        jaeger_enabled: Enable Jaeger exporter
        otlp_enabled: Enable OTLP exporter
        sample_rate: Custom sampling rate (0.0-1.0),
                    uses environment-based rate if None

    Returns:
        TracerProvider instance or None if disabled
    """
    if not enabled:
        logger.info("OpenTelemetry tracing is disabled")
        return None

    try:
        # Determine sampling rate
        if sample_rate is None:
            sample_rate = get_sampling_rate()

        logger.info(f"Initializing OpenTelemetry with {sample_rate*100}% sampling")

        # Create resource
        resource = get_resource()

        # Create sampler
        sampler = EnvironmentBasedSampler(default_rate=sample_rate)

        # Create TracerProvider
        tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
            id_generator=RandomIdGenerator(),
            active_span_processor=None,
        )

        # Add Jaeger exporter
        if jaeger_enabled:
            try:
                jaeger_exporter = get_jaeger_exporter()
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(
                        jaeger_exporter,
                        max_queue_size=2048,
                        max_export_batch_size=512,
                        schedule_delay_millis=5000,
                    )
                )
                logger.info("Jaeger exporter configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Jaeger exporter: {e}")

        # Add OTLP exporter if enabled
        if otlp_enabled:
            try:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
                    insecure=True,
                )
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info("OTLP exporter configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure OTLP exporter: {e}")

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Instrument Django
        DjangoInstrumentor().instrument(
            excluded_urls="admin.*,.*static.*,.*media.*,health.*",
        )
        logger.info("Django instrumentation enabled")

        # Instrument requests library
        RequestsInstrumentor().instrument()
        logger.info("Requests instrumentation enabled")

        # Instrument database (psycopg2)
        Psycopg2Instrumentor().instrument()
        logger.info("Database instrumentation enabled")

        # Instrument Redis
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")

        # Instrument Celery
        try:
            CeleryInstrumentor().instrument()
            logger.info("Celery instrumentation enabled")
        except Exception as e:
            logger.warning(f"Failed to instrument Celery: {e}")

        # Instrument HTTPX
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")

        # Setup propagators for correlation ID propagation
        propagators = [
            JaegerPropagator(),
            B3Format(),
            W3CBaggagePropagator(),
        ]

        from opentelemetry.propagators.composite import CompositePropagator
        composite_propagator = CompositePropagator(propagators)
        from opentelemetry import propagators as otel_propagators
        otel_propagators._PROPAGATOR = composite_propagator

        logger.info("OpenTelemetry tracing initialized successfully")
        return tracer_provider

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return None


def setup_metrics() -> Optional[MeterProvider]:
    """
    Setup OpenTelemetry metrics collection.

    Initializes metrics exporters and instruments:
    - Prometheus (scrape endpoint)
    - OTLP (push to collector)

    Returns:
        MeterProvider instance
    """
    try:
        resource = get_resource()

        # Create metrics readers
        prometheus_reader = PrometheusMetricReader()

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader],
        )

        # Set global meter provider
        metrics.set_meter_provider(meter_provider)

        logger.info("Metrics collection initialized")
        return meter_provider

    except Exception as e:
        logger.error(f"Failed to initialize metrics: {e}")
        return None


def get_tracer(name: str = __name__, version: str = None) -> trace.Tracer:
    """
    Get tracer instance for creating spans.

    Args:
        name: Tracer name (usually __name__)
        version: Tracer version

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name, version)


def get_meter(name: str = __name__, version: str = None) -> metrics.Meter:
    """
    Get meter instance for recording metrics.

    Args:
        name: Meter name (usually __name__)
        version: Meter version

    Returns:
        Meter instance
    """
    return metrics.get_meter(name, version)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID in baggage for propagation across services.

    This ID will be included in all spans and propagated to
    downstream services via trace headers.

    Args:
        correlation_id: Unique ID for request correlation
    """
    set_baggage("correlation_id", correlation_id)
    # Also set in active span
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("correlation_id", correlation_id)
