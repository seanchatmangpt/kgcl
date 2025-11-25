"""Complete end-to-end pipeline integration tests.

Tests the full flow: PyObjC events → UNRDF ingestion → Feature materialization
→ TTL2DSPy codegen → DSPy invocation.
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from kgcl.dspy_runtime import DSPY_AVAILABLE, UNRDFBridge
from kgcl.ingestion.config import CollectorConfig, FeatureConfig, IngestionConfig
from kgcl.ingestion.materializer import FeatureMaterializer
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock
from kgcl.ttl2dspy.generator import DSPyGenerator, SignatureDefinition
from kgcl.ttl2dspy.parser import PropertyShape, SHACLShape
from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.ingestion import IngestionPipeline

UNRDF = Namespace("http://unrdf.org/ontology/")


def create_sample_daily_events() -> tuple[list, datetime, datetime]:
    """Create 24 hours of realistic sample events.

    Returns
    -------
    tuple[list, datetime, datetime]
        (events, start_time, end_time)
    """
    start = datetime(2024, 11, 24, 9, 0, 0)  # 9 AM start
    events = []

    # Morning: Deep work session (9 AM - 12 PM)
    events.extend([
        AppEvent(
            event_id="app_morning_001",
            timestamp=start,
            app_name="com.microsoft.VSCode",
            app_display_name="VS Code",
            window_title="kgcl - test_full_pipeline.py",
            duration_seconds=3600.0,  # 1 hour
        ),
        BrowserVisit(
            event_id="browser_morning_001",
            timestamp=start + timedelta(hours=1),
            url="https://docs.python.org/3/library/unittest.html",
            domain="docs.python.org",
            title="unittest — Unit testing framework",
            browser_name="Safari",
            duration_seconds=900.0,  # 15 min
        ),
        AppEvent(
            event_id="app_morning_002",
            timestamp=start + timedelta(hours=1, minutes=15),
            app_name="com.microsoft.VSCode",
            duration_seconds=5100.0,  # 85 min
        ),
    ])

    # Lunch + breaks (12 PM - 1 PM)
    events.extend([
        AppEvent(
            event_id="app_lunch_001",
            timestamp=start + timedelta(hours=3),
            app_name="com.apple.Safari",
            window_title="News",
            duration_seconds=1800.0,  # 30 min
        ),
        CalendarBlock(
            event_id="cal_lunch_001",
            timestamp=start + timedelta(hours=3),
            end_time=start + timedelta(hours=4),
            title="Lunch Break",
            is_all_day=False,
        ),
    ])

    # Afternoon: Meetings + email (1 PM - 5 PM)
    events.extend([
        CalendarBlock(
            event_id="cal_afternoon_001",
            timestamp=start + timedelta(hours=4),
            end_time=start + timedelta(hours=5),
            title="Team Standup",
            attendees=["team@example.com"],
            organizer="manager@example.com",
            location="Zoom",
        ),
        AppEvent(
            event_id="app_afternoon_001",
            timestamp=start + timedelta(hours=5),
            app_name="com.apple.Mail",
            app_display_name="Mail",
            duration_seconds=1800.0,  # 30 min
        ),
        BrowserVisit(
            event_id="browser_afternoon_001",
            timestamp=start + timedelta(hours=5, minutes=30),
            url="https://github.com/user/kgcl/pulls",
            domain="github.com",
            title="Pull Requests · user/kgcl",
            browser_name="Safari",
            duration_seconds=600.0,  # 10 min
        ),
        CalendarBlock(
            event_id="cal_afternoon_002",
            timestamp=start + timedelta(hours=6),
            end_time=start + timedelta(hours=7),
            title="Code Review Session",
            attendees=["peer@example.com"],
        ),
        AppEvent(
            event_id="app_afternoon_002",
            timestamp=start + timedelta(hours=7),
            app_name="com.microsoft.VSCode",
            duration_seconds=3600.0,  # 1 hour
        ),
    ])

    # Evening: Context switches (5 PM - 6 PM)
    events.extend([
        AppEvent(
            event_id="app_evening_001",
            timestamp=start + timedelta(hours=8),
            app_name="com.apple.Safari",
            duration_seconds=300.0,  # 5 min
        ),
        AppEvent(
            event_id="app_evening_002",
            timestamp=start + timedelta(hours=8, minutes=5),
            app_name="com.apple.Mail",
            duration_seconds=300.0,
        ),
        AppEvent(
            event_id="app_evening_003",
            timestamp=start + timedelta(hours=8, minutes=10),
            app_name="com.slack.Slack",
            duration_seconds=600.0,  # 10 min
        ),
        BrowserVisit(
            event_id="browser_evening_001",
            timestamp=start + timedelta(hours=8, minutes=20),
            url="https://stackoverflow.com/questions/12345/pytest-fixtures",
            domain="stackoverflow.com",
            title="Pytest fixtures explained",
            browser_name="Safari",
            duration_seconds=480.0,  # 8 min
        ),
    ])

    end = start + timedelta(hours=9)
    return events, start, end


class TestFullPipeline:
    """Test complete end-to-end pipeline."""

    def test_complete_flow_with_realistic_data(self):
        """Test full pipeline with 24 hours of realistic events."""
        events, start_time, end_time = create_sample_daily_events()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Ingest events into UNRDF
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl")
            pipeline = IngestionPipeline(engine)

            # Convert events to JSON format for ingestion
            event_dicts = [
                {
                    "id": e.event_id,
                    "type": type(e).__name__,
                    "timestamp": e.timestamp.isoformat(),
                    **{k: v for k, v in e.model_dump().items()
                       if k not in ["event_id", "schema_version"]},
                }
                for e in events
            ]

            # Ingest batch
            result = pipeline.ingest_json(
                data=event_dicts, agent="test_agent", reason="Integration test"
            )

            assert result.success is True
            assert result.triples_added > 0

            # Step 2: Verify RDF structure
            assert len(engine.graph) >= len(events)

            # Query for app events
            app_query = """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?event WHERE {
                ?event unrdf:type "AppEvent" .
            }
            """
            app_results = list(engine.query(app_query))
            assert len(app_results) >= 8  # At least 8 app events

            # Step 3: Materialize features
            config = FeatureConfig(
                enabled_features=[
                    "app_usage_time",
                    "browser_domain_visits",
                    "meeting_count",
                    "context_switches",
                ]
            )
            materializer = FeatureMaterializer(config)

            features = materializer.materialize(events, start_time, end_time)

            # Verify feature computation
            assert len(features) > 0

            # Check specific features exist
            feature_ids = {f.feature_id for f in features}
            assert any("VSCode" in fid for fid in feature_ids)
            assert any("github.com" in fid for fid in feature_ids)
            assert "meeting_count" in feature_ids
            assert "context_switches" in feature_ids

            # Verify feature values are correct
            vscode_feature = next(
                (f for f in features if "VSCode" in f.feature_id), None
            )
            assert vscode_feature is not None
            assert vscode_feature.value > 7200  # More than 2 hours

            meeting_feature = next(
                (f for f in features if f.feature_id == "meeting_count"), None
            )
            assert meeting_feature is not None
            assert meeting_feature.value == 3  # 3 meetings

    def test_pipeline_with_feature_templates(self):
        """Test pipeline with feature template materialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl")
            pipeline = IngestionPipeline(engine)

            # Add a feature template to the graph
            txn = engine.transaction(agent="test", reason="Add template")
            template_uri = UNRDF["AppUsageTemplate"]
            engine.add_triple(template_uri, RDF.type, UNRDF.FeatureTemplate, txn)
            engine.add_triple(
                template_uri, UNRDF.property, UNRDF.appUsageTime, txn
            )
            engine.add_triple(
                template_uri,
                UNRDF.targetPattern,
                Literal("?s unrdf:type 'AppEvent'"),
                txn,
            )
            engine.commit(txn)

            # Ingest events
            events, start_time, end_time = create_sample_daily_events()
            app_events = [e for e in events if isinstance(e, AppEvent)]
            event_dicts = [
                {
                    "id": e.event_id,
                    "type": "AppEvent",
                    "timestamp": e.timestamp.isoformat(),
                    "app_name": e.app_name,
                    "duration_seconds": e.duration_seconds,
                }
                for e in app_events
            ]

            result = pipeline.ingest_json(data=event_dicts, agent="test")
            assert result.success is True

            # Materialize from template
            materialize_result = pipeline.materialize_features(
                template_uri=template_uri,
                target_pattern="?target unrdf:type 'AppEvent'",
                agent="test",
            )

            # In this simplified test, materialization completes
            assert materialize_result.success is True

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    @patch("requests.get")
    def test_pipeline_with_dspy_integration(
        self, mock_get, mock_ollama, mock_predict
    ):
        """Test complete pipeline including DSPy signature generation and invocation."""
        # Mock Ollama availability
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
        mock_get.return_value = mock_response

        # Mock LM and prediction
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        mock_prediction = Mock()
        mock_prediction.summary = "Daily productivity summary: 3 hours coding, 2 meetings"
        mock_prediction.key_insights = "Deep work in morning, context switches in evening"

        mock_predictor = Mock()
        mock_predictor.return_value = mock_prediction
        mock_predict.return_value = mock_predictor

        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Create SHACL shape for DailyBrief signature
            shape = SHACLShape(
                uri=URIRef("http://test.org/DailyBriefShape"),
                signature_name="DailyBriefSignature",
                description="Generate daily productivity brief",
            )
            shape.input_properties = [
                PropertyShape(
                    name="app_usage",
                    description="Application usage statistics",
                    datatype=XSD.string,
                    is_required=True,
                ),
                PropertyShape(
                    name="meeting_count",
                    description="Number of meetings",
                    datatype=XSD.integer,
                    is_required=True,
                ),
            ]
            shape.output_properties = [
                PropertyShape(
                    name="summary",
                    description="Brief summary of the day",
                    datatype=XSD.string,
                    is_required=True,
                ),
                PropertyShape(
                    name="key_insights",
                    description="Key insights from the day",
                    datatype=XSD.string,
                    is_required=True,
                ),
            ]

            # Step 2: Generate DSPy signature code
            generator = DSPyGenerator()
            signature_def = generator.generate_signature(shape)
            module_code = generator.generate_module([shape])

            # Write signature module
            sig_file = Path(tmpdir) / "daily_brief_sig.py"
            sig_file.write_text(module_code)

            # Step 3: Ingest and materialize features
            events, start_time, end_time = create_sample_daily_events()
            config = FeatureConfig(
                enabled_features=["app_usage_time", "meeting_count"]
            )
            materializer = FeatureMaterializer(config)
            features = materializer.materialize(events, start_time, end_time)

            # Step 4: Invoke DSPy signature via UNRDF bridge
            bridge = UNRDFBridge()

            # Prepare inputs from materialized features
            meeting_feature = next(
                (f for f in features if f.feature_id == "meeting_count"), None
            )
            app_usage = "VSCode: 3h, Mail: 0.5h, Safari: 1h"

            result = bridge.invoke(
                module_path=str(sig_file),
                signature_name="DailyBriefSignature",
                inputs={
                    "app_usage": app_usage,
                    "meeting_count": int(meeting_feature.value)
                    if meeting_feature
                    else 0,
                },
                source_features=[f.feature_id for f in features],
            )

            # Step 5: Verify complete flow
            assert result["result"]["success"] is True
            assert "receipt" in result
            assert result["receipt"]["success"] is True
            assert result["result"]["outputs"]["summary"] is not None

    def test_pipeline_validates_rdf_structure(self):
        """Test that pipeline produces correct RDF structure at each stage."""
        events, start_time, end_time = create_sample_daily_events()

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl")
            pipeline = IngestionPipeline(engine)

            # Ingest one event
            event = events[0]
            event_dict = {
                "id": event.event_id,
                "type": "AppEvent",
                "timestamp": event.timestamp.isoformat(),
                "app_name": event.app_name,
                "duration_seconds": event.duration_seconds,
            }

            result = pipeline.ingest_json(data=[event_dict], agent="test")
            assert result.success is True

            # Verify RDF structure
            # 1. Entity exists
            entity_uri = URIRef(f"http://unrdf.org/data/{event.event_id}")
            assert (entity_uri, None, None) in engine.graph

            # 2. Type is set correctly
            type_query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?type WHERE {{
                <http://unrdf.org/data/{event.event_id}> unrdf:type ?type .
            }}
            """
            type_results = list(engine.query(type_query))
            assert len(type_results) > 0

            # 3. Properties exist
            prop_query = f"""
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?p ?o WHERE {{
                <http://unrdf.org/data/{event.event_id}> ?p ?o .
            }}
            """
            props = list(engine.query(prop_query))
            assert len(props) >= 4  # At least id, type, timestamp, app_name

            # 4. Verify provenance tracking
            provenance = engine.get_provenance(
                entity_uri, UNRDF.type, Literal("AppEvent")
            )
            assert provenance is not None
            assert provenance.agent == "test"

    def test_pipeline_handles_time_windows(self):
        """Test that pipeline correctly handles time window aggregation."""
        events, start_time, end_time = create_sample_daily_events()

        config = FeatureConfig(
            enabled_features=["app_usage_time"],
            aggregation_windows=["1h", "1d"],  # Hourly and daily windows
        )
        materializer = FeatureMaterializer(config)

        # Materialize with hourly window
        hourly_start = start_time.replace(minute=0, second=0, microsecond=0)
        hourly_end = hourly_start + timedelta(hours=1)

        hourly_features = materializer.materialize(
            events, hourly_start, hourly_end
        )

        # Verify only events in first hour are included
        first_hour_events = [
            e for e in events if hourly_start <= e.timestamp < hourly_end
        ]
        assert len(first_hour_events) > 0

        # Check feature values match expectations
        for feature in hourly_features:
            if "VSCode" in feature.feature_id:
                # VSCode was used in first hour
                assert feature.value > 0
                assert feature.window_start == hourly_start
                assert feature.window_end == hourly_end
