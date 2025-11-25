# DSPy Runtime for KGCL

Production-ready DSPy + Ollama runtime with comprehensive observability, error handling, and UNRDF integration.

## Overview

The DSPy runtime provides a bridge between KGCL's knowledge graph capabilities and DSPy's structured LLM interactions via Ollama. It enables:

- **Dynamic Signature Invocation**: Load and execute DSPy signatures from Python modules
- **Receipt Generation**: Capture comprehensive metadata about each invocation in RDF format
- **UNRDF Integration**: External capability interface for knowledge graph workflows
- **Observability**: OpenTelemetry instrumentation for spans and metrics
- **Production-Ready**: Comprehensive error handling and fallback mechanisms

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     UNRDF Bridge                            │
│  (External Capability Interface for Knowledge Graph)       │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├──────> Ollama LM Configuration
               │        - Environment-based setup
               │        - Model management
               │        - Health checks
               │
               ├──────> Signature Invoker
               │        - Dynamic module loading
               │        - Prediction execution
               │        - Error handling
               │
               └──────> Receipt Generator
                        - Metadata capture
                        - RDF storage
                        - Provenance tracking
```

## Components

### 1. Ollama LM Configuration (`ollama_config.py`)

Manages DSPy language model setup with Ollama backend.

**Features:**
- Environment variable configuration
- Model availability checks
- Fallback handling
- Health monitoring

**Environment Variables:**
```bash
OLLAMA_MODEL=llama3.1          # Model name (default: llama3.1)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama server URL
OLLAMA_TEMPERATURE=0.7          # Temperature (default: 0.7)
OLLAMA_MAX_TOKENS=2048          # Max tokens (default: 2048)
OLLAMA_TIMEOUT=30               # Request timeout in seconds (default: 30)
```

**Example:**
```python
from kgcl.dspy_runtime import configure_ollama, health_check

# Configure with environment variables
lm = configure_ollama()

# Check health
health = health_check()
if health["status"] == "healthy":
    print("Ready to invoke signatures!")
```

### 2. Signature Invoker (`invoker.py`)

Dynamically loads DSPy signatures and executes predictions.

**Features:**
- Module-based signature loading
- Input validation
- Signature caching
- Comprehensive metrics collection

**Example:**
```python
from kgcl.dspy_runtime import SignatureInvoker

invoker = SignatureInvoker()

# Load and invoke signature
result = invoker.invoke_from_module(
    module_path="/path/to/signature.py",
    signature_name="MySignature",
    inputs={"question": "What is 2+2?"}
)

if result.success:
    print(f"Output: {result.outputs}")
    print(f"Latency: {result.metrics['latency_seconds']}s")
```

### 3. Receipt Generator (`receipts.py`)

Captures invocation metadata and stores as RDF.

**Features:**
- Comprehensive metadata capture
- RDF node generation
- Provenance linking
- Graph import/export

**Example:**
```python
from kgcl.dspy_runtime import ReceiptGenerator

generator = ReceiptGenerator()

# Generate receipt
receipt = generator.generate_receipt(
    signature_name="MySignature",
    module_path="/path/to/signature.py",
    inputs={"question": "test"},
    outputs={"answer": "result"},
    success=True,
    model="llama3.1",
    latency_seconds=1.5,
    source_features=["http://example.com/feature1"]
)

# Store in RDF graph
receipt_uri = generator.store_receipt(receipt)

# Export graph
generator.export_graph("receipts.ttl", format="turtle")
```

### 4. UNRDF Bridge (`unrdf_bridge.py`)

External capability interface for UNRDF integration.

**Features:**
- Unified invocation interface
- Batch processing
- Receipt management
- Statistics tracking

**Example:**
```python
from kgcl.dspy_runtime import UNRDFBridge

bridge = UNRDFBridge()
bridge.initialize()

# Invoke signature with provenance
result = bridge.invoke(
    module_path="/path/to/signature.py",
    signature_name="MySignature",
    inputs={"question": "What is the capital of France?"},
    source_features=["http://example.com/feature/geo"],
    source_signatures=["http://example.com/sig/qa"]
)

# Access result and receipt
print(f"Success: {result['result']['success']}")
print(f"Receipt ID: {result['receipt']['receipt_id']}")
print(f"Receipt URI: {result['receipt_uri']}")

# Get statistics
stats = bridge.get_stats()
print(f"Total invocations: {stats['total_invocations']}")
print(f"Success rate: {stats['success_rate']:.2%}")
```

### 5. CLI (`__main__.py`)

Command-line interface for runtime operations.

**Commands:**

```bash
# Health check
kgc-dspy health

# List available models
kgc-dspy models

# Get model info
kgc-dspy model-info llama3.1

# Invoke signature
kgc-dspy invoke /path/to/signature.py MySignature --inputs '{"question": "test"}'

# Invoke with input file
kgc-dspy invoke /path/to/signature.py MySignature --inputs-file inputs.json --output result.json

# List receipts
kgc-dspy receipts

# Filter receipts
kgc-dspy receipts --signature MySignature --success true --limit 10

# View statistics
kgc-dspy stats

# Test invocation
kgc-dspy test
```

## Installation

```bash
# Install with DSPy support
pip install -e .[dspy]

