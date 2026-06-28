package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"aletheia-telemetry-gw/pkg/middleware"
)

func main() {
	// Parse port from environment variable, default to 8080 (Cloud Run spec)
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// Initialize Aletheia Scorer Configuration from env variables (Section 5.1 checklist)
	cfg := middleware.Config{
		ProjectID:     os.Getenv("BQ_PROJECT"), // matches standard Cloud Run env variables
		DatasetID:     os.Getenv("BQ_DATASET"),
		TableID:       os.Getenv("BQ_TABLE"),
		Credentials:   os.Getenv("BQ_CREDENTIALS"),
		RedisAddr:     os.Getenv("REDIS_ADDR"),
		BatchSize:     100,
		FlushInterval: 5 * time.Second,
	}
	if cfg.DatasetID == "" {
		cfg.DatasetID = "aletheia"
	}
	if cfg.TableID == "" {
		cfg.TableID = "detection_events"
	}

	telemetryMiddleware, err := middleware.NewAletheiaMiddleware(cfg)
	if err != nil {
		log.Fatalf("Failed to initialize Aletheia telemetry: %v", err)
	}
	defer func() {
		log.Println("Shutting down telemetry scorer service...")
		if err := telemetryMiddleware.Close(); err != nil {
			log.Printf("Error closing telemetry scorer: %v", err)
		}
	}()

	mux := http.NewServeMux()

	// 1. Health check endpoint (Section 4.4 contract: GET /healthz returns 204 No Content)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			w.WriteHeader(http.StatusNoContent) // 204 No Content
			return
		}
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
	})

	// 2. Cloud Run push scoring endpoint (Section 4.4 contract: POST /score)
	mux.HandleFunc("/score", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}

		var scoreReq middleware.ScoringRequest
		decoder := json.NewDecoder(r.Body)
		if err := decoder.Decode(&scoreReq); err != nil {
			log.Printf("[Scorer] Error decoding scoring request: %v", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			_, _ = w.Write([]byte(`{"error":"Invalid request schema"}`))
			return
		}

		// Fill in default values if empty
		if scoreReq.RequestID == "" {
			scoreReq.RequestID = middleware.GenerateUUID()
		}
		if scoreReq.ReceivedAt.IsZero() {
			scoreReq.ReceivedAt = time.Now()
		}

		// Run scorers (Tier 1 checks, session context checks, database writes)
		response := telemetryMiddleware.ScoreRequest(scoreReq)

		// Return 200 OK + ScoringResponse
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		if err := json.NewEncoder(w).Encode(response); err != nil {
			log.Printf("[Scorer] Error encoding scoring response: %v", err)
		}
	})

	server := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Server runner and graceful shutdown orchestrator
	go func() {
		log.Printf("Starting Aletheia Cloud Run Scorer Service on port %s", port)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("Listen and serve error: %v", err)
		}
	}()

	// Listen for SIGINT / SIGTERM signals for graceful termination (critical for Google Cloud Run scale-to-zero)
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	<-stop
	log.Println("Received shutdown signal, terminating server gracefully...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("HTTP server shutdown error: %v", err)
	}

	log.Println("Aletheia Cloud Run Scorer stopped successfully.")
}
