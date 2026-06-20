"""Unit tests for data/expand_aiid.py — all API calls are mocked."""

import csv
import os

import pytest
from unittest.mock import MagicMock, patch, call

from data.expand_aiid import (
    extract_incident_text,
    fetch_aiid_page,
    fetch_all_incidents,
    incident_to_row,
    load_existing_ids,
    save_to_csv,
    CSV_COLUMNS,
)


# ── fetch_aiid_page ────────────────────────────────────────────────────────────

class TestFetchAiidPage:
    def _make_session(self, status_code, json_data=None, side_effects=None):
        session = MagicMock()
        if side_effects:
            session.post.side_effect = side_effects
        else:
            mock_resp = MagicMock()
            mock_resp.status_code = status_code
            mock_resp.json.return_value = json_data or {}
            session.post.return_value = mock_resp
        return session

    def test_success_returns_incident_list(self, mock_aiid_response):
        session = self._make_session(200, mock_aiid_response)
        result = fetch_aiid_page(10, 0, session)
        assert len(result) == 1
        assert result[0]["incident_id"] == 1469

    def test_http_500_returns_empty_list(self):
        session = self._make_session(500)
        result = fetch_aiid_page(10, 0, session)
        assert result == []

    def test_http_404_returns_empty_list(self):
        session = self._make_session(404)
        result = fetch_aiid_page(10, 0, session)
        assert result == []

    def test_malformed_json_returns_empty_list(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        session.post.return_value = mock_resp
        result = fetch_aiid_page(10, 0, session)
        assert result == []

    def test_missing_incidents_key_returns_empty_list(self):
        session = self._make_session(200, {"data": {}})
        result = fetch_aiid_page(10, 0, session)
        assert result == []

    def test_rate_limit_then_success_returns_data(self, mock_aiid_response):
        """429 on first call, 200 on second — should retry and succeed."""
        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = mock_aiid_response

        session = MagicMock()
        session.post.side_effect = [rate_limit_resp, success_resp]

        with patch("data.expand_aiid.time.sleep"):
            result = fetch_aiid_page(10, 0, session)

        assert len(result) == 1

    def test_network_error_returns_empty_list(self):
        import requests as req
        session = MagicMock()
        session.post.side_effect = req.ConnectionError("refused")
        with patch("data.expand_aiid.time.sleep"):
            result = fetch_aiid_page(10, 0, session)
        assert result == []

    def test_passes_correct_limit_and_skip(self, mock_aiid_response):
        session = self._make_session(200, mock_aiid_response)
        fetch_aiid_page(50, 200, session)
        call_kwargs = session.post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["variables"]["limit"] == 50
        assert payload["variables"]["skip"] == 200


# ── fetch_all_incidents ────────────────────────────────────────────────────────

class TestFetchAllIncidents:
    def test_respects_limit(self, mock_aiid_response):
        """With limit=1, page_size=100, should call page once and return 1 incident."""
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_aiid_response
        session.post.return_value = mock_resp

        with patch("data.expand_aiid.time.sleep"):
            result = fetch_all_incidents(limit=1, offset=0, session=session, page_size=100)

        assert len(result) == 1

    def test_respects_offset_in_first_request(self, mock_aiid_response):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_aiid_response
        # Second call returns empty to stop pagination
        empty_resp = MagicMock()
        empty_resp.status_code = 200
        empty_resp.json.return_value = {"data": {"incidents": []}}
        session.post.side_effect = [mock_resp, empty_resp, empty_resp, empty_resp]

        with patch("data.expand_aiid.time.sleep"):
            fetch_all_incidents(limit=10, offset=200, session=session, page_size=10)

        first_call = session.post.call_args_list[0]
        payload = first_call[1]["json"]
        assert payload["variables"]["skip"] == 200

    def test_stops_after_3_consecutive_empty_pages(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"incidents": []}}
        session.post.return_value = mock_resp

        with patch("data.expand_aiid.time.sleep"):
            result = fetch_all_incidents(limit=100, offset=0, session=session, page_size=10)

        assert result == []
        assert session.post.call_count == 3

    def test_paginates_across_multiple_pages(self):
        page1 = {"data": {"incidents": [{"incident_id": i, "title": f"Inc {i}",
                                          "date": "2024", "reports": []}
                                         for i in range(3)]}}
        page2 = {"data": {"incidents": [{"incident_id": i, "title": f"Inc {i}",
                                          "date": "2024", "reports": []}
                                         for i in range(3, 5)]}}
        empty = {"data": {"incidents": []}}

        session = MagicMock()
        responses = []
        for data in [page1, page2, empty, empty, empty]:
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = data
            responses.append(r)
        session.post.side_effect = responses

        with patch("data.expand_aiid.time.sleep"):
            result = fetch_all_incidents(limit=10, offset=0, session=session, page_size=3)

        assert len(result) == 5


