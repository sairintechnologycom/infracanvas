// Package push owns the agent's HTTP push client.
//
// D-07 contract: 3 attempts (1 initial + 2 retries), linear backoff 2s/4s,
// drop-and-continue after exhaustion (logged at WARN; the daemon ticker
// fires again at the next interval so the system self-heals once the
// backend recovers). Non-retryable failures (4xx auth/validation) bubble
// back as errors so the caller can log + investigate.
package push

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"go.uber.org/zap"
)

const (
	defaultRequestTimeout = 15 * time.Second
	routesPath            = "/v1/agent/routes"
	flowsPath             = "/v1/agent/flows"
)

// BackoffFunc returns the wait duration BEFORE attempt N (1-indexed).
// Production wiring uses linearBackoff (2s, 4s); tests inject a fast variant
// via Client.SetBackoff so the unit suite runs in well under a second.
type BackoffFunc func(attempt int) time.Duration

// linearBackoff is the locked D-07 backoff schedule:
//
//	attempt 1 -> 2s wait, attempt 2 -> 4s wait.
//
// TestPushRoutes_BackoffTiming regression-locks this against the production
// implementation (the only test that uses real timing).
func linearBackoff(attempt int) time.Duration {
	return time.Duration(attempt*2) * time.Second
}

// Client posts route and flow batches to the InfraCanvas backend.
type Client struct {
	backendURL string
	token      string
	http       *http.Client
	log        *zap.Logger
	backoff    BackoffFunc
}

// NewClient returns a push Client. backendURL is the scheme+host (no trailing
// slash needed; trimmed if present). token is the site_token loaded from
// agent.yaml; sent as `Authorization: Bearer <token>` per CONTEXT.md D-04.
// A nil log is replaced with zap.NewNop so the client is safe to use in
// tests without a configured logger.
func NewClient(backendURL, token string, log *zap.Logger) *Client {
	if log == nil {
		log = zap.NewNop()
	}
	return &Client{
		backendURL: strings.TrimRight(backendURL, "/"),
		token:      token,
		http:       &http.Client{Timeout: defaultRequestTimeout},
		log:        log,
		backoff:    linearBackoff,
	}
}

// SetBackoff replaces the production backoff with a custom one. Test seam:
// fastBackoff(50ms/100ms) lets the retry tests run in ~150ms instead of 6s.
func (c *Client) SetBackoff(b BackoffFunc) { c.backoff = b }

// PushRoutes POSTs a routes batch with retry-twice-then-drop semantics (D-07).
//
// Returns nil after 3 retried-failures: the batch is silently dropped, not
// surfaced to the daemon ticker — drops are visible only via WARN logs. This
// is intentional: the routes ticker fires every 5min; failing the daemon
// callback would leave logs noisier than the drop telemetry.
//
// Returns a non-nil error ONLY for non-retryable failures (4xx — 401/403/422)
// so the caller can surface auth/validation problems explicitly to operators.
func (c *Client) PushRoutes(ctx context.Context, p RoutesPayload) error {
	body, err := json.Marshal(p)
	if err != nil {
		return fmt.Errorf("push: marshal routes: %w", err)
	}
	return c.postWithRetry(ctx, routesPath, body, "routes",
		zap.String("site_id", p.SiteID),
		zap.String("device_host", p.DeviceHost),
		zap.Int("count", len(p.Routes)))
}

// PushFlows POSTs a flows batch. Same retry contract as PushRoutes.
func (c *Client) PushFlows(ctx context.Context, p FlowsPayload) error {
	body, err := json.Marshal(p)
	if err != nil {
		return fmt.Errorf("push: marshal flows: %w", err)
	}
	return c.postWithRetry(ctx, flowsPath, body, "flows",
		zap.String("site_id", p.SiteID),
		zap.Int("count", len(p.Flows)))
}

// postWithRetry implements the D-07 retry-twice-then-drop loop:
// transport errors and 5xx → retry; 4xx → bail out without retry; 2xx → return.
func (c *Client) postWithRetry(
	ctx context.Context,
	path string,
	body []byte,
	kind string,
	logFields ...zap.Field,
) error {
	url := c.backendURL + path
	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		if attempt > 0 {
			wait := c.backoff(attempt)
			select {
			case <-time.After(wait):
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		status, err := c.doPost(ctx, url, body)
		if err == nil {
			return nil // 2xx
		}
		// Auth/validation failures are non-retryable — surface immediately.
		if status == http.StatusUnauthorized || status == http.StatusForbidden ||
			status == http.StatusUnprocessableEntity {
			return err
		}
		lastErr = err
	}
	c.log.Warn("push_drop_after_retries",
		append(logFields,
			zap.String("kind", kind),
			zap.String("path", path),
			zap.Error(lastErr),
		)...)
	return nil
}

// doPost issues one POST attempt. Returns (statusCode, error). On 2xx returns
// (status, nil). On non-2xx returns (status, error including statusCode + a
// 512-byte body snippet — T-10-07-06 caps memory consumption from misbehaving
// servers). On transport error returns (0, error).
func (c *Client) doPost(ctx context.Context, url string, body []byte) (int, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return 0, fmt.Errorf("push: build request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+c.token)
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return 0, fmt.Errorf("push: do: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return resp.StatusCode, nil
	}
	var sample bytes.Buffer
	_, _ = io.CopyN(&sample, resp.Body, 512)
	return resp.StatusCode, fmt.Errorf("push: status=%d body=%s", resp.StatusCode, sample.String())
}
