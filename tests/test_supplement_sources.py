"""Unit tests for data/supplement_sources.py — no network calls, pure logic."""

import csv
import os
import re

import pytest

from data.supplement_sources import (
    S3_SUPPLEMENTAL_INCIDENTS,
    S4_SUPPLEMENTAL_INCIDENTS,
    SUPPLEMENTAL_REGISTRY,
    CSV_COLUMNS,
    annotate_incident,
    get_incidents_for_signatures,
    save_supplemental,
)

REQUIRED_RAW_FIELDS = {"incident_id", "title", "description", "source", "source_url"}
SUPP_ID_PATTERN = re.compile(r"^SUPP-(S3|S4)-\d{3}$")


# ── Dataset integrity ──────────────────────────────────────────────────────────

class TestDatasetIntegrity:
    def test_s3_has_at_least_20_incidents(self):
        assert len(S3_SUPPLEMENTAL_INCIDENTS) >= 20

    def test_s4_has_at_least_20_incidents(self):
        assert len(S4_SUPPLEMENTAL_INCIDENTS) >= 20

    def test_all_s3_incidents_have_required_fields(self):
        for inc in S3_SUPPLEMENTAL_INCIDENTS:
            missing = REQUIRED_RAW_FIELDS - set(inc.keys())
            assert not missing, f"{inc.get('incident_id')} missing: {missing}"

    def test_all_s4_incidents_have_required_fields(self):
        for inc in S4_SUPPLEMENTAL_INCIDENTS:
            missing = REQUIRED_RAW_FIELDS - set(inc.keys())
            assert not missing, f"{inc.get('incident_id')} missing: {missing}"

    def test_s3_incident_ids_are_unique(self):
        ids = [inc["incident_id"] for inc in S3_SUPPLEMENTAL_INCIDENTS]
        assert len(ids) == len(set(ids))

    def test_s4_incident_ids_are_unique(self):
        ids = [inc["incident_id"] for inc in S4_SUPPLEMENTAL_INCIDENTS]
        assert len(ids) == len(set(ids))

    def test_no_overlap_between_s3_and_s4_ids(self):
        s3_ids = {inc["incident_id"] for inc in S3_SUPPLEMENTAL_INCIDENTS}
        s4_ids = {inc["incident_id"] for inc in S4_SUPPLEMENTAL_INCIDENTS}
        assert s3_ids.isdisjoint(s4_ids)

    def test_s3_ids_match_naming_convention(self):
        for inc in S3_SUPPLEMENTAL_INCIDENTS:
            iid = inc["incident_id"]
            assert SUPP_ID_PATTERN.match(iid), f"Bad ID format: {iid}"
            assert iid.startswith("SUPP-S3-")

    def test_s4_ids_match_naming_convention(self):
        for inc in S4_SUPPLEMENTAL_INCIDENTS:
            iid = inc["incident_id"]
            assert SUPP_ID_PATTERN.match(iid), f"Bad ID format: {iid}"
            assert iid.startswith("SUPP-S4-")

    def test_all_incidents_have_non_empty_title(self):
        for inc in S3_SUPPLEMENTAL_INCIDENTS + S4_SUPPLEMENTAL_INCIDENTS:
            assert inc["title"].strip(), f"{inc['incident_id']} has empty title"

    def test_all_incidents_have_non_empty_description(self):
        for inc in S3_SUPPLEMENTAL_INCIDENTS + S4_SUPPLEMENTAL_INCIDENTS:
            assert inc["description"].strip(), f"{inc['incident_id']} has empty description"

    def test_registry_contains_s3_and_s4(self):
        assert "S3" in SUPPLEMENTAL_REGISTRY
        assert "S4" in SUPPLEMENTAL_REGISTRY


# ── get_incidents_for_signatures ───────────────────────────────────────────────

class TestGetIncidentsForSignatures:
    def test_s3_only_returns_only_s3(self):
        result = get_incidents_for_signatures(["S3"])
        ids = [inc["incident_id"] for inc in result]
        assert all(iid.startswith("SUPP-S3-") for iid in ids)
        assert len(result) == len(S3_SUPPLEMENTAL_INCIDENTS)

    def test_s4_only_returns_only_s4(self):
        result = get_incidents_for_signatures(["S4"])
        ids = [inc["incident_id"] for inc in result]
        assert all(iid.startswith("SUPP-S4-") for iid in ids)

    def test_both_s3_and_s4_returns_combined(self):
        result = get_incidents_for_signatures(["S3", "S4"])
        total = len(S3_SUPPLEMENTAL_INCIDENTS) + len(S4_SUPPLEMENTAL_INCIDENTS)
        assert len(result) == total

    def test_empty_list_returns_all_registered(self):
        result = get_incidents_for_signatures([])
        total = len(S3_SUPPLEMENTAL_INCIDENTS) + len(S4_SUPPLEMENTAL_INCIDENTS)
        assert len(result) == total

    def test_unknown_signature_returns_empty(self):
        result = get_incidents_for_signatures(["S9"])
        assert result == []

    def test_order_is_s3_then_s4_for_both(self):
        result = get_incidents_for_signatures(["S3", "S4"])
        s3_end = len(S3_SUPPLEMENTAL_INCIDENTS)
        assert result[0]["incident_id"].startswith("SUPP-S3-")
        assert result[s3_end]["incident_id"].startswith("SUPP-S4-")