# ── extract_incident_text ──────────────────────────────────────────────────────

class TestExtractIncidentText:
    def test_includes_title_and_report_text(self):
        inc = {
            "title": "Main title",
            "reports": [{"title": "Report A", "text": "Some text", "url": "http://x.com"}],
        }
        text = extract_incident_text(inc)
        assert "Main title" in text
        assert "Report A" in text
        assert "Some text" in text

    def test_truncates_long_report_text(self):
        inc = {
            "title": "T",
            "reports": [{"title": "R", "text": "x" * 1000, "url": ""}],
        }
        text = extract_incident_text(inc)
        assert len(text) <= 550

    def test_handles_empty_reports(self):
        inc = {"title": "Just the title", "reports": []}
        text = extract_incident_text(inc)
        assert text == "Just the title"

    def test_handles_null_reports(self):
        inc = {"title": "Title only", "reports": None}
        text = extract_incident_text(inc)
        assert "Title only" in text

    def test_handles_missing_report_text(self):
        inc = {
            "title": "T",
            "reports": [{"title": "R", "url": "http://x.com"}],
        }
        text = extract_incident_text(inc)
        assert "T" in text
        assert "R" in text

    def test_multiple_reports_combined(self):
        inc = {
            "title": "T",
            "reports": [
                {"title": "R1", "text": "text one", "url": ""},
                {"title": "R2", "text": "text two", "url": ""},
            ],
        }
        text = extract_incident_text(inc)
        assert "R1" in text
        assert "R2" in text
        assert "text one" in text
        assert "text two" in text


# ── incident_to_row ────────────────────────────────────────────────────────────

class TestIncidentToRow:
    def _make_incident(self, text=""):
        return {
            "incident_id": 42,
            "title": text,
            "date": "2024-01-01",
            "reports": [{"title": "", "text": text, "url": "http://example.com"}],
        }

    def test_matching_text_returns_row(self):
        inc = self._make_incident(
            "The agent deleted the production database without authorization, "
            "exceeding its scope beyond mandate"
        )
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        assert row is not None
        assert "S3" in row["signatures"]

    def test_non_matching_text_returns_none(self):
        inc = self._make_incident("The weather was sunny today with no clouds")
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        assert row is None

    def test_signature_filter_restricts_results(self):
        inc = self._make_incident(
            "Agent deleted files without authorization exceeding scope, "
            "also fabricated false information and hallucination"
        )
        row = incident_to_row(inc, target_sigs=["S3"], min_confidence=0.3)
        assert row is not None
        sigs = row["signatures"].split(",")
        assert all(s == "S3" for s in sigs)

    def test_returns_all_csv_schema_columns(self):
        inc = self._make_incident(
            "Agent deleted database without authorization overstepped scope exceeded mandate"
        )
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        assert row is not None
        for col in CSV_COLUMNS:
            assert col in row

    def test_incident_id_is_string(self):
        inc = self._make_incident(
            "deleted files unauthorized action exceeded scope overstepped"
        )
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        if row:
            assert isinstance(row["incident_id"], str)

    def test_source_is_aiid(self):
        inc = self._make_incident(
            "AI agent deleted production database unauthorized action beyond mandate"
        )
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        if row:
            assert row["source"] == "AIID"

    def test_source_url_from_first_report(self):
        inc = {
            "incident_id": 99,
            "title": "deleted files unauthorized action scope",
            "date": "2024",
            "reports": [
                {"title": "", "text": "unauthorized action beyond mandate deleted",
                 "url": "http://first-report.com"},
                {"title": "", "text": "more text", "url": "http://second.com"},
            ],
        }
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        if row:
            assert row["source_url"] == "http://first-report.com"

    def test_empty_target_sigs_allows_all_signatures(self):
        inc = self._make_incident(
            "hallucination fabricated false claim misinformation"
        )
        row = incident_to_row(inc, target_sigs=[], min_confidence=0.3)
        assert row is not None
        assert "S1" in row["signatures"]


