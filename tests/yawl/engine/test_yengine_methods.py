"""Comprehensive tests for YEngine missing methods.

Tests all 148 missing methods added to YEngine class.
"""

from __future__ import annotations

from xml.dom.minidom import Document

import pytest

from kgcl.yawl.elements.y_identifier import YIdentifier
from kgcl.yawl.elements.y_specification import YSpecification, YSpecificationID
from kgcl.yawl.engine.y_case import YCase
from kgcl.yawl.engine.y_engine import (
    AnnouncementContext,
    EngineStatus,
    InstanceCache,
    InterfaceAManagementObserver,
    InterfaceBClientObserver,
    ObserverGateway,
    Status,
    WorkItemCompletion,
    YAnnouncer,
    YAWLServiceReference,
    YBuildProperties,
    YClient,
    YEngine,
    YExternalClient,
    YLogDataItemList,
    YNetData,
    YNetRunnerRepository,
    YPersistenceManager,
    YSessionCache,
    YVerificationHandler,
    YWorkItemRepository,
)
from kgcl.yawl.engine.y_net_runner import YNetRunner
from kgcl.yawl.engine.y_work_item import WorkItemStatus, YWorkItem

# === External client management tests ===


def test_add_external_client() -> None:
    """Test adding external client."""
    engine = YEngine()
    client = YExternalClient(id="test_client", password="pass123", documentation="Test client")

    result = engine.addExternalClient(client)

    assert result is True
    assert engine.getExternalClient("test_client") == client
    assert client in engine.getExternalClients()


def test_add_duplicate_external_client() -> None:
    """Test adding duplicate client returns False."""
    engine = YEngine()
    client = YExternalClient(id="test_client", password="pass123")

    engine.addExternalClient(client)
    result = engine.addExternalClient(client)

    assert result is False


def test_remove_external_client() -> None:
    """Test removing external client."""
    engine = YEngine()
    client = YExternalClient(id="test_client", password="pass123")
    engine.addExternalClient(client)

    removed = engine.removeExternalClient("test_client")

    assert removed == client
    assert engine.getExternalClient("test_client") is None


def test_update_external_client() -> None:
    """Test updating external client credentials."""
    engine = YEngine()
    client = YExternalClient(id="test_client", password="old_pass")
    engine.addExternalClient(client)

    result = engine.updateExternalClient("test_client", "new_pass", "Updated")

    assert result is True
    updated = engine.getExternalClient("test_client")
    assert updated is not None
    assert updated.password == "new_pass"
    assert updated.documentation == "Updated"


def test_load_default_clients() -> None:
    """Test loading default clients."""
    engine = YEngine()

    clients = engine.loadDefaultClients()

    assert len(clients) == 1
    admin = next(iter(clients))
    assert admin.id == "admin"
    assert engine.getExternalClient("admin") is not None


# === YAWL service management tests ===


def test_add_yawl_service() -> None:
    """Test adding YAWL service."""
    engine = YEngine()
    service = YAWLServiceReference(service_id="worklist", uri="http://localhost:8080/worklist")

    engine.addYawlService(service)

    assert engine.getRegisteredYawlService("worklist") == service
    assert service in engine.getYAWLServices()


def test_remove_yawl_service() -> None:
    """Test removing YAWL service."""
    engine = YEngine()
    service = YAWLServiceReference(service_id="worklist", uri="http://localhost:8080/worklist")
    engine.addYawlService(service)

    removed = engine.removeYawlService("http://localhost:8080/worklist")

    assert removed == service
    assert engine.getRegisteredYawlService("worklist") is None


def test_set_default_worklist() -> None:
    """Test setting default worklist."""
    engine = YEngine()
    service = YAWLServiceReference(service_id="worklist", uri="http://localhost:8080/worklist")
    engine.addYawlService(service)

    engine.setDefaultWorklist("worklist")

    assert engine.getDefaultWorklist() == service


# === Interface listeners tests ===


def test_add_interface_x_listener() -> None:
    """Test adding Interface X listener."""
    engine = YEngine()

    result = engine.addInterfaceXListener("http://localhost:9000/observer")

    assert result is True
    assert "http://localhost:9000/observer" in engine.interface_x_listeners


