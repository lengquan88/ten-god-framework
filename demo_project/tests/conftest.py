"""pytest fixtures for config_manager tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

import tengod.config_manager as cm


@pytest.fixture(autouse=True)
def reset_config_global_state():
    """Reset config_manager global state before each test."""
    # Save original state
    orig_instance = cm._CONFIG_INSTANCE
    orig_path = cm._CONFIG_PATH
    orig_mtime = cm._CONFIG_MTIME
    orig_hot_reload = cm._CONFIG_HOT_RELOAD
    orig_interval = cm._CONFIG_HOT_RELOAD_INTERVAL

    # Reset
    cm._CONFIG_INSTANCE = None
    cm._CONFIG_PATH = None
    cm._CONFIG_MTIME = 0
    cm._CONFIG_HOT_RELOAD = False
    cm._CONFIG_HOT_RELOAD_INTERVAL = 5

    yield

    # Restore
    cm._CONFIG_INSTANCE = orig_instance
    cm._CONFIG_PATH = orig_path
    cm._CONFIG_MTIME = orig_mtime
    cm._CONFIG_HOT_RELOAD = orig_hot_reload
    cm._CONFIG_HOT_RELOAD_INTERVAL = orig_interval


@pytest.fixture
def temp_yaml_config():
    """Create a temporary YAML config file."""
    content = """\
name: test-tengod
server:
  host: 127.0.0.1
  port: 9090
  mode: simple
  workers: 2
  cors_origins:
    - http://localhost:3000
database:
  backend: sqlite
  url: test.db
  pool_size: 10
  wal_mode: false
  echo_sql: true
llm:
  provider: openai
  api_key: sk-test-key-1234567890
  api_base: https://api.openai.com
  model: gpt-4
  temperature: 0.5
  max_tokens: 4096
  timeout: 30.0
  max_retries: 5
  retry_backoff: 3.0
security:
  jwt_secret: test-secret-key
  jwt_algorithm: HS512
  jwt_expire_minutes: 120
  rate_limit_capacity: 200
  rate_limit_refill_rate: 20.0
  audit_enabled: false
  audit_backend: json
scheduler:
  max_workers: 8
  timeout: 60
  queue_size: 200
  cache_enabled: false
  cache_size: 500
consensus:
  enabled: true
  node_id: node-1
  peer_addresses:
    - 10.0.0.1:8000
    - 10.0.0.2:8000
  election_timeout_min: 3.0
  election_timeout_max: 8.0
  heartbeat_interval: 1.5
knowledge:
  backend: sqlite
  vector_enabled: true
  vector_backend: faiss
  max_node_size: 50000
  index_path: /data/faiss.index
monitoring:
  prometheus_enabled: false
  log_level: DEBUG
  log_format: text
  health_check_interval: 60
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        f.flush()
        yield f.name

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def minimal_yaml_config():
    """Create a minimal YAML config file."""
    content = "name: minimal\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        f.flush()
        yield f.name

    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def invalid_yaml_file():
    """Create an invalid YAML file."""
    content = "name: [unclosed\n  indented: wrong: way\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        f.flush()
        yield f.name

    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def clean_env():
    """Remove all TENGOD_* env vars during test."""
    to_restore = {}
    for key in list(os.environ.keys()):
        if key.startswith("TENGOD_"):
            to_restore[key] = os.environ.pop(key)

    yield

    for key, val in to_restore.items():
        os.environ[key] = val