# ── load_existing_ids ──────────────────────────────────────────────────────────

class TestLoadExistingIds:
    def test_returns_empty_set_when_file_missing(self, tmp_path):
        result = load_existing_ids(str(tmp_path / "nonexistent.csv"))
        assert result == set()

    def test_reads_ids_from_existing_csv(self, tmp_path):
        path = tmp_path / "existing.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()
            w.writerow({col: "" for col in CSV_COLUMNS} | {"incident_id": "1469"})
            w.writerow({col: "" for col in CSV_COLUMNS} | {"incident_id": "791"})
        result = load_existing_ids(str(path))
        assert "1469" in result
        assert "791" in result

    def test_reads_ids_from_extra_paths(self, tmp_path):
        path_a = tmp_path / "a.csv"
        path_b = tmp_path / "b.csv"
        for path, iid in [(path_a, "111"), (path_b, "222")]:
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                w.writeheader()
                w.writerow({col: "" for col in CSV_COLUMNS} | {"incident_id": iid})
        result = load_existing_ids(str(path_a), extra_paths=[str(path_b)])
        assert "111" in result
        assert "222" in result

    def test_ignores_missing_extra_path(self, tmp_path):
        path_a = tmp_path / "a.csv"
        with open(path_a, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()
            w.writerow({col: "" for col in CSV_COLUMNS} | {"incident_id": "42"})
        result = load_existing_ids(str(path_a), extra_paths=["/does/not/exist.csv"])
        assert "42" in result


# ── save_to_csv ────────────────────────────────────────────────────────────────

class TestSaveToCsv:
    def _make_row(self, incident_id, confidence=0.8):
        return {
            "incident_id": incident_id,
            "title": f"Title {incident_id}",
            "description": "desc",
            "signatures": "S3",
            "source": "AIID",
            "source_url": "http://example.com",
            "annotation_confidence": confidence,
            "annotated_by": "test",
            "date_annotated": "2026-06-20",
        }

    def test_creates_file_when_not_exists(self, tmp_path):
        path = str(tmp_path / "output.csv")
        save_to_csv([self._make_row("1")], path)
        assert os.path.isfile(path)

    def test_creates_parent_directory(self, tmp_path):
        path = str(tmp_path / "subdir" / "output.csv")
        save_to_csv([self._make_row("1")], path)
        assert os.path.isfile(path)

    def test_written_csv_has_correct_schema(self, tmp_path):
        path = str(tmp_path / "output.csv")
        save_to_csv([self._make_row("1")], path)
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            assert set(reader.fieldnames) == set(CSV_COLUMNS)

    def test_appends_and_deduplicates(self, tmp_path):
        path = str(tmp_path / "output.csv")
        save_to_csv([self._make_row("1", confidence=0.5)], path)
        save_to_csv([self._make_row("1", confidence=0.9), self._make_row("2")], path)
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        row_1 = next(r for r in rows if r["incident_id"] == "1")
        assert float(row_1["annotation_confidence"]) == pytest.approx(0.9)

    def test_deduplication_keeps_highest_confidence(self, tmp_path):
        path = str(tmp_path / "output.csv")
        rows = [
            self._make_row("42", confidence=0.3),
            self._make_row("42", confidence=0.95),
            self._make_row("42", confidence=0.6),
        ]
        save_to_csv(rows, path)
        with open(path, newline="") as f:
            result = list(csv.DictReader(f))
        assert len(result) == 1
        assert float(result[0]["annotation_confidence"]) == pytest.approx(0.95)