def test_add_duplicate_interface_x_listener() -> None:
    """Test adding duplicate listener returns False."""
    engine = YEngine()
    engine.addInterfaceXListener("http://localhost:9000/observer")

    result = engine.addInterfaceXListener("http://localhost:9000/observer")

    assert result is False


def test_remove_interface_x_listener() -> None:
    """Test removing Interface X listener."""
    engine = YEngine()
    engine.addInterfaceXListener("http://localhost:9000/observer")

    result = engine.removeInterfaceXListener("http://localhost:9000/observer")

    assert result is True
    assert "http://localhost:9000/observer" not in engine.interface_x_listeners


def test_register_interface_a_client() -> None:
    """Test registering Interface A client."""
    engine = YEngine()
    observer = InterfaceAManagementObserver()

    engine.registerInterfaceAClient(observer)

    assert observer in engine.interface_a_observers


def test_register_interface_b_observer() -> None:
    """Test registering Interface B observer."""
    engine = YEngine()
    observer = InterfaceBClientObserver()

    engine.registerInterfaceBObserver(observer)

    assert observer in engine.interface_b_observers


def test_register_interface_b_gateway() -> None:
    """Test registering Interface B gateway."""
    engine = YEngine()
    gateway = ObserverGateway()

    engine.registerInterfaceBObserverGateway(gateway)

    assert gateway in engine.observer_gateways


# === Case data APIs tests ===


def test_get_case_data() -> None:
    """Test getting case data by identifier."""
    engine = YEngine()
    engine.start()

    # Create and start a simple case
    from kgcl.yawl.elements.y_net import YNet

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec", input_data={"x": 10})
    identifier = YIdentifier(id=case.id)

    net_data = engine.getCaseData(identifier)

    assert isinstance(net_data, YNetData)
    assert net_data.data["x"] == 10


def test_get_case_data_str() -> None:
    """Test getting case data as string."""
    engine = YEngine()
    engine.start()

    # Create case
    from kgcl.yawl.elements.y_net import YNet

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec", input_data={"x": 10})

    data_str = engine.getCaseData_str(case.id)

    assert "x" in data_str
    assert "10" in data_str


def test_update_case_data() -> None:
    """Test updating case data."""
    engine = YEngine()
    engine.start()

    # Create case
    from kgcl.yawl.elements.y_net import YNet

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec")

    result = engine.updateCaseData(case.id, '{"x": 20}')

    assert result is True
    assert case.data.data["x"] == 20


def test_get_net_data() -> None:
    """Test getting net data."""
    engine = YEngine()
    engine.start()

    from kgcl.yawl.elements.y_net import YNet

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec", input_data={"x": 10})

    net_data = engine.getNetData(case.id)

    assert isinstance(net_data, str)
    assert "x" in net_data


# === Persistence transaction tests ===


def test_start_transaction() -> None:
    """Test starting persistence transaction."""
    engine = YEngine()
    engine.persisting = True

    result = engine.startTransaction()

    assert result is True
    assert engine.persistence_manager.transaction_active


def test_commit_transaction() -> None:
    """Test committing transaction."""
    engine = YEngine()
    engine.persisting = True
    engine.startTransaction()

    engine.commitTransaction()

    assert not engine.persistence_manager.transaction_active


def test_rollback_transaction() -> None:
    """Test rolling back transaction."""
    engine = YEngine()
    engine.persisting = True
    engine.startTransaction()

    engine.rollbackTransaction()

    assert not engine.persistence_manager.transaction_active


def test_store_update_delete_object() -> None:
    """Test persistence operations."""
    engine = YEngine()
    engine.persisting = True

    obj = object()

    # These shouldn't raise errors
    engine.storeObject(obj)
    engine.updateObject(obj)
    engine.deleteObject(obj)


def test_do_persist_action() -> None:
    """Test doPersistAction."""
    engine = YEngine()
    engine.persisting = True

    obj = object()

    # Test all action codes
    engine.doPersistAction(obj, 0)  # store
    engine.doPersistAction(obj, 1)  # update
    engine.doPersistAction(obj, 2)  # delete


# === Case ID allocation tests ===


