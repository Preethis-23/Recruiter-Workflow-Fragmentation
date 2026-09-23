"""Test two-tier matching fallback mechanism (Cloud API -> Local TF-IDF).

Verifies that when external cloud APIs fail or hit rate limits, the system
automatically falls back to local TF-IDF similarity to guarantee 100% pipeline
matching availability across candidate profile records.
"""

from unittest.mock import patch
from recruiter_workflow.config import settings
from recruiter_workflow.services.embedding_service import compute_similarity, compute_similarity_tfidf


def test_two_tier_fallback_on_cloud_api_failure():
    """Verify that when Cloud API (OpenAI) raises an exception, local TF-IDF is used."""
    sample_resume = "Experienced Senior Python Engineer with skills in Django, Celery, PostgreSQL, Redis."
    sample_jd = "Looking for a Python Developer with Django and PostgreSQL experience."

    # Compute expected local TF-IDF similarity score directly
    expected_tfidf_score = compute_similarity_tfidf(sample_resume, sample_jd)
    assert expected_tfidf_score > 0.0

    # 1. Simulate Cloud API failure (e.g. RateLimitError, APIConnectionError, Timeout)
    with patch("recruiter_workflow.services.embedding_service.compute_similarity_openai", side_effect=Exception("Cloud API Rate Limit Exceeded (429)")):
        with patch.object(settings, "LLM_PROVIDER", "openai"):
            with patch.object(settings, "OPENAI_API_KEY", "sk-mock-key"):
                # Call main dispatch compute_similarity
                score = compute_similarity(sample_resume, sample_jd)
                
                # Should not crash, and should return valid similarity score via TF-IDF fallback
                assert score is not None
                assert isinstance(score, float)
                assert score == expected_tfidf_score
                assert score > 0.0


def test_100_percent_availability_across_multiple_records():
    """Verify 100% matching availability across multiple job description and resume pairs during simulated cloud outage."""
    jds = [
        "Senior Backend Engineer Python Django Celery PostgreSQL",
        "Frontend React Developer TypeScript Next.js Tailwind",
        "DevOps Cloud Engineer Kubernetes Docker AWS CI/CD",
    ]
    resumes = [
        "Backend Developer with 5 years experience in Python, Django, Redis, PostgreSQL.",
        "Frontend Engineer building responsive web apps with React, TypeScript, Redux.",
        "Infrastructure Architect skilled in Kubernetes, Terraform, Docker, AWS.",
    ]

    # Simulate cloud failure across all pairs
    with patch("recruiter_workflow.services.embedding_service.compute_similarity_openai", side_effect=Exception("Connection Timed Out")):
        with patch.object(settings, "LLM_PROVIDER", "openai"):
            with patch.object(settings, "OPENAI_API_KEY", "sk-test"):
                processed_count = 0
                successful_matches = 0

                for jd in jds:
                    for resume in resumes:
                        processed_count += 1
                        score = compute_similarity(resume, jd)
                        if score is not None and score >= 0.0:
                            successful_matches += 1

                # 100% availability rate
                availability_rate = (successful_matches / processed_count) * 100.0
                assert availability_rate == 100.0
                assert successful_matches == 9
