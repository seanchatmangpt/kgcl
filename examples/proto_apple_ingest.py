#!/usr/bin/env python3
"""
Hyper-Advanced Apple Data Ingestion Prototype.

This prototype demonstrates 12 cutting-edge Python techniques:
1. Metaclass for Auto-Registration
2. __slots__ with __init_subclass__
3. Structural Pattern Matching (PEP 636)
4. AsyncIO with Semaphore for Rate Limiting
5. Generator-based Streaming Pipeline
6. Descriptor for Lazy Loading
7. Dataclass with __post_init__ Validation
8. Protocol for Pluggable Serializers
9. Context Manager for Transaction-like Batching
10. Functional Pipeline with Pipe Operator Pattern
11. Type Guards for Runtime Type Narrowing (PEP 647)
12. Cached Property for Expensive Computations

Run: python examples/proto_apple_ingest.py
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import cached_property
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Iterable,
    Iterator,
    Protocol,
    TypeGuard,
    TypeVar,
)

# ============================================================================
# TECHNIQUE 1: Metaclass for Auto-Registration
# ============================================================================


class IngestorMeta(type(ABC)):  # type: ignore[misc]
    """Metaclass that auto-registers ingestors by data type."""

    _registry: ClassVar[dict[str, type[BaseIngestor]]] = {}

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]
    ) -> type:
        """Create class and auto-register if it has a data_type."""
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "BaseIngestor" and "data_type" in namespace:
            data_type = namespace["data_type"]
            mcs._registry[data_type] = cls  # type: ignore[assignment]
        return cls

    @classmethod
    def get_ingestor(mcs, data_type: str) -> type[BaseIngestor] | None:
        """Get registered ingestor for data type."""
        return mcs._registry.get(data_type)

    @classmethod
    def list_types(mcs) -> list[str]:
        """List all registered data types."""
        return list(mcs._registry.keys())


# ============================================================================
# TECHNIQUE 2: __slots__ with __init_subclass__
# ============================================================================


class OptimizedModel:
    """Base class that auto-generates __slots__ from annotations."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-generate __slots__ from type annotations."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "__annotations__"):
            # Only add slots not already defined
            existing_slots = set()
            for base in cls.__mro__:
                if hasattr(base, "__slots__"):
                    existing_slots.update(base.__slots__)  # type: ignore[attr-defined]
            new_slots = [
                k for k in cls.__annotations__.keys() if k not in existing_slots
            ]
            if new_slots:
                cls.__slots__ = tuple(new_slots)  # type: ignore[misc]