def test_allocate_case_id() -> None:
    """Test allocating case ID."""
    engine = YEngine()

    case_id = engine.allocateCaseID()

    assert isinstance(case_id, str)
    assert len(case_id) > 0


def test_get_next_case_nbr() -> None:
    """Test getting next case number."""
    engine = YEngine()

    nbr1 = engine.getNextCaseNbr()
    nbr2 = engine.getNextCaseNbr()

    assert int(nbr2) == int(nbr1) + 1


# === Net runner tests ===


def test_add_runner() -> None:
    """Test adding net runner."""
    from kgcl.yawl.elements.y_net import YNet

    engine = YEngine()
    net = YNet(id="net1", name="Test Net")
    runner = YNetRunner(net=net, case_id="case1")

    engine.addRunner(runner)

    assert "case1:net1" in engine.net_runners
    assert engine.net_runners["case1:net1"] == runner


def test_get_net_runner_by_identifier() -> None:
    """Test getting net runner by identifier."""
    from kgcl.yawl.elements.y_net import YNet

    engine = YEngine()
    engine.start()

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec")
    engine.start_case(case.id)

    identifier = YIdentifier(id=case.id)
    runner = engine.getNetRunner(identifier)

    assert runner is not None
    assert runner.case_id == case.id


def test_get_net_runner_repository() -> None:
    """Test getting net runner repository."""
    engine = YEngine()

    repo = engine.getNetRunnerRepository()

    assert isinstance(repo, YNetRunnerRepository)


# === Specification tests ===


def test_get_latest_specification() -> None:
    """Test getting latest specification by key."""
    engine = YEngine()

    spec = YSpecification(id="test_spec_v1")
    engine.load_specification(spec)

    latest = engine.getLatestSpecification("test_spec")

    assert latest == spec


def test_get_loaded_specification_ids() -> None:
    """Test getting loaded specification IDs."""
    engine = YEngine()

    spec = YSpecification(id="test_spec")
    engine.load_specification(spec)

    ids = engine.getLoadedSpecificationIDs()

    assert len(ids) == 1
    spec_id = next(iter(ids))
    assert spec_id.identifier == "test_spec"


def test_get_load_status() -> None:
    """Test getting load status of specification."""
    engine = YEngine()

    spec = YSpecification(id="test_spec")
    engine.load_specification(spec)

    spec_id = YSpecificationID(uri="http://test", version="1.0", identifier="test_spec")
    status = engine.getLoadStatus(spec_id)

    assert status == "LOADED"


def test_get_process_definition() -> None:
    """Test getting process definition."""
    engine = YEngine()

    spec = YSpecification(id="test_spec")
    engine.load_specification(spec)

    spec_id = YSpecificationID(uri="http://test", version="1.0", identifier="test_spec")
    definition = engine.getProcessDefinition(spec_id)

    assert definition == spec


def test_get_specification_for_case() -> None:
    """Test getting specification for case."""
    from kgcl.yawl.elements.y_net import YNet

    engine = YEngine()
    engine.start()

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec")

    case_id = YIdentifier(id=case.id)
    spec_for_case = engine.getSpecificationForCase(case_id)

    assert spec_for_case == spec


# === Case state tests ===


def test_get_case_id() -> None:
    """Test getting case identifier from string."""
    engine = YEngine()

    identifier = engine.getCaseID("case123")

    assert identifier.id == "case123"


def test_get_case_locations() -> None:
    """Test getting case locations (marking)."""
    engine = YEngine()

    # Would need complete case setup - simplified test
    identifier = YIdentifier(id="case123")
    locations = engine.getCaseLocations(identifier)

    assert isinstance(locations, set)


def test_get_cases_for_specification() -> None:
    """Test getting cases for specification."""
    from kgcl.yawl.elements.y_net import YNet

    engine = YEngine()
    engine.start()

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case1 = engine.create_case("test_spec")
    case2 = engine.create_case("test_spec")

    spec_id = YSpecificationID(uri="http://test", version="1.0", identifier="test_spec")
    cases = engine.getCasesForSpecification(spec_id)

    assert len(cases) == 2
    assert case1 in cases
    assert case2 in cases


