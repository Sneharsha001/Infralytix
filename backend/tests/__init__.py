"""
Infralytix Backend — Test Suite.

Test organization:
  tests/unit/         — Pure unit tests, no I/O, no database
  tests/integration/  — Tests that require a running database

Markers (defined in pyproject.toml):
  @pytest.mark.unit        — Unit tests
  @pytest.mark.integration — Integration tests (needs DB)
  @pytest.mark.slow        — Tests > 1 second
"""
