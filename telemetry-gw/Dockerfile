# --- Build Stage ---
FROM golang:1.21-alpine AS builder

# Set build directory
WORKDIR /app

# Copy dependency manifests
COPY go.mod ./
# Note: if go.sum is present, copy it.
# RUN go mod download (disabled for now or run after copy)

# Copy source code
COPY . .

# Download dependencies
RUN go mod download

# Build statically with optimization flags:
# -s: Omit symbols and debug info
# -w: Omit DWARF debugging information
# CGO_ENABLED=0 builds a fully self-contained static binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o telemetry-gw .

# --- Runtime Stage ---
# Using Google's minimal distroless static image for security and smallest size
FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /

# Copy the pre-compiled binary from the builder stage
COPY --from=builder /app/telemetry-gw /telemetry-gw

# Expose port (Cloud Run defaults to 8080 and injects PORT env variable)
EXPOSE 8080

# Run the web service
ENTRYPOINT ["/telemetry-gw"]