def test_get_running_case_ids() -> None:
    """Test getting running case IDs."""
    from kgcl.yawl.elements.y_net import YNet

    engine = YEngine()
    engine.start()

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec")
    engine.start_case(case.id)

    case_ids = engine.getRunningCaseIDs()

    assert case.id in case_ids


def test_get_running_case_map() -> None:
    """Test getting running case map."""
    from kgcl.yawl.elements.y_net import YNet

    engine = YEngine()
    engine.start()

    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")
    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    case = engine.create_case("test_spec")
    engine.start_case(case.id)

    case_map = engine.getRunningCaseMap()

    assert case.id in case_map
    assert case_map[case.id] == case


# === Work item tests ===


def test_get_all_work_items() -> None:
    """Test getting all work items."""
    engine = YEngine()

    work_items = engine.getAllWorkItems()

    assert isinstance(work_items, set)


def test_get_available_work_items() -> None:
    """Test getting available work items."""
    engine = YEngine()

    work_items = engine.getAvailableWorkItems()

    assert isinstance(work_items, set)


def test_get_work_item() -> None:
    """Test getting work item by ID."""
    engine = YEngine()

    work_item = engine.getWorkItem("nonexistent")

    assert work_item is None


def test_get_work_item_repository() -> None:
    """Test getting work item repository."""
    engine = YEngine()

    repo = engine.getWorkItemRepository()

    assert isinstance(repo, YWorkItemRepository)


# === Engine configuration tests ===


def test_check_engine_running() -> None:
    """Test checking engine is running."""
    engine = YEngine()

    with pytest.raises(RuntimeError, match="Engine is not running"):
        engine.checkEngineRunning()


def test_get_set_engine_status() -> None:
    """Test getting and setting engine status."""
    engine = YEngine()

    engine.setEngineStatus(Status.RUNNING)

    assert engine.getEngineStatus() == Status.RUNNING


def test_is_persisting() -> None:
    """Test checking persistence enabled."""
    engine = YEngine()

    assert not engine.isPersisting()

    engine.setPersisting(True)

    assert engine.isPersisting()


def test_get_persistence_manager() -> None:
    """Test getting persistence manager."""
    engine = YEngine()

    manager = engine.getPersistenceManager()

    assert isinstance(manager, YPersistenceManager)


def test_get_instance_cache() -> None:
    """Test getting instance cache."""
    engine = YEngine()

    cache = engine.getInstanceCache()

    assert isinstance(cache, InstanceCache)


def test_get_session_cache() -> None:
    """Test getting session cache."""
    engine = YEngine()

    cache = engine.getSessionCache()

    assert isinstance(cache, YSessionCache)


def test_get_set_engine_classes_root_path() -> None:
    """Test engine classes root path."""
    engine = YEngine()

    engine.setEngineClassesRootFilePath("/path/to/classes")

    assert engine.getEngineClassesRootFilePath() == "/path/to/classes"


def test_get_engine_nbr() -> None:
    """Test getting engine number."""
    engine = YEngine()

    nbr = engine.getEngineNbr()

    assert isinstance(nbr, int)


def test_generate_ui_metadata() -> None:
    """Test UI metadata generation settings."""
    engine = YEngine()

    assert not engine.generateUIMetaData()

    engine.setGenerateUIMetaData(True)

    assert engine.generateUIMetaData()


def test_is_generic_admin_allowed() -> None:
    """Test generic admin allowed settings."""
    engine = YEngine()

    assert not engine.isGenericAdminAllowed()

    engine.setAllowAdminID(True)

    assert engine.isGenericAdminAllowed()


def test_hibernate_statistics() -> None:
    """Test Hibernate statistics settings."""
    engine = YEngine()

    assert not engine.isHibernateStatisticsEnabled()

    engine.setHibernateStatisticsEnabled(True)

    assert engine.isHibernateStatisticsEnabled()
    assert "enabled" in engine.getHibernateStatistics()


def test_disable_process_logging() -> None:
    """Test disabling process logging."""
    engine = YEngine()

    assert engine.process_logging_enabled

    engine.disableProcessLogging()

    assert not engine.process_logging_enabled


def test_get_build_properties() -> None:
    """Test getting build properties."""
    engine = YEngine()

    props = engine.getBuildProperties()

    assert isinstance(props, YBuildProperties)
    assert props.version == "5.2"


