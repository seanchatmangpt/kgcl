"""
Streaming Change Feed and Stream Processor.

Real-time change processing for knowledge graph updates with
publish-subscribe pattern and batch processing capabilities.
Ported from UNRDF streaming/stream-processor.mjs and streaming/change-feed.mjs.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from collections import deque
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class ChangeType(Enum):
  """Type of change in stream."""

  ADDED = "added"
  REMOVED = "removed"
  MODIFIED = "modified"


@dataclass
class Change:
  """Single change event in stream.

  Parameters
  ----------
  change_type : ChangeType
      Type of change operation
  triple : tuple
      RDF triple (subject, predicate, object)
  timestamp : float
      Unix timestamp of change
  source : str
      Hook/operation that caused change
  metadata : Dict[str, Any]
      Additional metadata about the change
  """

  change_type: ChangeType
  triple: tuple  # (subject, predicate, object)
  timestamp: float
  source: str
  metadata: Dict[str, Any] = field(default_factory=dict)

  def to_dict(self) -> Dict[str, Any]:
    """Convert change to dictionary."""
    return {
      "change_type": self.change_type.value,
      "triple": self.triple,
      "timestamp": self.timestamp,
      "source": self.source,
      "metadata": self.metadata,
    }


class ChangeFeed:
  """Captures changes to knowledge graph.

  Implements publish-subscribe pattern for real-time change notifications
  with buffering and historical query capabilities.
  """

  def __init__(self, max_buffer_size: int = 10000) -> None:
    """Initialize change feed.

    Parameters
    ----------
    max_buffer_size : int
        Maximum number of changes to buffer
    """
    self.changes: deque = deque(maxlen=max_buffer_size)
    self.subscribers: List[Callable[[Change], None]] = []
    self.max_buffer_size = max_buffer_size
    self._total_changes = 0

  def publish_change(self, change: Change) -> None:
    """Add change to feed and notify subscribers.

    Parameters
    ----------
    change : Change
        Change event to publish
    """
    self.changes.append(change)
    self._total_changes += 1

    # Notify all subscribers
    for subscriber in self.subscribers:
      try:
        subscriber(change)
      except Exception as e:
        logger.error(f"Subscriber error: {e}")

  def subscribe(self, callback: Callable[[Change], None]) -> None:
    """Subscribe to change feed.

    Parameters
    ----------
    callback : Callable[[Change], None]
        Function to call for each change
    """
    self.subscribers.append(callback)

  def unsubscribe(self, callback: Callable[[Change], None]) -> bool:
    """Unsubscribe from change feed.

    Parameters
    ----------
    callback : Callable[[Change], None]
        Callback to remove

    Returns
    -------
    bool
        True if callback was removed
    """
    try:
      self.subscribers.remove(callback)
      return True
    except ValueError:
      return False

  def get_changes_since(self, timestamp: float) -> List[Change]:
    """Get changes after timestamp.

    Parameters
    ----------
    timestamp : float
        Unix timestamp

    Returns
    -------
    List[Change]
        Changes that occurred after timestamp
    """
    return [c for c in self.changes if c.timestamp > timestamp]

  def get_changes_by_source(self, source: str) -> List[Change]:
    """Get changes from specific source.

    Parameters
    ----------
    source : str
        Source identifier

    Returns
    -------
    List[Change]
        Changes from specified source
    """
    return [c for c in self.changes if c.source == source]

  def get_changes_by_type(self, change_type: ChangeType) -> List[Change]:
    """Get changes of specific type.

    Parameters
    ----------
    change_type : ChangeType
        Type of changes to retrieve

    Returns
    -------
    List[Change]
        Changes of specified type
    """
    return [c for c in self.changes if c.change_type == change_type]

  def get_recent_changes(self, count: int = 100) -> List[Change]:
    """Get most recent changes.

    Parameters
    ----------
    count : int
        Number of recent changes to retrieve

    Returns
    -------
    List[Change]
        Most recent changes
    """
    return list(self.changes)[-count:]

  def clear(self) -> None:
    """Clear all buffered changes."""
    self.changes.clear()

  def get_stats(self) -> Dict[str, Any]:
    """Get feed statistics.

    Returns
    -------
    Dict[str, Any]
        Statistics about the change feed
    """
    return {
      "buffer_size": len(self.changes),
      "max_buffer_size": self.max_buffer_size,
      "total_changes": self._total_changes,
      "subscriber_count": len(self.subscribers),
      "oldest_timestamp": self.changes[0].timestamp if self.changes else None,
      "newest_timestamp": self.changes[-1].timestamp if self.changes else None,
    }


class StreamProcessor:
  """Process streaming changes in real-time.

  Supports multiple named processors that can transform, filter,
  or react to changes in the knowledge graph.
  """

  def __init__(self) -> None:
    """Initialize stream processor."""
    self.feed = ChangeFeed()
    self.processors: Dict[str, Callable[[Change], Optional[Any]]] = {}
    self._processor_stats: Dict[str, Dict[str, int]] = {}

  def register_processor(
    self, name: str, processor: Callable[[Change], Optional[Any]]
  ) -> None:
    """Register change processor.

    Parameters
    ----------
    name : str
        Processor name
    processor : Callable[[Change], Optional[Any]]
        Function that processes a change
    """
    self.processors[name] = processor
    self._processor_stats[name] = {"processed": 0, "errors": 0}

  def unregister_processor(self, name: str) -> bool:
    """Unregister change processor.

    Parameters
    ----------
    name : str
        Processor name

    Returns
    -------
    bool
        True if processor was removed
    """
    if name in self.processors:
      del self.processors[name]
      del self._processor_stats[name]
      return True
    return False

  def process_change(self, change: Change) -> Dict[str, Any]:
    """Process single change through all processors.

    Parameters
    ----------
    change : Change
        Change to process

    Returns
    -------
    Dict[str, Any]
        Results from each processor
    """
    results: Dict[str, Any] = {}

    # Publish to feed
    self.feed.publish_change(change)

    # Process through each registered processor
    for name, processor in self.processors.items():
      try:
        result = processor(change)
        results[name] = result
        self._processor_stats[name]["processed"] += 1
      except Exception as e:
        logger.error(f"Processor {name} failed: {e}")
        results[name] = {"error": str(e)}
        self._processor_stats[name]["errors"] += 1

    return results

  def process_batch(self, changes: List[Change]) -> List[Dict[str, Any]]:
    """Process batch of changes.

    Parameters
    ----------
    changes : List[Change]
        Batch of changes to process

    Returns
    -------
    List[Dict[str, Any]]
        Results for each change
    """
    return [self.process_change(change) for change in changes]

  def get_processor_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
    """Get processor statistics.

    Parameters
    ----------
    name : Optional[str]
        Processor name (None for all processors)

    Returns
    -------
    Dict[str, Any]
        Statistics for processor(s)
    """
    if name:
      return self._processor_stats.get(name, {})
    return self._processor_stats.copy()

  def create_filter_processor(
    self,
    name: str,
    predicate: Callable[[Change], bool],
    action: Callable[[Change], None],
  ) -> None:
    """Create processor that filters and acts on changes.

    Parameters
    ----------
    name : str
        Processor name
    predicate : Callable[[Change], bool]
        Filter predicate
    action : Callable[[Change], None]
        Action to perform on matching changes
    """

    def processor(change: Change) -> Optional[bool]:
      if predicate(change):
        action(change)
        return True
      return False

    self.register_processor(name, processor)

  def create_transform_processor(
    self,
    name: str,
    transform: Callable[[Change], Change],
  ) -> None:
    """Create processor that transforms changes.

    Parameters
    ----------
    name : str
        Processor name
    transform : Callable[[Change], Change]
        Transformation function
    """

    def processor(change: Change) -> Change:
      return transform(change)

    self.register_processor(name, processor)

  def get_feed(self) -> ChangeFeed:
    """Get underlying change feed.

    Returns
    -------
    ChangeFeed
        The change feed
    """
    return self.feed


class WindowedStreamProcessor(StreamProcessor):
  """Stream processor with time-window aggregation.

  Supports tumbling windows for aggregating changes over time periods.
  """

  def __init__(self, window_size_ms: int = 1000) -> None:
    """Initialize windowed stream processor.

    Parameters
    ----------
    window_size_ms : int
        Window size in milliseconds
    """
    super().__init__()
    self.window_size_ms = window_size_ms
    self.current_window: List[Change] = []
    self.window_start: Optional[float] = None
    self.window_callbacks: List[Callable[[List[Change]], None]] = []

  def register_window_callback(
    self, callback: Callable[[List[Change]], None]
  ) -> None:
    """Register callback for completed windows.

    Parameters
    ----------
    callback : Callable[[List[Change]], None]
        Function called when window completes
    """
    self.window_callbacks.append(callback)

  def process_change(self, change: Change) -> Dict[str, Any]:
    """Process change with windowing.

    Parameters
    ----------
    change : Change
        Change to process

    Returns
    -------
    Dict[str, Any]
        Processing results
    """
    # Initialize window if needed
    if self.window_start is None:
      self.window_start = change.timestamp

    # Check if change is in current window
    window_end = self.window_start + (self.window_size_ms / 1000.0)

    if change.timestamp >= window_end:
      # Window complete, trigger callbacks
      self._complete_window()
      self.window_start = change.timestamp

    self.current_window.append(change)

    # Process through standard processors
    return super().process_change(change)

  def _complete_window(self) -> None:
    """Complete current window and trigger callbacks."""
    if not self.current_window:
      return

    for callback in self.window_callbacks:
      try:
        callback(self.current_window)
      except Exception as e:
        logger.error(f"Window callback error: {e}")

    self.current_window = []

  def flush_window(self) -> None:
    """Force completion of current window."""
    self._complete_window()
    self.window_start = None