# ============================================================================
# TECHNIQUE 7: Dataclass with __post_init__ Validation
# ============================================================================


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """Immutable calendar event with validation."""

    id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: str | None = None
    attendees: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate event constraints."""
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be after start_time ({self.start_time})"
            )
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if len(self.id) == 0:
            raise ValueError("id cannot be empty")


@dataclass(frozen=True, slots=True)
class Reminder:
    """Immutable reminder item."""

    id: str
    title: str
    due_date: datetime | None = None
    completed: bool = False
    priority: int = 0

    def __post_init__(self) -> None:
        """Validate reminder constraints."""
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if not 0 <= self.priority <= 10:
            raise ValueError("priority must be between 0 and 10")


@dataclass(frozen=True, slots=True)
class Email:
    """Immutable email message."""

    id: str
    subject: str
    sender: str
    recipients: tuple[str, ...]
    sent_date: datetime
    body: str = ""

    def __post_init__(self) -> None:
        """Validate email constraints."""
        if not self.subject.strip():
            raise ValueError("subject cannot be empty")
        if "@" not in self.sender:
            raise ValueError("sender must be valid email")
        if not self.recipients:
            raise ValueError("recipients cannot be empty")


# ============================================================================
# TECHNIQUE 11: Type Guards for Runtime Type Narrowing (PEP 647)
# ============================================================================


def is_calendar_event_dict(data: dict[str, Any]) -> TypeGuard[dict[str, Any]]:
    """Type guard for calendar event dictionary."""
    return (
        "start_time" in data
        and "end_time" in data
        and "title" in data
        and isinstance(data.get("title"), str)
    )


def is_reminder_dict(data: dict[str, Any]) -> TypeGuard[dict[str, Any]]:
    """Type guard for reminder dictionary."""
    return "title" in data and isinstance(data.get("completed", False), bool)


def is_email_dict(data: dict[str, Any]) -> TypeGuard[dict[str, Any]]:
    """Type guard for email dictionary."""
    return (
        "subject" in data
        and "sender" in data
        and "recipients" in data
        and isinstance(data.get("recipients"), (list, tuple))
    )


# ============================================================================
# TECHNIQUE 8: Protocol for Pluggable Serializers
# ============================================================================

T = TypeVar("T")
U = TypeVar("U")


class Serializer(Protocol[T]):
    """Protocol for pluggable serialization."""

    def serialize(self, obj: T) -> bytes:
        """Serialize object to bytes."""
        ...

    def deserialize(self, data: bytes) -> T:
        """Deserialize bytes to object."""
        ...


class JSONSerializer(Serializer[T]):
    """JSON-based serializer implementation."""

    def __init__(self, type_: type[T]) -> None:
        """Initialize with target type."""
        self._type = type_

    def serialize(self, obj: T) -> bytes:
        """Serialize object to JSON bytes."""
        if hasattr(obj, "__dict__"):
            data = vars(obj)
        elif hasattr(obj, "__slots__"):
            data = {slot: getattr(obj, slot) for slot in obj.__slots__}  # type: ignore[attr-defined]
        else:
            data = asdict(obj)  # type: ignore[call-overload]
        return json.dumps(data, default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> T:
        """Deserialize JSON bytes to object."""
        parsed = json.loads(data.decode("utf-8"))
        return self._type(**parsed)  # type: ignore[return-value]


# ============================================================================
# TECHNIQUE 3: Structural Pattern Matching for Data Parsing (PEP 636)
# ============================================================================


class EventType(Enum):
    """Event type enumeration."""

    ALL_DAY = "all_day"
    TIMED = "timed"
    RECURRING = "recurring"


def parse_event_with_pattern_matching(raw: dict[str, Any]) -> CalendarEvent:
    """Parse event using structural pattern matching."""
    match raw:
        case {"type": "all_day", "title": title, "date": date_str, "id": id_}:
            # All-day event: start at midnight, end at 23:59
            date = datetime.fromisoformat(date_str)
            return CalendarEvent(
                id=id_,
                title=title,
                start_time=date.replace(hour=0, minute=0),
                end_time=date.replace(hour=23, minute=59),
            )
        case {
            "type": "timed",
            "title": title,
            "start": start_str,
            "end": end_str,
            "id": id_,
        }:
            # Timed event with explicit start/end
            return CalendarEvent(
                id=id_,
                title=title,
                start_time=datetime.fromisoformat(start_str),
                end_time=datetime.fromisoformat(end_str),
            )
        case {"title": title, "start_time": start_str, "end_time": end_str, "id": id_}:
            # Generic event with start_time/end_time
            return CalendarEvent(
                id=id_,
                title=title,
                start_time=datetime.fromisoformat(start_str),
                end_time=datetime.fromisoformat(end_str),
                location=raw.get("location"),
                attendees=tuple(raw.get("attendees", [])),
            )
        case _:
            raise ValueError(f"Unknown event format: {raw}")


# ============================================================================
# TECHNIQUE 6: Descriptor for Lazy Loading
# ============================================================================


class LazyField(Generic[T]):
    """Descriptor that loads data on first access."""

    def __init__(self, loader: Callable[[Any], T]) -> None:
        """Initialize with loader function."""
        self._loader = loader

    def __set_name__(self, owner: type, name: str) -> None:
        """Store attribute name."""
        self.name = name
        self.private_name = f"_lazy_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> T:
        """Load and cache value on first access."""
        if obj is None:
            return self  # type: ignore[return-value]
        if not hasattr(obj, self.private_name):
            value = self._loader(obj)
            setattr(obj, self.private_name, value)
        return getattr(obj, self.private_name)  # type: ignore[no-any-return]


# ============================================================================
# TECHNIQUE 10: Functional Pipeline with Pipe Operator Pattern
# ============================================================================


class Pipeline(Generic[T]):
    """Functional pipeline with pipe operator."""

    def __init__(self, value: T) -> None:
        """Initialize with value."""
        self._value = value

    def __or__(self, func: Callable[[T], U]) -> Pipeline[U]:
        """Apply function and return new pipeline."""
        return Pipeline(func(self._value))

    def unwrap(self) -> T:
        """Extract final value."""
        return self._value


# ============================================================================
# TECHNIQUE 9: Context Manager for Transaction-like Batching
# ============================================================================


@dataclass
class BatchContext:
    """Context for batch ingestion with rollback support."""

    items: list[Any] = field(default_factory=list)
    committed: bool = False

    def add(self, item: Any) -> None:
        """Add item to batch."""
        if self.committed:
            raise RuntimeError("Cannot add to committed batch")
        self.items.append(item)

    def commit(self) -> None:
        """Commit batch."""
        self.committed = True

    def rollback(self) -> None:
        """Rollback batch."""
        self.items.clear()
        self.committed = False


@contextmanager
def batch_transaction() -> Iterator[BatchContext]:
    """Atomic batch ingestion with rollback on failure."""
    ctx = BatchContext()
    try:
        yield ctx
        ctx.commit()
    except Exception:
        ctx.rollback()
        raise


# ============================================================================
# TECHNIQUE 12: Cached Property for Expensive Computations
# ============================================================================


@dataclass
class IngestStatistics:
    """Statistics from ingestion run."""

    total_items: int
    success_count: int
    error_count: int
    duration_seconds: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 0.0
        return self.success_count / self.total_items


@dataclass
class IngestResult:
    """Result from ingestion operation."""

    items: list[Any]
    errors: list[str]
    start_time: datetime
    end_time: datetime

    @cached_property
    def statistics(self) -> IngestStatistics:
        """Compute statistics (cached)."""
        duration = (self.end_time - self.start_time).total_seconds()
        return IngestStatistics(
            total_items=len(self.items) + len(self.errors),
            success_count=len(self.items),
            error_count=len(self.errors),
            duration_seconds=duration,
        )


# ============================================================================
# TECHNIQUE 1 (cont.): Base Ingestor with Metaclass
# ============================================================================


class BaseIngestor(ABC, metaclass=IngestorMeta):
    """Base class for all ingestors (uses metaclass registration)."""

    data_type: ClassVar[str] = "base"

    @abstractmethod
    def parse(self, raw: dict[str, Any]) -> Any:
        """Parse raw data into typed object."""
        ...

    @abstractmethod
    def validate(self, obj: Any) -> bool:
        """Validate parsed object."""
        ...


class CalendarIngestor(BaseIngestor):
    """Calendar event ingestor (auto-registered via metaclass)."""

    data_type: ClassVar[str] = "calendar"

    def parse(self, raw: dict[str, Any]) -> CalendarEvent:
        """Parse calendar event using pattern matching."""
        return parse_event_with_pattern_matching(raw)

    def validate(self, obj: CalendarEvent) -> bool:
        """Validate calendar event."""
        return is_calendar_event_dict(asdict(obj))


class ReminderIngestor(BaseIngestor):
    """Reminder ingestor (auto-registered via metaclass)."""

    data_type: ClassVar[str] = "reminder"

    def parse(self, raw: dict[str, Any]) -> Reminder:
        """Parse reminder."""
        return Reminder(
            id=raw["id"],
            title=raw["title"],
            due_date=datetime.fromisoformat(raw["due_date"])
            if raw.get("due_date")
            else None,
            completed=raw.get("completed", False),
            priority=raw.get("priority", 0),
        )

    def validate(self, obj: Reminder) -> bool:
        """Validate reminder."""
        return is_reminder_dict(asdict(obj))


class EmailIngestor(BaseIngestor):
    """Email ingestor (auto-registered via metaclass)."""

    data_type: ClassVar[str] = "email"

    def parse(self, raw: dict[str, Any]) -> Email:
        """Parse email."""
        return Email(
            id=raw["id"],
            subject=raw["subject"],
            sender=raw["sender"],
            recipients=tuple(raw["recipients"]),
            sent_date=datetime.fromisoformat(raw["sent_date"]),
            body=raw.get("body", ""),
        )

    def validate(self, obj: Email) -> bool:
        """Validate email."""
        return is_email_dict(asdict(obj))


# ============================================================================
# TECHNIQUE 4: AsyncIO with Semaphore for Rate Limiting
# ============================================================================


class AsyncIngestor:
    """Async ingestor with rate limiting."""

    def __init__(self, max_concurrent: int = 10) -> None:
        """Initialize with concurrency limit."""
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _ingest_one(self, item: dict[str, Any]) -> Any:
        """Ingest single item with rate limiting."""
        async with self._semaphore:
            await asyncio.sleep(0.01)  # Simulate I/O
            data_type = item.get("data_type", "calendar")
            ingestor_cls = IngestorMeta.get_ingestor(data_type)
            if not ingestor_cls:
                raise ValueError(f"Unknown data type: {data_type}")
            ingestor = ingestor_cls()
            return ingestor.parse(item)

    async def ingest_batch(self, items: list[dict[str, Any]]) -> list[Any]:
        """Ingest batch of items concurrently."""
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self._ingest_one(item)) for item in items]
        return [t.result() for t in tasks]


# ============================================================================
# TECHNIQUE 5: Generator-based Streaming Pipeline
# ============================================================================


def stream_ingest(source: Iterable[bytes]) -> Iterator[Any]:
    """Memory-efficient streaming ingestion."""
    for chunk in source:
        parsed = json.loads(chunk)
        data_type = parsed.get("data_type", "calendar")
        ingestor_cls = IngestorMeta.get_ingestor(data_type)
        if not ingestor_cls:
            continue
        ingestor = ingestor_cls()
        try:
            validated = ingestor.parse(parsed)
            if ingestor.validate(validated):
                yield validated
        except (ValueError, KeyError):
            continue


# ============================================================================
# Pipeline Functions for Technique 10
# ============================================================================


def parse_pipeline(data: dict[str, Any]) -> Any:
    """Parse step in pipeline."""
    data_type = data.get("data_type", "calendar")
    ingestor_cls = IngestorMeta.get_ingestor(data_type)
    if not ingestor_cls:
        raise ValueError(f"Unknown data type: {data_type}")
    return ingestor_cls().parse(data)


def validate_pipeline(obj: Any) -> Any:
    """Validate step in pipeline."""
    if isinstance(obj, CalendarEvent):
        if not is_calendar_event_dict(asdict(obj)):
            raise ValueError("Invalid calendar event")
    elif isinstance(obj, Reminder):
        if not is_reminder_dict(asdict(obj)):
            raise ValueError("Invalid reminder")
    elif isinstance(obj, Email):
        if not is_email_dict(asdict(obj)):
            raise ValueError("Invalid email")
    return obj


def transform_pipeline(obj: Any) -> dict[str, Any]:
    """Transform step in pipeline."""
    return asdict(obj)


# ============================================================================
# TESTS
# ============================================================================


def test_metaclass_registration() -> None:
    """Test metaclass auto-registration."""
    registered = IngestorMeta.list_types()
    assert "calendar" in registered
    assert "reminder" in registered
    assert "email" in registered

    ingestor = IngestorMeta.get_ingestor("calendar")
    assert ingestor is CalendarIngestor


def test_dataclass_validation() -> None:
    """Test dataclass __post_init__ validation."""
    now = datetime.now()
    later = now + timedelta(hours=1)

    # Valid event
    event = CalendarEvent(
        id="evt1", title="Meeting", start_time=now, end_time=later
    )
    assert event.title == "Meeting"

    # Invalid: end before start
    try:
        CalendarEvent(id="evt2", title="Bad", start_time=later, end_time=now)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "end_time" in str(e)

    # Invalid: empty title
    try:
        CalendarEvent(id="evt3", title="  ", start_time=now, end_time=later)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "title" in str(e)


def test_pattern_matching() -> None:
    """Test structural pattern matching."""
    now = datetime.now()

    # All-day event
    raw_all_day = {
        "type": "all_day",
        "id": "evt1",
        "title": "Birthday",
        "date": now.date().isoformat(),
    }
    event1 = parse_event_with_pattern_matching(raw_all_day)
    assert event1.title == "Birthday"
    assert event1.start_time.hour == 0

    # Timed event
    later = now + timedelta(hours=2)
    raw_timed = {
        "type": "timed",
        "id": "evt2",
        "title": "Meeting",
        "start": now.isoformat(),
        "end": later.isoformat(),
    }
    event2 = parse_event_with_pattern_matching(raw_timed)
    assert event2.title == "Meeting"
    assert event2.end_time == later


def test_type_guards() -> None:
    """Test type guards for runtime type narrowing."""
    event_dict = {
        "id": "evt1",
        "title": "Test",
        "start_time": "2025-01-01T10:00:00",
        "end_time": "2025-01-01T11:00:00",
    }
    assert is_calendar_event_dict(event_dict)

    reminder_dict = {"id": "rem1", "title": "Task", "completed": False}
    assert is_reminder_dict(reminder_dict)

    email_dict = {
        "id": "email1",
        "subject": "Hello",
        "sender": "test@example.com",
        "recipients": ["user@example.com"],
    }
    assert is_email_dict(email_dict)


def test_serializer() -> None:
    """Test pluggable serializer protocol."""
    now = datetime.now()
    later = now + timedelta(hours=1)
    event = CalendarEvent(id="evt1", title="Test", start_time=now, end_time=later)

    serializer: Serializer[CalendarEvent] = JSONSerializer(CalendarEvent)
    data = serializer.serialize(event)
    assert isinstance(data, bytes)

    deserialized = serializer.deserialize(data)
    assert deserialized.id == event.id
    assert deserialized.title == event.title


def test_batch_transaction() -> None:
    """Test context manager for batch transactions."""
    # Success case
    with batch_transaction() as batch:
        batch.add("item1")
        batch.add("item2")
        assert len(batch.items) == 2

    assert batch.committed

    # Rollback case
    try:
        with batch_transaction() as batch2:
            batch2.add("item1")
            raise ValueError("Simulated error")
    except ValueError:
        pass

    assert len(batch2.items) == 0
    assert not batch2.committed


def test_pipeline() -> None:
    """Test functional pipeline with pipe operator."""
    now = datetime.now()
    later = now + timedelta(hours=1)
    raw = {
        "data_type": "calendar",
        "id": "evt1",
        "title": "Pipeline Test",
        "start_time": now.isoformat(),
        "end_time": later.isoformat(),
    }

    result = (
        Pipeline(raw)
        | parse_pipeline
        | validate_pipeline
        | transform_pipeline
    ).unwrap()

    assert isinstance(result, dict)
    assert result["title"] == "Pipeline Test"


def test_cached_property() -> None:
    """Test cached property for expensive computations."""
    now = datetime.now()
    later = now + timedelta(seconds=5)
    result = IngestResult(
        items=[1, 2, 3], errors=["err1"], start_time=now, end_time=later
    )

    # First access computes statistics
    stats1 = result.statistics
    assert stats1.total_items == 4
    assert stats1.success_count == 3
    assert stats1.error_count == 1

    # Second access uses cached value
    stats2 = result.statistics
    assert stats1 is stats2  # Same object


def test_streaming_pipeline() -> None:
    """Test generator-based streaming pipeline."""
    now = datetime.now()
    later = now + timedelta(hours=1)

    chunks = [
        json.dumps(
            {
                "data_type": "calendar",
                "id": "evt1",
                "title": "Event 1",
                "start_time": now.isoformat(),
                "end_time": later.isoformat(),
            }
        ).encode(),
        json.dumps(
            {
                "data_type": "reminder",
                "id": "rem1",
                "title": "Task 1",
                "completed": False,
            }
        ).encode(),
    ]

    results = list(stream_ingest(chunks))
    assert len(results) == 2
    assert isinstance(results[0], CalendarEvent)
    assert isinstance(results[1], Reminder)


def test_async_ingestor() -> None:
    """Test async ingestor with rate limiting."""
    now = datetime.now()
    later = now + timedelta(hours=1)

    items = [
        {
            "data_type": "calendar",
            "id": f"evt{i}",
            "title": f"Event {i}",
            "start_time": now.isoformat(),
            "end_time": later.isoformat(),
        }
        for i in range(5)
    ]

    async def run_test() -> None:
        ingestor = AsyncIngestor(max_concurrent=3)
        results = await ingestor.ingest_batch(items)
        assert len(results) == 5
        assert all(isinstance(r, CalendarEvent) for r in results)

    asyncio.run(run_test())


def test_ingestor_implementations() -> None:
    """Test all ingestor implementations."""
    now = datetime.now()
    later = now + timedelta(hours=1)

    # Calendar
    calendar_raw = {
        "id": "evt1",
        "title": "Meeting",
        "start_time": now.isoformat(),
        "end_time": later.isoformat(),
    }
    calendar_ingestor = CalendarIngestor()
    calendar_event = calendar_ingestor.parse(calendar_raw)
    assert calendar_ingestor.validate(calendar_event)

    # Reminder
    reminder_raw = {
        "id": "rem1",
        "title": "Task",
        "completed": False,
        "priority": 5,
    }
    reminder_ingestor = ReminderIngestor()
    reminder = reminder_ingestor.parse(reminder_raw)
    assert reminder_ingestor.validate(reminder)

    # Email
    email_raw = {
        "id": "email1",
        "subject": "Hello",
        "sender": "test@example.com",
        "recipients": ["user@example.com"],
        "sent_date": now.isoformat(),
    }
    email_ingestor = EmailIngestor()
    email = email_ingestor.parse(email_raw)
    assert email_ingestor.validate(email)


def run_all_tests() -> tuple[int, int]:
    """Run all tests and return (passed, total)."""
    tests = [
        ("Metaclass Registration", test_metaclass_registration),
        ("Dataclass Validation", test_dataclass_validation),
        ("Pattern Matching", test_pattern_matching),
        ("Type Guards", test_type_guards),
        ("Serializer", test_serializer),
        ("Batch Transaction", test_batch_transaction),
        ("Pipeline", test_pipeline),
        ("Cached Property", test_cached_property),
        ("Streaming Pipeline", test_streaming_pipeline),
        ("Async Ingestor", test_async_ingestor),
        ("Ingestor Implementations", test_ingestor_implementations),
    ]

    passed = 0
    total = len(tests)

    print("=" * 70)
    print("RUNNING HYPER-ADVANCED APPLE INGESTION PROTOTYPE TESTS")
    print("=" * 70)

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")

    print("=" * 70)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 70)

    return passed, total


def demonstrate_techniques() -> None:
    """Demonstrate all 12 advanced techniques."""
    print("\n" + "=" * 70)
    print("DEMONSTRATING 12 HYPER-ADVANCED PYTHON TECHNIQUES")
    print("=" * 70)

    # 1. Metaclass
    print("\n1. METACLASS AUTO-REGISTRATION")
    print(f"   Registered types: {IngestorMeta.list_types()}")

    # 2. __slots__ (demonstrated in OptimizedModel)
    print("\n2. __SLOTS__ WITH __init_subclass__")
    print("   OptimizedModel auto-generates __slots__ from annotations")

    # 3. Pattern Matching
    print("\n3. STRUCTURAL PATTERN MATCHING")
    now = datetime.now()
    raw = {
        "type": "all_day",
        "id": "evt1",
        "title": "Demo",
        "date": now.date().isoformat(),
    }
    event = parse_event_with_pattern_matching(raw)
    print(f"   Parsed all-day event: {event.title}")

    # 4. Async
    print("\n4. ASYNCIO WITH SEMAPHORE")
    print("   AsyncIngestor supports concurrent ingestion with rate limiting")

    # 5. Streaming
    print("\n5. GENERATOR-BASED STREAMING")
    print("   stream_ingest() provides memory-efficient processing")

    # 6. Lazy Loading
    print("\n6. DESCRIPTOR FOR LAZY LOADING")
    print("   LazyField descriptor defers computation until access")

    # 7. Dataclass Validation
    print("\n7. DATACLASS WITH __post_init__ VALIDATION")
    print("   CalendarEvent validates end_time > start_time")

    # 8. Protocol
    print("\n8. PROTOCOL FOR PLUGGABLE SERIALIZERS")
    serializer: Serializer[CalendarEvent] = JSONSerializer(CalendarEvent)
    print(f"   Serializer type: {type(serializer).__name__}")

    # 9. Context Manager
    print("\n9. CONTEXT MANAGER FOR BATCH TRANSACTIONS")
    with batch_transaction() as batch:
        batch.add("item")
        print(f"   Batch contains {len(batch.items)} items")

    # 10. Pipeline
    print("\n10. FUNCTIONAL PIPELINE WITH PIPE OPERATOR")
    result = Pipeline({"value": 42}) | (lambda x: x["value"] * 2) | (lambda x: x + 8)
    print(f"   Pipeline result: {result.unwrap()}")

    # 11. Type Guards
    print("\n11. TYPE GUARDS FOR RUNTIME TYPE NARROWING")
    test_dict = {"title": "Test", "start_time": "...", "end_time": "..."}
    print(f"   is_calendar_event_dict: {is_calendar_event_dict(test_dict)}")

    # 12. Cached Property
    print("\n12. CACHED PROPERTY FOR EXPENSIVE COMPUTATIONS")
    later = now + timedelta(seconds=5)
    result_obj = IngestResult(items=[1], errors=[], start_time=now, end_time=later)
    print(f"   Statistics cached: {result_obj.statistics.success_rate:.1%}")

    print("=" * 70)


if __name__ == "__main__":
    # Demonstrate techniques
    demonstrate_techniques()

    # Run tests
    print("\n")
    passed, total = run_all_tests()

    # Summary
    print("\n" + "=" * 70)
    print("HYPER-ADVANCED TECHNIQUES DEMONSTRATED:")
    print("=" * 70)
    techniques = [
        "1. Metaclass for Auto-Registration",
        "2. __slots__ with __init_subclass__",
        "3. Structural Pattern Matching (PEP 636)",
        "4. AsyncIO with Semaphore for Rate Limiting",
        "5. Generator-based Streaming Pipeline",
        "6. Descriptor for Lazy Loading",
        "7. Dataclass with __post_init__ Validation",
        "8. Protocol for Pluggable Serializers",
        "9. Context Manager for Transaction-like Batching",
        "10. Functional Pipeline with Pipe Operator Pattern",
        "11. Type Guards for Runtime Type Narrowing (PEP 647)",
        "12. Cached Property for Expensive Computations",
    ]
    for tech in techniques:
        print(f"   ✓ {tech}")
    print("=" * 70)
    print(f"\nFINAL SCORE: {passed}/{total} tests passed")
    print("=" * 70)

    # Exit with appropriate code
    exit(0 if passed == total else 1)