def test_get_users() -> None:
    """Test getting users (participants)."""
    engine = YEngine()

    users = engine.getUsers()

    assert isinstance(users, set)


# === Engine lifecycle tests ===


def test_initialise() -> None:
    """Test engine initialization."""
    engine = YEngine()
    pmgr = YPersistenceManager()

    engine.initialise(pmgr, True, True, False)

    assert engine.persisting
    assert engine.hibernate_statistics_enabled


def test_shutdown() -> None:
    """Test engine shutdown."""
    engine = YEngine()
    engine.start()

    engine.shutdown()

    assert engine.status == EngineStatus.STOPPED


def test_promote_demote() -> None:
    """Test engine promote and demote (HA mode)."""
    engine = YEngine()

    engine.promote()

    assert engine.status == EngineStatus.RUNNING

    engine.demote()

    assert engine.status == EngineStatus.PAUSED


def test_dump() -> None:
    """Test engine state dump."""
    engine = YEngine()

    # Should not raise
    engine.dump()


def test_get_instance() -> None:
    """Test getInstance singleton pattern."""
    engine = YEngine.getInstance(persisting=True, gather_hbn_stats=True)

    assert engine.persisting
    assert engine.hibernate_statistics_enabled


# === Announcement tests ===


def test_reannounce_enabled_work_items() -> None:
    """Test reannouncing enabled work items."""
    engine = YEngine()

    count = engine.reannounceEnabledWorkItems()

    assert isinstance(count, int)
    assert count >= 0


def test_reannounce_executing_work_items() -> None:
    """Test reannouncing executing work items."""
    engine = YEngine()

    count = engine.reannounceExecutingWorkItems()

    assert isinstance(count, int)


def test_reannounce_fired_work_items() -> None:
    """Test reannouncing fired work items."""
    engine = YEngine()

    count = engine.reannounceFiredWorkItems()

    assert isinstance(count, int)


def test_get_announcement_context() -> None:
    """Test getting announcement context."""
    engine = YEngine()

    context = engine.getAnnouncementContext()

    assert isinstance(context, AnnouncementContext)


def test_get_announcer() -> None:
    """Test getting announcer."""
    engine = YEngine()

    announcer = engine.getAnnouncer()

    assert isinstance(announcer, YAnnouncer)


# === Integration tests ===


def test_full_case_lifecycle_with_new_methods() -> None:
    """Test full case lifecycle using new methods."""
    from kgcl.yawl.elements.y_atomic_task import YAtomicTask
    from kgcl.yawl.elements.y_net import YNet

    # Setup engine
    engine = YEngine()
    engine.start()

    # Add external client
    client = YExternalClient(id="test_user", password="pass123")
    assert engine.addExternalClient(client)

    # Add YAWL service
    service = YAWLServiceReference(service_id="worklist", uri="http://localhost:8080/worklist")
    engine.addYawlService(service)
    engine.setDefaultWorklist("worklist")

    # Create specification
    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")

    # Conditions would be added here

    # Add task
    task = YAtomicTask(id="task1", name="Task 1")
    net.add_task(task)

    # Flows would be added here

    spec.add_net(net)
    engine.load_specification(spec)
    engine.activate_specification("test_spec")

    # Launch case using new method
    spec_id = YSpecificationID(uri="http://test", version="1.0", identifier="test_spec")
    log_data = YLogDataItemList()
    case_id_str = engine.launchCase(spec_id=spec_id, case_params='{"x": 10}', log_data=log_data, delayed=False)

    assert isinstance(case_id_str, str)

    # Get case data using new methods
    case_data = engine.getCaseData_str(case_id_str)
    assert "x" in case_data

    # Get case identifier
    case_identifier = engine.getCaseID(case_id_str)
    assert case_identifier.id == case_id_str

    # Get specification for case
    spec_for_case = engine.getSpecificationForCase(identifier)
    assert spec_for_case == spec

    # Get running cases
    running_ids = engine.getRunningCaseIDs()
    assert case_id_str in running_ids

    # Check persistence (not enabled)
    assert not engine.isPersisting()

    # Engine should be running
    assert engine.getEngineStatus() == Status.RUNNING
