"""Shared fixtures for Aletheia data pipeline tests."""

import os
import sys

import pandas as pd
import pytest

# Ensure repo root is on sys.path so `from data.X import Y` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SAMPLE_CSV_DATA = {
    "incident_id": ["1469", "791", "SUPP-S3-001"],
    "title": [
        "DB deletion incident",
        "Fecal matter AI recommendation",
        "Scope creep paper example",
    ],
    "description": [
        (
            "Claude Code agent deleted the production database without authorization, "
            "overstepping its scope and exceeding its mandate."
        ),
        (
            "Google AI missed context blindness in food recommendation, "
            "failed to understand pragmatic intent."
        ),
        (
            "AI agent exceeded its scope and took unauthorized action beyond "
            "its mandate, overstepping its permitted boundary."
        ),
    ],
    "signatures": ["S3", "S4", "S3,S5"],
    "source": ["AIID", "AIID", "CAIS"],
    "source_url": [
        "https://incidentdatabase.ai/cite/1469",
        "https://incidentdatabase.ai/cite/791",
        "https://cais.example.com/paper1",
    ],
    "annotation_confidence": [0.8, 0.7, 0.9],
    "annotated_by": [
        "keyword_classifier_v1",
        "keyword_classifier_v1",
        "human_curated",
    ],
    "date_annotated": ["2026-06-20", "2026-06-20", "2026-06-20"],
}


@pytest.fixture
def sample_df():
    return pd.DataFrame(SAMPLE_CSV_DATA)


@pytest.fixture
def sample_csv(tmp_path, sample_df):
    path = tmp_path / "test_annotated.csv"
    sample_df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def mock_aiid_response():
    return {
        "data": {
            "incidents": [
                {
                    "incident_id": 1469,
                    "title": "Claude Code deleted production database",
                    "date": "2024-11-01",
                    "reports": [
                        {
                            "title": "PocketOS incident report",
                            "text": (
                                "AI agent deleted the production database without "
                                "authorization. The agent exceeded its scope and took "
                                "unauthorized deletion actions beyond its mandate."
                            ),
                            "url": "https://example.com/pocketos",
                        }
                    ],
                }
            ]
        }
    }
