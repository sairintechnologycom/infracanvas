# InfraCanvas DC Agent — local dev convenience targets.
# All commands match the CI workflow (.github/workflows/ci.yml::test-agent)
# so what passes locally also passes in CI.

.PHONY: test test-race test-short build vet lint check ci

# Default: fast deterministic test run for tight loops.
test:
	go test ./... -count=1 -timeout 60s

# Full -race mode (matches CI; slower).
test-race:
	go test ./... -race -count=1 -timeout 180s

# Skip the slow backoff timing test (TestPushRoutes_BackoffTiming) for
# quick feedback — useful when iterating on push client code.
test-short:
	go test ./... -short -count=1 -timeout 60s

vet:
	go vet ./...

# Local cross-compile smoke — same flags CI uses for release.yml.
build:
	CGO_ENABLED=0 go build -ldflags="-s -w -X main.version=dev" \
	    -o ../dist/infracanvas-agent ./cmd/infracanvas-agent

# Mirrors CI test-agent job exactly (Plan 10-08).
ci: vet test-race build

# `make check` is a friendly alias.
check: ci
