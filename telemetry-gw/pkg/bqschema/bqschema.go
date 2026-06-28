package bqschema

import (
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"regexp"
	"time"

	"cloud.google.com/go/civil"
)

// Column regex representing BigQuery field naming rules:
// Case-sensitive, alphanumeric and underscores, starting with a letter or underscore.
var bqColumnRegex = regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]{0,299}$`)

// DetectionEventRow represents the authoritative BigQuery schema for detection_events (Section 4.1).
type DetectionEventRow struct {
	EventID          string     `bigquery:"event_id"`
	RequestID        string     `bigquery:"request_id"`
	SessionID        *string    `bigquery:"session_id"`
	OrgID            string     `bigquery:"org_id"`
	APIKeyPrefix     string     `bigquery:"api_key_prefix"`
	ModelID          string     `bigquery:"model_id"`
	ModelProvider    string     `bigquery:"model_provider"`
	ModelVersion     *string    `bigquery:"model_version"`
	SignatureID      string     `bigquery:"signature_id"`
	SignatureVersion string     `bigquery:"signature_version"`
	Failed           bool       `bigquery:"failed"`
	Confidence       float64    `bigquery:"confidence"`
	Reason           string     `bigquery:"reason"`
	Signals          string     `bigquery:"signals"` // Stored as a JSON string (BigQuery JSON type)
	LatencyMs        *int64     `bigquery:"latency_ms"`
	PromptTokens     *int64     `bigquery:"prompt_tokens"`
	ResponseTokens   *int64     `bigquery:"response_tokens"`
	TotalTokens      *int64     `bigquery:"total_tokens"`
	Layer            string     `bigquery:"layer"`
	ScorerSource     string     `bigquery:"scorer_source"`
	ScoredAt         time.Time  `bigquery:"scored_at"`
	PartitionDate    civil.Date `bigquery:"partition_date"`
}

// ValidateColumnName validates that a column name adheres to BigQuery specifications.
func ValidateColumnName(name string) error {
	if name == "" {
		return errors.New("column name cannot be empty")
	}
	if !bqColumnRegex.MatchString(name) {
		return fmt.Errorf("invalid column name %q: must match regex ^[a-zA-Z_][a-zA-Z0-9_]{0,299}$", name)
	}
	return nil
}

// ValidateEventRow validates the values of a DetectionEventRow struct to avoid insertion formatting errors.
func ValidateEventRow(row *DetectionEventRow) error {
	if row.EventID == "" {
		return errors.New("event_id cannot be empty")
	}
	if row.RequestID == "" {
		return errors.New("request_id cannot be empty")
	}
	if row.OrgID == "" {
		return errors.New("org_id cannot be empty")
	}
	if row.ModelID == "" {
		return errors.New("model_id cannot be empty")
	}
	if row.SignatureID == "" {
		return errors.New("signature_id cannot be empty")
	}
	if row.ScoredAt.IsZero() {
		return errors.New("scored_at timestamp cannot be zero")
	}
	if row.PartitionDate.IsZero() {
		return errors.New("partition_date cannot be zero")
	}

	// Validate floats for NaN or Inf
	if math.IsNaN(row.Confidence) || math.IsInf(row.Confidence, 0) {
		return fmt.Errorf("confidence value cannot be NaN or Inf")
	}

	// Check JSON format of Signals field
	if row.Signals != "" {
		var js json.RawMessage
		if err := json.Unmarshal([]byte(row.Signals), &js); err != nil {
			return fmt.Errorf("signals field contains invalid JSON: %w", err)
		}
	}

	return nil
}

// FormatDateTime formats a time.Time to the exact format required by BigQuery's DATETIME field.
func FormatDateTime(t time.Time) string {
	return t.UTC().Format("2006-01-02 15:04:05.000000")
}

// FormatTimestamp formats a time.Time to the format expected by BigQuery's TIMESTAMP field.
func FormatTimestamp(t time.Time) string {
	return t.UTC().Format(time.RFC3339Nano)
}

// ValidateFieldName checks field constraints dynamically.
func ValidateFieldName(name string) error {
	return ValidateColumnName(name)
}