# Or install DSPy separately
pip install dspy-ai
```

## Setup

1. **Start Ollama:**
   ```bash
   ollama serve
   ```

2. **Pull a model:**
   ```bash
   ollama pull llama3.1
   ```

3. **Configure environment (optional):**
   ```bash
   export OLLAMA_MODEL=llama3.1
   export OLLAMA_BASE_URL=http://localhost:11434
   ```

4. **Verify health:**
   ```bash
   kgc-dspy health
   ```

## Observability

### OpenTelemetry Integration

The runtime is fully instrumented with OpenTelemetry:

**Spans:**
- `dspy.predict` - Individual predictions
- `dspy.invoke_from_module` - Module loading and invocation
- `unrdf.bridge.invoke` - Bridge invocations
- `unrdf.bridge.batch_invoke` - Batch operations

**Metrics:**
- `dspy.predictions.total` - Total predictions counter
- `dspy.predictions.latency` - Prediction latency histogram
- `dspy.predictions.errors` - Error counter by type

**Attributes:**
- `signature` - Signature name
- `input_count` - Number of inputs
- `output_count` - Number of outputs
- `latency_seconds` - Execution time
- `success` - Success/failure status
- `error_type` - Error type if failed

### Viewing Traces

When integrated with OpenTelemetry collector:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Setup console exporter for debugging
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

# All DSPy runtime operations will now emit spans
```

## Error Handling

The runtime implements comprehensive error handling:

### Graceful Degradation

```python
from kgcl.dspy_runtime import OllamaLM, DSPY_AVAILABLE

if not DSPY_AVAILABLE:
    print("DSPy not installed, using fallback")
else:
    lm = OllamaLM()
    if not lm.is_available():
        print("Ollama not available, check service")
```

### Error Receipts

Failed invocations still generate receipts:

```python
result = bridge.invoke(...)

if not result['result']['success']:
    error_msg = result['result']['error']
    receipt = result['receipt']

    print(f"Invocation failed: {error_msg}")
    print(f"Error receipt: {receipt['receipt_id']}")
```

## Testing

```bash
# Run all tests
PYTHONPATH=src pytest tests/dspy_runtime/ -v

# Run unit tests only
PYTHONPATH=src pytest tests/dspy_runtime/ -v -m "not integration"

# Run integration tests (requires Ollama)
PYTHONPATH=src pytest tests/dspy_runtime/ -v -m integration

# Run with coverage
PYTHONPATH=src pytest tests/dspy_runtime/ --cov=kgcl.dspy_runtime --cov-report=html
```

## Performance

### Benchmarks

Typical performance on modern hardware:

- **Signature loading**: <50ms (with caching: <1ms)
- **Input validation**: <1ms
- **Receipt generation**: 2-5ms
- **RDF storage**: 5-10ms per receipt
- **Prediction latency**: Depends on model and Ollama server

### Optimization Tips

1. **Enable signature caching:**
   ```python
   # Signatures are cached by default
   invoker = SignatureInvoker()
   sig = invoker.load_signature(path, name)  # First load: 50ms
   sig = invoker.load_signature(path, name)  # Cached: <1ms
   ```

2. **Batch operations:**
   ```python
   # More efficient than individual invokes
   results = bridge.batch_invoke(invocations)
   ```

3. **Reuse bridge instance:**
   ```python
   # Initialize once, use many times
   bridge = UNRDFBridge()
   bridge.initialize()

   for inputs in input_list:
       bridge.invoke(...)
   ```

## Integration with UNRDF

The runtime is designed as an external capability for UNRDF:

```python
from kgcl.unrdf_engine import UNRDFEngine
from kgcl.dspy_runtime import UNRDFBridge

# Initialize engine
engine = UNRDFEngine()

# Register DSPy capability
dspy_bridge = UNRDFBridge()
engine.register_capability("dspy_invoke", dspy_bridge.invoke)

# Use in workflows
result = engine.invoke_capability(
    "dspy_invoke",
    module_path="/path/to/signature.py",
    signature_name="FeatureExtractor",
    inputs={"text": "..."},
    source_features=["http://example.com/feature/1"]
)
```

## Best Practices

1. **Always check health before operations:**
   ```python
   health = health_check()
   assert health["status"] == "healthy"
   ```

2. **Use environment variables for configuration:**
   ```bash
   # Production
   export OLLAMA_MODEL=llama3.1
   export OLLAMA_TEMPERATURE=0.3  # Lower for more deterministic

   # Development
   export OLLAMA_MODEL=llama2
   export OLLAMA_TEMPERATURE=0.7
   ```

3. **Export receipts for persistence:**
   ```python
   bridge.export_receipts("receipts.ttl")
   ```

4. **Monitor statistics:**
   ```python
   stats = bridge.get_stats()
   if stats["success_rate"] < 0.8:
       print("Warning: High failure rate!")
   ```

5. **Handle DSPy unavailability:**
   ```python
   from kgcl.dspy_runtime import DSPY_AVAILABLE

   if not DSPY_AVAILABLE:
       raise RuntimeError("Install DSPy: pip install dspy-ai")
   ```

## Troubleshooting

### Ollama Connection Issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check logs
journalctl -u ollama -f
```

### Model Not Available

```bash
# Pull model
ollama pull llama3.1

# List available models
ollama list
```

### DSPy Import Errors

```bash
# Install DSPy
pip install dspy-ai

# Verify installation
python -c "import dspy; print(dspy.__version__)"
```

### Memory Issues

```bash
# Limit Ollama memory
OLLAMA_MAX_LOADED_MODELS=1 ollama serve

# Use smaller model
export OLLAMA_MODEL=llama2
```

## License

See main project LICENSE file.
