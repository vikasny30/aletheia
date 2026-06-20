"""Unit tests for data/validation_status.py"""

import json
import os

import pandas as pd
import pytest

from data.validation_status import (
    ALL_SIGNATURES,
    REQUIRED_COLUMNS,
    compute_gap_table,
    expand_signatures,
    find_csv_files,
    load_and_merge,
    to_json_output,
)


# ── find_csv_files ─────────────────────────────────────────────────────────────

class TestFindCsvFiles:
    def test_empty_dir_returns_empty_list(self, tmp_path):
        assert find_csv_files(str(tmp_path)) == []

    def test_finds_multiple_csv_files(self, tmp_path):
        for name in ["a.csv", "b.csv", "c.csv"]:
            (tmp_path / name).touch()
        assert len(find_csv_files(str(tmp_path))) == 3

    def test_ignores_non_csv_files(self, tmp_path):
        (tmp_path / "data.csv").touch()
        (tmp_path / "notes.txt").touch()
        (tmp_path / "report.json").touch()
        result = find_csv_files(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("data.csv")

    def test_does_not_recurse_into_subdirectories(self, tmp_path):
        subdir = tmp_path / "results"
        subdir.mkdir()
        (subdir / "nested.csv").touch()
        (tmp_path / "top.csv").touch()
        result = find_csv_files(str(tmp_path))
        assert len(result) == 1
        assert "top.csv" in result[0]

    def test_returns_sorted_paths(self, tmp_path):
        for name in ["c.csv", "a.csv", "b.csv"]:
            (tmp_path / name).touch()
        basenames = [os.path.basename(p) for p in find_csv_files(str(tmp_path))]
        assert basenames == ["a.csv", "b.csv", "c.csv"]


# ── load_and_merge ─────────────────────────────────────────────────────────────

class TestLoadAndMerge:
    def test_loads_single_valid_file(self, sample_csv):
        df = load_and_merge([sample_csv])
        assert len(df) == 3
        assert REQUIRED_COLUMNS.issubset(set(df.columns))

    def test_deduplication_keeps_higher_confidence(self, tmp_path, sample_df):
        df_low = sample_df.copy()
        df_low.loc[df_low["incident_id"] == "1469", "annotation_confidence"] = 0.4

        df_high = sample_df.copy()
        df_high.loc[df_high["incident_id"] == "1469", "annotation_confidence"] = 0.95

        path_low = str(tmp_path / "low.csv")
        path_high = str(tmp_path / "high.csv")
        df_low.to_csv(path_low, index=False)
        df_high.to_csv(path_high, index=False)

        merged = load_and_merge([path_low, path_high])
        row = merged[merged["incident_id"] == "1469"]
        assert len(row) == 1
        assert float(row["annotation_confidence"].iloc[0]) == pytest.approx(0.95)

    def test_deduplication_no_duplicate_ids(self, tmp_path, sample_df):
        path1 = str(tmp_path / "a.csv")
        path2 = str(tmp_path / "b.csv")
        sample_df.to_csv(path1, index=False)
        sample_df.to_csv(path2, index=False)
        merged = load_and_merge([path1, path2])
        assert merged["incident_id"].nunique() == len(merged)

    def test_skips_file_with_missing_columns(self, tmp_path, capsys):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("incident_id,title\n1,test\n")
        df = load_and_merge([str(bad_csv)])
        assert df.empty
        assert "missing columns" in capsys.readouterr().err

    def test_skips_unreadable_file_with_warning(self, tmp_path, capsys):
        df = load_and_merge([str(tmp_path / "nonexistent.csv")])
        assert df.empty
        assert "WARN" in capsys.readouterr().err

    def test_empty_path_list_returns_empty_dataframe(self):
        df = load_and_merge([])
        assert df.empty

    def test_incident_id_cast_to_string(self, sample_csv):
        df = load_and_merge([sample_csv])
        assert df["incident_id"].dtype == object

    def test_merges_two_valid_files(self, tmp_path):
        data_a = {
            "incident_id": ["1"], "title": ["A"], "description": ["desc A"],
            "signatures": ["S1"], "source": ["AIID"], "source_url": ["http://a.com"],
            "annotation_confidence": [0.8], "annotated_by": ["auto"],
            "date_annotated": ["2026-06-20"],
        }
        data_b = {
            "incident_id": ["2"], "title": ["B"], "description": ["desc B"],
            "signatures": ["S2"], "source": ["CAIS"], "source_url": ["http://b.com"],
            "annotation_confidence": [0.7], "annotated_by": ["human"],
            "date_annotated": ["2026-06-20"],
        }
        pd.DataFrame(data_a).to_csv(tmp_path / "a.csv", index=False)
        pd.DataFrame(data_b).to_csv(tmp_path / "b.csv", index=False)
        df = load_and_merge([str(tmp_path / "a.csv"), str(tmp_path / "b.csv")])
        assert len(df) == 2


# ── expand_signatures ──────────────────────────────────────────────────────────

class TestExpandSignatures:
    def test_single_signature_row(self, sample_df):
        result = expand_signatures(sample_df)
        assert "S3" in result["signature"].values
        assert "S4" in result["signature"].values

    def test_comma_separated_explodes_to_multiple_rows(self, sample_df):
        result = expand_signatures(sample_df)
        supp_rows = result[result["incident_id"] == "SUPP-S3-001"]
        assert len(supp_rows) == 2
        assert set(supp_rows["signature"]) == {"S3", "S5"}

    def test_filters_out_unknown_signatures(self):
        df = pd.DataFrame({
            "incident_id": ["1"],
            "signatures": ["S1,S9,UNKNOWN"],
            "annotation_confidence": [0.8],
        })
        result = expand_signatures(df)
        assert set(result["signature"]) == {"S1"}

    def test_empty_dataframe_returns_empty(self):
        df = pd.DataFrame(columns=["incident_id", "signatures", "annotation_confidence"])
        result = expand_signatures(df)
        assert result.empty

    def test_output_columns_are_correct(self, sample_df):
        result = expand_signatures(sample_df)
        assert set(result.columns) == {"incident_id", "signature", "annotation_confidence"}

    def test_signatures_normalized_to_uppercase(self):
        df = pd.DataFrame({
            "incident_id": ["1"],
            "signatures": ["s1,s2"],
            "annotation_confidence": [0.8],
        })
        result = expand_signatures(df)
        assert set(result["signature"]) == {"S1", "S2"}

    def test_whitespace_stripped_from_signatures(self):
        df = pd.DataFrame({
            "incident_id": ["1"],
            "signatures": [" S1 , S2 "],
            "annotation_confidence": [0.8],
        })
        result = expand_signatures(df)
        assert set(result["signature"]) == {"S1", "S2"}


# ── compute_gap_table ──────────────────────────────────────────────────────────

class TestComputeGapTable:
    def test_returns_all_8_signatures(self, sample_df):
        exploded = expand_signatures(sample_df)
        gap_table = compute_gap_table(exploded, target=40)
        assert len(gap_table) == 8
        assert [r["signature"] for r in gap_table] == ALL_SIGNATURES

    def test_on_track_status_at_90_percent(self):
        rows = [{"incident_id": str(i), "signature": "S1",
                 "annotation_confidence": 0.8} for i in range(36)]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s1 = next(r for r in gap_table if r["signature"] == "S1")
        assert s1["status"] == "ON_TRACK"
        assert s1["count"] == 36
        assert s1["gap"] == 4

    def test_at_risk_status_at_60_to_89_percent(self):
        rows = [{"incident_id": str(i), "signature": "S1",
                 "annotation_confidence": 0.8} for i in range(25)]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s1 = next(r for r in gap_table if r["signature"] == "S1")
        assert s1["status"] == "AT_RISK"

    def test_needs_supplement_status_below_60_percent(self):
        rows = [{"incident_id": str(i), "signature": "S4",
                 "annotation_confidence": 0.7} for i in range(5)]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s4 = next(r for r in gap_table if r["signature"] == "S4")
        assert s4["status"] == "NEEDS_SUPPLEMENT"
        assert s4["gap"] == 35
        assert s4["count"] == 5

    def test_missing_signature_shows_zero_count_and_full_gap(self):
        rows = [{"incident_id": str(i), "signature": "S1",
                 "annotation_confidence": 0.8} for i in range(10)]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s2 = next(r for r in gap_table if r["signature"] == "S2")
        assert s2["count"] == 0
        assert s2["gap"] == 40
        assert s2["status"] == "NEEDS_SUPPLEMENT"

    def test_gap_is_zero_when_target_met_or_exceeded(self):
        rows = [{"incident_id": str(i), "signature": "S1",
                 "annotation_confidence": 0.9} for i in range(50)]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s1 = next(r for r in gap_table if r["signature"] == "S1")
        assert s1["gap"] == 0
        assert s1["count"] == 50

    def test_empty_exploded_df_all_zeros(self):
        df = pd.DataFrame(columns=["incident_id", "signature", "annotation_confidence"])
        gap_table = compute_gap_table(df, target=40)
        assert all(r["count"] == 0 for r in gap_table)
        assert all(r["gap"] == 40 for r in gap_table)

    def test_pct_complete_calculation(self):
        rows = [{"incident_id": str(i), "signature": "S1",
                 "annotation_confidence": 0.8} for i in range(20)]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s1 = next(r for r in gap_table if r["signature"] == "S1")
        assert s1["pct_complete"] == pytest.approx(50.0)

    def test_deduplication_counts_unique_incident_ids(self):
        # Same incident appears twice with same sig — should count as 1
        rows = [
            {"incident_id": "1", "signature": "S1", "annotation_confidence": 0.8},
            {"incident_id": "1", "signature": "S1", "annotation_confidence": 0.9},
        ]
        df = pd.DataFrame(rows)
        gap_table = compute_gap_table(df, target=40)
        s1 = next(r for r in gap_table if r["signature"] == "S1")
        assert s1["count"] == 1

    def test_target_is_preserved_in_each_row(self):
        df = pd.DataFrame(columns=["incident_id", "signature", "annotation_confidence"])
        gap_table = compute_gap_table(df, target=35)
        assert all(r["target"] == 35 for r in gap_table)


# ── to_json_output ─────────────────────────────────────────────────────────────

class TestToJsonOutput:
    def test_output_has_required_keys(self, sample_df):
        exploded = expand_signatures(sample_df)
        gap_table = compute_gap_table(exploded, target=40)
        result = to_json_output(gap_table, total_unique=3, csv_files=["a.csv"])
        for key in ("signatures", "total_unique_incidents", "csv_files", "generated_at"):
            assert key in result

    def test_signatures_list_has_8_items(self, sample_df):
        exploded = expand_signatures(sample_df)
        gap_table = compute_gap_table(exploded, target=40)
        result = to_json_output(gap_table, total_unique=3, csv_files=[])
        assert len(result["signatures"]) == 8

    def test_is_json_serializable(self, sample_df):
        exploded = expand_signatures(sample_df)
        gap_table = compute_gap_table(exploded, target=40)
        result = to_json_output(gap_table, total_unique=3, csv_files=["a.csv"])
        parsed = json.loads(json.dumps(result))
        assert parsed["total_unique_incidents"] == 3

    def test_csv_files_reduced_to_basename(self):
        df = pd.DataFrame(columns=["incident_id", "signature", "annotation_confidence"])
        gap_table = compute_gap_table(df, target=40)
        result = to_json_output(
            gap_table, total_unique=0,
            csv_files=["/full/path/to/data.csv", "/another/path/more.csv"]
        )
        assert result["csv_files"] == ["data.csv", "more.csv"]

    def test_total_unique_incidents_reflected(self):
        df = pd.DataFrame(columns=["incident_id", "signature", "annotation_confidence"])
        gap_table = compute_gap_table(df, target=40)
        result = to_json_output(gap_table, total_unique=42, csv_files=[])
        assert result["total_unique_incidents"] == 42
