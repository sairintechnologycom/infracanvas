package netflow

import (
	"context"
	"errors"
	"fmt"
	"net"
	"sync"
	"time"

	"go.uber.org/zap"
)

const (
	// DefaultUDPAddr is the standard NetFlow v9/IPFIX listening port.
	DefaultUDPAddr = ":2055"
	// udpReadBuf is sized for jumbo-frame-tolerant NetFlow packets.
	udpReadBuf = 9000
)

// DecodeFunc is the test seam for the goflow2 decoder. Production wires
// newGoflow2Decode (below). Tests inject a deterministic stub.
//
// samplerKey is addr.String() — used to scope the per-sampler template cache.
// The function returns the FlowRecords parsed from this packet (may be empty
// if the packet was a template flowset that updates state but yields no data).
type DecodeFunc func(packet []byte, samplerKey string) ([]FlowRecord, error)

// Listener owns the UDP socket and decode loop.
type Listener struct {
	addr   string
	buf    *RingBuffer
	log    *zap.Logger
	decode DecodeFunc

	// Template cache lifetime: per-process. Per-sampler isolation handled by DecodeFunc.
}

// NewListener returns a Listener bound to addr (":2055" if empty) writing into buf.
// Production wiring: pass newGoflow2Decode() as decode.
func NewListener(addr string, buf *RingBuffer, log *zap.Logger, decode DecodeFunc) *Listener {
	if addr == "" {
		addr = DefaultUDPAddr
	}
	if log == nil {
		log = zap.NewNop()
	}
	return &Listener{addr: addr, buf: buf, log: log, decode: decode}
}

// Run binds the UDP socket and reads until ctx is cancelled.
// Decode errors are logged at WARN and the loop continues (T-10-dos mitigation).
func (l *Listener) Run(ctx context.Context) error {
	udpAddr, err := net.ResolveUDPAddr("udp", l.addr)
	if err != nil {
		return fmt.Errorf("netflow: resolve %s: %w", l.addr, err)
	}
	conn, err := net.ListenUDP("udp", udpAddr)
	if err != nil {
		return fmt.Errorf("netflow: listen %s: %w", l.addr, err)
	}
	l.log.Info("netflow_listener_started", zap.String("addr", conn.LocalAddr().String()))

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		<-ctx.Done()
		_ = conn.Close()
	}()

	buf := make([]byte, udpReadBuf)
	for {
		// Set short read deadline so context cancellation is observed promptly
		// even when no traffic arrives.
		_ = conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
		n, addr, err := conn.ReadFromUDP(buf)
		if err != nil {
			if ctx.Err() != nil {
				wg.Wait()
				l.log.Info("netflow_listener_stopped")
				return nil
			}
			var ne net.Error
			if errors.As(err, &ne) && ne.Timeout() {
				continue
			}
			// Non-timeout, non-shutdown error — log and keep running.
			l.log.Warn("netflow_read_error", zap.Error(err))
			continue
		}
		if n == 0 || addr == nil {
			continue
		}
		packet := make([]byte, n)
		copy(packet, buf[:n])
		samplerKey := addr.String()
		records, decErr := l.decode(packet, samplerKey)
		if decErr != nil {
			l.log.Warn("netflow_decode_error",
				zap.String("sampler", samplerKey),
				zap.Int("bytes", n),
				zap.Error(decErr))
			continue
		}
		if len(records) > 0 {
			l.buf.Append(records)
		}
	}
}

// newGoflow2Decode returns the production DecodeFunc backed by goflow2/v2's
// NetFlow v9/IPFIX decoder + a per-sampler template cache. Plan 10-07 will
// implement this against the actual goflow2/v2 v2.2.6 API; for now it is a
// stub that returns an "unimplemented" error so referencing it from main.go
// surfaces the missing wire-up at runtime rather than at compile time.
//
//nolint:unused // wired in plan 10-07
func newGoflow2Decode() DecodeFunc {
	return func(packet []byte, samplerKey string) ([]FlowRecord, error) {
		return nil, errors.New("goflow2 decoder not yet wired (plan 10-07)")
	}
}