# ── annotate_incident ──────────────────────────────────────────────────────────

class TestAnnotateIncident:
    def _raw_s3(self):
        return S3_SUPPLEMENTAL_INCIDENTS[0]

    def _raw_s4(self):
        return S4_SUPPLEMENTAL_INCIDENTS[0]

    def test_returns_all_csv_schema_columns(self):
        row = annotate_incident(self._raw_s3(), "S3", date_annotated="2026-06-20")
        for col in CSV_COLUMNS:
            assert col in row, f"Missing column: {col}"

    def test_primary_signature_always_included(self):
        row = annotate_incident(self._raw_s3(), "S3", date_annotated="2026-06-20")
        assert "S3" in row["signatures"].split(",")

    def test_confidence_floored_at_0_7(self):
        # Even if classifier scores low, human-curated incidents get >= 0.7
        raw = {
            "incident_id": "SUPP-S3-TEST",
            "title": "Completely unrelated text with no keywords",
            "description": "Weather was nice today",
            "source": "test",
            "source_url": "http://test.com",
        }
        row = annotate_incident(raw, "S3", date_annotated="2026-06-20")
        assert row["annotation_confidence"] >= 0.7

    def test_annotated_by_contains_human_curated(self):
        row = annotate_incident(self._raw_s3(), "S3", date_annotated="2026-06-20")
        assert "human_curated" in row["annotated_by"]

    def test_date_annotated_used_when_provided(self):
        row = annotate_incident(self._raw_s3(), "S3", date_annotated="2026-01-01")
        assert row["date_annotated"] == "2026-01-01"

    def test_date_annotated_defaults_to_today(self):
        import datetime
        row = annotate_incident(self._raw_s3(), "S3")
        today = datetime.date.today().isoformat()
        assert row["date_annotated"] == today

    def test_source_and_source_url_preserved(self):
        raw = self._raw_s3()
        row = annotate_incident(raw, "S3", date_annotated="2026-06-20")
        assert row["source"] == raw["source"]
        assert row["source_url"] == raw["source_url"]

    def test_incident_id_preserved(self):
        raw = self._raw_s3()
        row = annotate_incident(raw, "S3", date_annotated="2026-06-20")
        assert row["incident_id"] == raw["incident_id"]

    def test_cross_tagging_adds_additional_signatures(self):
        """Text with both S3 and S5 keywords should get both signatures tagged."""
        raw = {
            "incident_id": "SUPP-S3-CROSS",
            "title": "Agent exceeded scope and had no stop mechanism",
            "description": (
                "AI agent deleted files beyond mandate unsanctioned scope creep. "
                "Additionally, no stop mechanism existed and the system failed to halt "
                "with no override, stuck in loop."
            ),
            "source": "test",
            "source_url": "http://example.com",
        }
        row = annotate_incident(raw, "S3", date_annotated="2026-06-20")
        sigs = row["signatures"].split(",")
        assert "S3" in sigs
        # S5 keywords present — may be cross-tagged at threshold 0.5
        # (2 S5 keywords → score 0.8 > 0.5)
        assert "S5" in sigs

    def test_s4_annotation(self):
        row = annotate_incident(self._raw_s4(), "S4", date_annotated="2026-06-20")
        assert "S4" in row["signatures"].split(",")
        assert row["annotation_confidence"] >= 0.7


# ── save_supplemental ──────────────────────────────────────────────────────────

class TestSaveSupplemental:
    def _make_rows(self, n=3):
        return [
            annotate_incident(S3_SUPPLEMENTAL_INCIDENTS[i], "S3",
                              date_annotated="2026-06-20")
            for i in range(n)
        ]

    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "supp.csv")
        save_supplemental(self._make_rows(), path)
        assert os.path.isfile(path)

    def test_creates_parent_directory(self, tmp_path):
        path = str(tmp_path / "subdir" / "supp.csv")
        save_supplemental(self._make_rows(), path)
        assert os.path.isfile(path)

    def test_written_file_has_correct_schema(self, tmp_path):
        path = str(tmp_path / "supp.csv")
        save_supplemental(self._make_rows(), path)
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            assert set(reader.fieldnames) == set(CSV_COLUMNS)

    def test_all_rows_written(self, tmp_path):
        path = str(tmp_path / "supp.csv")
        rows = self._make_rows(5)
        save_supplemental(rows, path)
        with open(path, newline="") as f:
            written = list(csv.DictReader(f))
        assert len(written) == 5

    def test_incident_ids_preserved_in_output(self, tmp_path):
        path = str(tmp_path / "supp.csv")
        rows = self._make_rows(2)
        save_supplemental(rows, path)
        with open(path, newline="") as f:
            written = list(csv.DictReader(f))
        written_ids = {r["incident_id"] for r in written}
        expected_ids = {r["incident_id"] for r in rows}
        assert written_ids == expected_ids
