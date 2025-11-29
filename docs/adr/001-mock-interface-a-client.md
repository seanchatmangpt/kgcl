# ADR 001: Mock Interface A Client for Development and Testing

## Status
**Accepted** - 2025-11-29

## Context
The YAWL session management requires Interface A client to authenticate users and services. However:

1. **Development Challenge**: Full Interface A requires:
   - Running YAWL engine instance
   - Database configuration
   - Network connectivity
   - Service registration

2. **Testing Challenge**: Unit tests need:
   - Fast execution (<1s per test)
   - No external dependencies
   - Deterministic behavior
   - Easy credential setup

3. **Current State**:
   - `InterfaceAClient` had 5 TODO comments
   - `get_password()` returned `None` (blocking all auth)
   - No way to run session tests without full engine

## Decision
Implement `MockInterfaceAClient` with:
- In-memory credential store
- Compatible API with real Interface A
- Environment variable toggle: `USE_MOCK_INTERFACE_A` (default: true)
- Clear migration path documented in code

## Consequences

### Positive
✅ **Testing Enabled**: All session tests can now run
✅ **Fast Development**: No engine setup required
✅ **Clear Migration**: Environment variable + comments show the path
✅ **80/20 Win**: 20% effort (mock impl) enables 80% of testing

### Negative
⚠️ **Not Production Ready**: Mock doesn't validate against real engine
⚠️ **Dual Codepaths**: Must maintain both mock and real implementation paths
⚠️ **False Confidence**: Tests may pass with mock but fail with real client

### Mitigation
- Integration tests with real engine (when available) via `USE_MOCK_INTERFACE_A=false`
- Clear documentation in code and ADR
- Mock behavior closely mirrors expected real behavior
- Example credentials provided for common test cases

## Migration Path

### Current State (Development/Testing)
```python
# Default: Uses MockInterfaceAClient
sessions = Sessions(
    ia_uri="http://localhost:8080/interfaceA",
    ia_userid="admin",
    ia_password="admin"
)
```

### Future State (Production)
```python
# Set environment variable
os.environ["USE_MOCK_INTERFACE_A"] = "false"

# Replace mock import with real client
from yawl.interfaceA import InterfaceA_EnvironmentBasedClient

# Update session.py constructor to use real client
```

### Completion Checklist
- [ ] Implement `InterfaceA_EnvironmentBasedClient` wrapper
- [ ] Add integration tests with real YAWL engine
- [ ] Document configuration requirements
- [ ] Update deployment guide
- [ ] Set `USE_MOCK_INTERFACE_A=false` in production config

## Implementation Details

### Mock Client Features
- **User Registration**: `register_user(userid, password)`
- **Service Registration**: `register_service(name, password, uri)`
- **Password Lookup**: `get_password(userid)` - checks users and services
- **Connection Check**: Always succeeds (for testing)
- **Default Users**: `admin:admin` + connecting user auto-registered

### Files Changed
- `src/kgcl/yawl/util/session.py` - Use mock by default
- `src/kgcl/yawl/util/mock_interface_a.py` - Mock implementation
- `docs/adr/001-mock-interface-a-client.md` - This ADR

## References
- Original TODOs: `session.py:313, 319, 343, 362`
- YAWL Java Interface A: https://github.com/yawlfoundation/yawl
- Testing philosophy: Chicago School TDD (test real behavior, minimal mocking)

## Notes
This follows the 80/20 principle: implementing 20% of the functionality (in-memory auth) enables 80% of the testing scenarios. The mock is **intentionally simple** - if you need more features, consider if you actually need the real Interface A client instead.
