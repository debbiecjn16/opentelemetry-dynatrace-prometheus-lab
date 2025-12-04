"""
Sample Application - Sends data to OpenTelemetry Collector
"""

from flask import Flask, jsonify
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
import time
import os

app = Flask(__name__)

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "demo-app"),
    "service.version": "1.0.0",
    "deployment.environment": "lab",
})

# Setup Tracing
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
trace_provider = TracerProvider(resource=resource)
trace_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# Setup Metrics
metric_exporter = OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics")
metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Create metrics
request_counter = meter.create_counter(
    name="http_requests_total",
    description="Total HTTP requests",
    unit="1"
)

# Instrument Flask
FlaskInstrumentor().instrument_app(app)

print(f"✅ Sending telemetry to: {otlp_endpoint}")


@app.route("/")
def home():
    request_counter.add(1, {"endpoint": "/"})
    return jsonify({
        "message": "Dynatrace Multi-Export Lab",
        "status": "running"
    })


@app.route("/api/test")
def test():
    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("endpoint", "/api/test")
        time.sleep(0.1)  # Simulate work
        
        request_counter.add(1, {"endpoint": "/api/test"})
        return jsonify({"result": "success"})


if __name__ == "__main__":
    print("🚀 Starting application...")
    app.run(host="0.0.0.0", port=5000, debug=False)
