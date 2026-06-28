package bqschema

import (
	"math"
	"testing"
	"time"

	"cloud.google.com/go/civil"
)

func TestFormatDateTime(t *testing.T) {
	tm := time.Date(2026, 6, 28, 11, 49, 51, 123456000, time.UTC)
	expected := "2026-06-28 11:49:51.123456"
	actual := FormatDateTime(tm)
	if actual != expected {
		t.Errorf("FormatDateTime failed: expected %q, got %q", expected, actual)
	}
}

func TestFormatTimestamp(t *testing.T) {
	tm := time.Date(2026, 6, 28, 11, 49, 51, 123456000, time.UTC)
	expected := "2026-06-28T11:49:51.123456Z"
	actual := FormatTimestamp(tm)
	if actual != expected {
		t.Errorf("FormatTimestamp failed: expected %q, got %q", expected, actual)
	}
}

func TestValidateColumnName(t *testing.T) {
	validNames := []string{"request_id", "session_id", "s1_detected", "_metric_name", "A123_bc"}
	for _, name := range validNames {
		if err := ValidateColumnName(name); err != nil {
			t.Errorf("expected %q to be valid column name, got error: %v", name, err)
		}
	}

	invalidNames := []string{"", "123request", "request-id", "session$id", "invalid.dot"}
	for _, name := range invalidNames {
		if err := ValidateColumnName(name); err == nil {
			t.Errorf("expected %q to be invalid column name, but no error was returned", name)
		}
	}
}

func TestValidateEventRow(t *testing.T) {
	sessID := "sess-456"
	modelVer := "v1"
	latency := int64(12)

	row := DetectionEventRow{
		EventID:          "evt-123",
		RequestID:        "req-123",
		SessionID:        &sessID,
		OrgID:            "org-123",
		APIKeyPrefix:     "sk-123",
		ModelID:          "gpt-4o",
		ModelProvider:    "openai",
		ModelVersion:     &modelVer,
		SignatureID:      "S1",
		SignatureVersion: "v1.0.0",
		Failed:           false,
		Confidence:       0.15,
		Reason:           "No confidence language detected",
		Signals:          `{"hedged": true}`,
		LatencyMs:        &latency,
		Layer:            "async",
		ScorerSource:     "runtime_keywords",
		ScoredAt:         time.Now(),
		PartitionDate:    civil.DateOf(time.Now()),
	}

	if err := ValidateEventRow(&row); err != nil {
		t.Errorf("expected valid row to pass validation, got: %v", err)
	}

	// Test invalid float value
	invalidRow := row
	invalidRow.Confidence = math.NaN()
	if err := ValidateEventRow(&invalidRow); err == nil {
		t.Error("expected error for NaN float value, got nil")
	}

	// Test invalid JSON in signals
	invalidJSONRow := row
	invalidJSONRow.Signals = `{invalid_json}`
	if err := ValidateEventRow(&invalidJSONRow); err == nil {
		t.Error("expected error for invalid JSON in signals, got nil")
	}
}
