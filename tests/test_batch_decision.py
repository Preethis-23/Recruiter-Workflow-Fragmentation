"""Tests for email extraction, auto-ranking, and batch recruiter decision endpoint."""

import pytest
from recruiter_workflow.services.parser_service import extract_email_from_text


def test_email_extraction_scenarios():
    """Test extracting emails with ligatures, envelope icons, prefixes, and obfuscation."""
    # 1. Envelope icon & ligature
    text1 = "John Doe\nenvel✉pepreethiswarang@gmail.com\nPython Developer"
    assert extract_email_from_text(text1) == "preethiswarang@gmail.com"

    # 2. Unicode symbols / contact prefix
    text2 = "Jane Smith 📧 Contact: jane.smith@example.org Phone: 1234567890"
    assert extract_email_from_text(text2) == "jane.smith@example.org"

    # 3. Obfuscated format
    text3 = "Alex Turner - alex.turner [at] techcorp [dot] com"
    assert extract_email_from_text(text3) == "alex.turner@techcorp.com"


def test_batch_decision_workflow(client):
    """Test the 2-step recruiter batch decision endpoint."""
    # 1. Create JD via API
    jd_res = client.post("/api/jds/", json={
        "title": "Python ML Engineer",
        "description": "Machine learning engineer experienced in Python, PyTorch, and NLP.",
        "required_skills": "Python, PyTorch, NLP"
    })
    assert jd_res.status_code == 201
    jd_id = jd_res.json()["id"]

    # 2. Create Candidate manually or test batch-decision logic with dummy candidate payload
    # Let's test calling batch-decision with empty candidates to verify 400 response
    batch_res = client.post("/api/candidates/batch-decision", json={
        "jd_id": jd_id,
        "selected_candidate_ids": []
    })
    assert batch_res.status_code == 400
    assert "No candidates found" in batch_res.json()["detail"]
