"""Database schema definitions for YAWL persistence.

Defines SQL schema for storing runtime state including
cases, work items, checkpoints, and history.
"""

from __future__ import annotations

from dataclasses import dataclass

# SQL schema definitions
SCHEMA_SQL = """
-- YAWL Engine Persistence Schema

-- Specifications
CREATE TABLE IF NOT EXISTS yawl_specifications (
    id VARCHAR(255) PRIMARY KEY,
    uri VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    status VARCHAR(50) NOT NULL DEFAULT 'INACTIVE',
    documentation TEXT,
    xml_content TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spec_uri ON yawl_specifications(uri);
CREATE INDEX IF NOT EXISTS idx_spec_status ON yawl_specifications(status);

-- Cases
CREATE TABLE IF NOT EXISTS yawl_cases (
    id VARCHAR(255) PRIMARY KEY,
    specification_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    root_net_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    parent_case_id VARCHAR(255),
    parent_work_item_id VARCHAR(255),
    FOREIGN KEY (specification_id) REFERENCES yawl_specifications(id),
    FOREIGN KEY (parent_case_id) REFERENCES yawl_cases(id)
);

CREATE INDEX IF NOT EXISTS idx_case_spec ON yawl_cases(specification_id);
CREATE INDEX IF NOT EXISTS idx_case_status ON yawl_cases(status);
CREATE INDEX IF NOT EXISTS idx_case_parent ON yawl_cases(parent_case_id);

-- Case Data
CREATE TABLE IF NOT EXISTS yawl_case_data (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    value TEXT,
    data_type VARCHAR(50) DEFAULT 'string',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES yawl_cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_case_data_case ON yawl_case_data(case_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_case_data_name ON yawl_case_data(case_id, name);

-- Work Items
CREATE TABLE IF NOT EXISTS yawl_work_items (
    id VARCHAR(255) PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    net_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fired_at TIMESTAMP,
    allocated_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    allocated_to VARCHAR(255),
    started_by VARCHAR(255),
    completed_by VARCHAR(255),
    instance_number INTEGER DEFAULT 0,
    data_in TEXT,
    data_out TEXT,
    FOREIGN KEY (case_id) REFERENCES yawl_cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wi_case ON yawl_work_items(case_id);
CREATE INDEX IF NOT EXISTS idx_wi_task ON yawl_work_items(task_id);
CREATE INDEX IF NOT EXISTS idx_wi_status ON yawl_work_items(status);
CREATE INDEX IF NOT EXISTS idx_wi_allocated ON yawl_work_items(allocated_to);

-- Work Item History (for RBAC)
CREATE TABLE IF NOT EXISTS yawl_work_item_history (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    work_item_id VARCHAR(255) NOT NULL,
    participant_id VARCHAR(255) NOT NULL,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    task_name VARCHAR(255),
    duration_ms INTEGER,
    FOREIGN KEY (case_id) REFERENCES yawl_cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wih_case ON yawl_work_item_history(case_id);
CREATE INDEX IF NOT EXISTS idx_wih_task ON yawl_work_item_history(task_id);
CREATE INDEX IF NOT EXISTS idx_wih_participant ON yawl_work_item_history(participant_id);

-- Timers
CREATE TABLE IF NOT EXISTS yawl_timers (
    id VARCHAR(255) PRIMARY KEY,
    work_item_id VARCHAR(255) NOT NULL,
    case_id VARCHAR(255) NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fired BOOLEAN DEFAULT FALSE,
    fired_at TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES yawl_cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timer_wi ON yawl_timers(work_item_id);
CREATE INDEX IF NOT EXISTS idx_timer_expires ON yawl_timers(expires_at);
CREATE INDEX IF NOT EXISTS idx_timer_fired ON yawl_timers(fired);

-- Net Runner State (markings)
CREATE TABLE IF NOT EXISTS yawl_net_runners (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    net_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    marking_json TEXT,
    enabled_tasks TEXT,
    completed BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES yawl_cases(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_nr_case_net ON yawl_net_runners(case_id, net_id);

-- Checkpoints
CREATE TABLE IF NOT EXISTS yawl_checkpoints (
    id VARCHAR(255) PRIMARY KEY,
    case_id VARCHAR(255),
    engine_id VARCHAR(255),
    checkpoint_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    restored_at TIMESTAMP,
    state_json TEXT NOT NULL,
    description VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_cp_case ON yawl_checkpoints(case_id);
CREATE INDEX IF NOT EXISTS idx_cp_engine ON yawl_checkpoints(engine_id);
CREATE INDEX IF NOT EXISTS idx_cp_created ON yawl_checkpoints(created_at);

-- Worklet Cases
CREATE TABLE IF NOT EXISTS yawl_worklet_cases (
    id VARCHAR(255) PRIMARY KEY,
    worklet_id VARCHAR(255) NOT NULL,
    parent_case_id VARCHAR(255) NOT NULL,
    parent_work_item_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    exception_type VARCHAR(255),
    exception_data TEXT,
    result_data TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (parent_case_id) REFERENCES yawl_cases(id)
);

CREATE INDEX IF NOT EXISTS idx_wc_parent ON yawl_worklet_cases(parent_case_id);
CREATE INDEX IF NOT EXISTS idx_wc_status ON yawl_worklet_cases(status);

-- Events/Audit Log
CREATE TABLE IF NOT EXISTS yawl_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    case_id VARCHAR(255),
    work_item_id VARCHAR(255),
    task_id VARCHAR(255),
    participant_id VARCHAR(255),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_evt_case ON yawl_events(case_id);
CREATE INDEX IF NOT EXISTS idx_evt_type ON yawl_events(event_type);
CREATE INDEX IF NOT EXISTS idx_evt_time ON yawl_events(timestamp);
"""


@dataclass
class DatabaseSchema:
    """Database schema manager.

    Provides schema creation and migration operations.

    Parameters
    ----------
    schema_version : str
        Current schema version
    """

    schema_version: str = "1.0.0"

    def get_create_schema_sql(self) -> str:
        """Get SQL to create schema.

        Returns
        -------
        str
            CREATE TABLE statements
        """
        return SCHEMA_SQL

    def get_drop_schema_sql(self) -> str:
        """Get SQL to drop schema.

        Returns
        -------
        str
            DROP TABLE statements
        """
        return """
DROP TABLE IF EXISTS yawl_events CASCADE;
DROP TABLE IF EXISTS yawl_worklet_cases CASCADE;
DROP TABLE IF EXISTS yawl_checkpoints CASCADE;
DROP TABLE IF EXISTS yawl_net_runners CASCADE;
DROP TABLE IF EXISTS yawl_timers CASCADE;
DROP TABLE IF EXISTS yawl_work_item_history CASCADE;
DROP TABLE IF EXISTS yawl_work_items CASCADE;
DROP TABLE IF EXISTS yawl_case_data CASCADE;
DROP TABLE IF EXISTS yawl_cases CASCADE;
DROP TABLE IF EXISTS yawl_specifications CASCADE;
"""

    def get_table_names(self) -> list[str]:
        """Get list of table names.

        Returns
        -------
        list[str]
            Table names
        """
        return [
            "yawl_specifications",
            "yawl_cases",
            "yawl_case_data",
            "yawl_work_items",
            "yawl_work_item_history",
            "yawl_timers",
            "yawl_net_runners",
            "yawl_checkpoints",
            "yawl_worklet_cases",
            "yawl_events",
        ]
