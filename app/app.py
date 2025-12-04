"""
Sample Flask Application with OpenTelemetry Instrumentation
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
import random
import os

# Create Flask app
app = Flask(__name__)

# Configure OpenTelemetry Resource
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

# Create custom metrics
request_counter = meter.create_counter(
    name="http_requests_total",
    description="Total HTTP requests",
    unit="1"
)

request_duration = meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration",
    unit="ms"
)

# Instrument Flask
FlaskInstrumentor().instrument_app(app)

print("✅ OpenTelemetry configured successfully")
print(f"📡 Sending data to: {otlp_endpoint}")


@app.route("/")
def home():
    """Home endpoint"""
    request_counter.add(1, {"endpoint": "/", "method": "GET"})
    return jsonify({
        "message": "Dynatrace OpenTelemetry Lab",
        "status": "running",
        "endpoints": ["/", "/api/hello", "/api/data", "/api/slow"]
    })


@app.route("/api/hello")
def hello():
    """Simple hello endpoint"""
    start = time.time()
    
    with tracer.start_as_current_span("hello_handler") as span:
        span.set_attribute("endpoint", "/api/hello")
        
        name = "World"
        response = {"message": f"Hello, {name}!"}
        
        duration = (time.time() - start) * 1000
        request_counter.add(1, {"endpoint": "/api/hello", "method": "GET"})
        request_duration.record(duration, {"endpoint": "/api/hello"})
        
        return jsonify(response)


@app.route("/api/data")
def get_data():
    """Get data endpoint with database simulation"""
    start = time.time()
    
    with tracer.start_as_current_span("get_data") as span:
        span.set_attribute("endpoint", "/api/data")
        
        # Simulate database query
        with tracer.start_as_current_span("database.query") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.operation", "SELECT")
            time.sleep(0.05)  # Simulate query time
            
            data = [
                {"id": 1, "value": random.randint(1, 100)},
                {"id": 2, "value": random.randint(1, 100)},
                {"id": 3, "value": random.randint(1, 100)}
            ]
        
        duration = (time.time() - start) * 1000
        request_counter.add(1, {"endpoint": "/api/data", "method": "GET"})
        request_duration.record(duration, {"endpoint": "/api/data"})
        
        return jsonify({"data": data})


@app.route("/api/slow")
def slow_endpoint():
    """Intentionally slow endpoint"""
    start = time.time()
    
    with tracer.start_as_current_span("slow_operation") as span:
        span.set_attribute("endpoint", "/api/slow")
        
        sleep_time = random.uniform(1.0, 2.0)
        time.sleep(sleep_time)
        
        duration = (time.time() - start) * 1000
        request_counter.add(1, {"endpoint": "/api/slow", "method": "GET"})
        request_duration.record(duration, {"endpoint": "/api/slow"})
        
        return jsonify({
            "message": "Slow operation completed",
            "duration": round(sleep_time, 2)
        })


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Starting Dynatrace OpenTelemetry Demo App")
    print("="*60)
    print(f"Service Name: {os.getenv('OTEL_SERVICE_NAME', 'demo-app')}")
    print(f"OTLP Endpoint: {otlp_endpoint}")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False)
