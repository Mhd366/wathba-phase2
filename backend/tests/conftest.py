import pytest


@pytest.fixture(autouse=True)
def isolate_database(monkeypatch):
    """API contract tests never write to the production Supabase database."""
    monkeypatch.setattr("app.main.save_analysis", lambda owner_id, request, result: None)
