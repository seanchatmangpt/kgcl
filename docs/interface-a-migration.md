# Interface A Migration Guide

## Overview
The YAWL session management currently uses `MockInterfaceAClient` for development and testing. This guide explains how to migrate to a production Interface A client.

## Current State (80% Complete)

### What Works ✅
- Session creation and management
- User authentication (in-memory)
- Service authentication (in-memory)
- Background task cleanup
- Inactivity timeout handling
- All session unit tests passing

### What's Mocked 🎭
- Interface A network communication
- Credential persistence (database)
- Service registration with engine
- Real session handle generation

## Gap Analysis (20% to Production)

### Critical Gaps
1. **No Database**: Credentials stored in-memory only
2. **No Network**: No actual connection to YAWL engine
3. **No Validation**: Can't verify against real engine state
4. **No Service Discovery**: Can't query registered services

### When You Need Real Implementation
- [ ] Connecting to production YAWL engine
- [ ] Multi-user production environment
- [ ] Service coordination across network
- [ ] Persistent session management
- [ ] Integration with YAWL resource service

## Migration Steps

### Phase 1: Test with Mock (Current)
```python
import os

# Default behavior - uses mock
from kgcl.yawl.util.session import Sessions

sessions = Sessions(
    ia_uri="http://localhost:8080/interfaceA",
    ia_userid="admin",
    ia_password="admin"
)

# Register additional test users
sessions._ia_client.register_user("testuser", "testpass")
```

### Phase 2: Integration Testing
```python
# Set environment variable to disable mock
os.environ["USE_MOCK_INTERFACE_A"] = "false"

# This will fail until real client is implemented
# Provides clear migration signal
sessions = Sessions(
    ia_uri="http://real-yawl-engine:8080/interfaceA",
    ia_userid="admin",
    ia_password="admin"
)
```

### Phase 3: Implement Real Client
```python
# File: src/kgcl/yawl/util/interface_a_client.py

from yawl.engine import InterfaceA_EnvironmentBasedClient

class ProductionInterfaceAClient:
    """Production Interface A client wrapper.

    Wraps YAWL engine's InterfaceA_EnvironmentBasedClient with
    compatible API to MockInterfaceAClient.
    """

    def __init__(self, uri: str, userid: str, password: str) -> None:
        self.client = InterfaceA_EnvironmentBasedClient(uri)
        self.handle = self.client.connect(userid, password)

        if not self.client.successful(self.handle):
            raise ConnectionError(f"Failed to connect: {self.handle}")

    def get_password(self, userid: str) -> str | None:
        """Get password from engine."""
        # Check services
        services = self.client.getRegisteredYAWLServices(self.handle)
        for service in services:
            if service.getServiceName() == userid:
                return service.getServicePassword()

        # Check external clients
        password = self.client.getPassword(userid, self.handle)
        if self.client.successful(password):
            return password

        return None

    def check_connection(self, handle: str | None = None) -> str:
        """Verify connection is alive."""
        result = self.client.checkConnection(handle or self.handle)
        return result

    def connect(self, userid: str, password: str) -> str:
        """Connect with credentials."""
        return self.client.connect(userid, password)
```

### Phase 4: Update session.py
```python
# In InterfaceAClient.__init__

use_mock = os.getenv("USE_MOCK_INTERFACE_A", "true").lower() == "true"

if use_mock:
    from kgcl.yawl.util.mock_interface_a import MockInterfaceAClient
    self._ia_client = MockInterfaceAClient(uri, userid, password)
else:
    # Real implementation
    from kgcl.yawl.util.interface_a_client import ProductionInterfaceAClient
    self._ia_client = ProductionInterfaceAClient(uri, userid, password)
```

### Phase 5: Configuration Management
```yaml
# config/production.yaml
yawl:
  interface_a:
    uri: https://yawl-engine.production:8080/interfaceA
    userid: service-account
    password: ${YAWL_SERVICE_PASSWORD}  # From secrets
    use_mock: false  # Explicit in production

# config/development.yaml
yawl:
  interface_a:
    uri: http://localhost:8080/interfaceA
    userid: admin
    password: admin
    use_mock: true  # Explicit for clarity
```

## Testing Strategy

### Unit Tests (Mock - Fast)
```python
# All existing tests use mock by default
def test_session_creation():
    sessions = Sessions("http://localhost/ia", "admin", "admin")
    handle = sessions.connect("testuser", "testpass")
    assert handle is not None
```

### Integration Tests (Real - Slow)
```python
import pytest

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("USE_MOCK_INTERFACE_A", "true") == "true",
    reason="Requires real YAWL engine"
)
def test_session_with_real_engine():
    """Test against actual YAWL engine.

    Requires:
    - YAWL engine running at YAWL_ENGINE_URL
    - Valid credentials in environment
    - Network connectivity
    """
    os.environ["USE_MOCK_INTERFACE_A"] = "false"

    sessions = Sessions(
        ia_uri=os.environ["YAWL_ENGINE_URL"],
        ia_userid=os.environ["YAWL_USER"],
        ia_password=os.environ["YAWL_PASS"]
    )

    # Test real authentication
    handle = sessions.connect(
        os.environ["TEST_USER"],
        os.environ["TEST_PASS"]
    )
    assert handle is not None
    assert not handle.startswith("mock-")  # Real handle
```

## Completion Checklist

### Phase 1: Foundation (Complete ✅)
- [x] Mock client implemented
- [x] Session tests passing
- [x] ADR documented
- [x] Migration guide written

### Phase 2: Real Client (To Do 📋)
- [ ] Obtain YAWL engine Java client library
- [ ] Create Python wrapper for InterfaceA
- [ ] Implement ProductionInterfaceAClient
- [ ] Update session.py imports

### Phase 3: Integration (To Do 📋)
- [ ] Set up test YAWL engine
- [ ] Create integration test suite
- [ ] Document configuration
- [ ] Add deployment guide

### Phase 4: Production (To Do 📋)
- [ ] Security review
- [ ] Performance testing
- [ ] Connection pooling
- [ ] Error handling & retry logic
- [ ] Monitoring & logging

## Troubleshooting

### "No module named 'yawl.engine'"
- **Cause**: YAWL Java client not installed
- **Solution**: Install YAWL engine client library or use mock

### "Connection refused"
- **Cause**: YAWL engine not running or wrong URL
- **Solution**: Check engine is running, verify `ia_uri`

### Tests fail with "Invalid credentials"
- **Cause**: Using mock but credentials not registered
- **Solution**: Use `sessions._ia_client.register_user()` in tests

### Mock works but real client fails
- **Cause**: Expected behavior - mock is simplified
- **Solution**: This is normal during migration, implement real client

## References
- ADR 001: Mock Interface A Client Decision
- YAWL Engine Documentation: https://yawlfoundation.github.io/yawl/
- Interface A Specification: https://yawlfoundation.github.io/yawl/manual/
