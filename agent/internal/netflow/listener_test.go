package netflow

import (
	"context"
	"errors"
	"net"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap/zaptest"
)

// randomLocalUDP returns a free UDP address on loopback for test isolation.
func randomLocalUDP(t *testing.T) string {
	t.Helper()
	c, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.IPv4(127, 0, 0, 1), Port: 0})
	require.NoError(t, err)
	addr := c.LocalAddr().String()
	require.NoError(t, c.Close())
	return addr
}

// sendUDP fires one packet at addr from a fresh source socket.
func sendUDP(t *testing.T, addr string, payload []byte) net.Addr {
	t.Helper()
	raddr, err := net.ResolveUDPAddr("udp", addr)
	require.NoError(t, err)
	c, err := net.DialUDP("udp", nil, raddr)
	require.NoError(t, err)
	defer func() { _ = c.Close() }()
	_, err = c.Write(payload)
	require.NoError(t, err)
	return c.LocalAddr()
}

func TestNetFlowListener_Happy(t *testing.T) {
	rb := NewRingBuffer(100)
	addr := randomLocalUDP(t)
	decode := func(p []byte, key string) ([]FlowRecord, error) {
		return []FlowRecord{
			{SrcIP: "10.0.0.1", DstIP: "10.0.0.2", SrcPort: 1234, DstPort: 80, Protocol: 6, Bytes: 1500, Packets: 1},
			{SrcIP: "10.0.0.3", DstIP: "10.0.0.4", SrcPort: 5678, DstPort: 443, Protocol: 6, Bytes: 800, Packets: 1},
		}, nil
	}
	l := NewListener(addr, rb, zaptest.NewLogger(t), decode)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- l.Run(ctx) }()

	time.Sleep(50 * time.Millisecond) // listener bind window
	sendUDP(t, addr, []byte("dummy-packet"))
	// Allow listener loop to read + decode + Append.
	require.Eventually(t, func() bool { return rb.Len() >= 2 }, 2*time.Second, 20*time.Millisecond)

	cancel()
	select {
	case err := <-done:
		require.NoError(t, err)
	case <-time.After(2 * time.Second):
		t.Fatal("Run did not return after ctx cancel")
	}
}

func TestNetFlowListener_DecodeErrorContinues(t *testing.T) {
	rb := NewRingBuffer(100)
	addr := randomLocalUDP(t)
	var calls int32
	decode := func(p []byte, key string) ([]FlowRecord, error) {
		n := atomic.AddInt32(&calls, 1)
		if n == 1 {
			return nil, errors.New("malformed packet")
		}
		return []FlowRecord{
			{SrcIP: "10.0.0.5", DstIP: "10.0.0.6", SrcPort: 1, DstPort: 2, Protocol: 17, Bytes: 100, Packets: 1},
		}, nil
	}
	l := NewListener(addr, rb, zaptest.NewLogger(t), decode)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = l.Run(ctx) }()
	time.Sleep(50 * time.Millisecond)

	sendUDP(t, addr, []byte("bad"))
	sendUDP(t, addr, []byte("good"))

	require.Eventually(t, func() bool { return rb.Len() >= 1 }, 2*time.Second, 20*time.Millisecond)
	require.GreaterOrEqual(t, int(atomic.LoadInt32(&calls)), 2,
		"decoder must be called at least twice — error did not crash the loop")
}

func TestNetFlowListener_ContextCancel(t *testing.T) {
	rb := NewRingBuffer(10)
	addr := randomLocalUDP(t)
	decode := func(p []byte, key string) ([]FlowRecord, error) { return nil, nil }
	l := NewListener(addr, rb, zaptest.NewLogger(t), decode)

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- l.Run(ctx) }()
	time.Sleep(50 * time.Millisecond)
	cancel()
	select {
	case err := <-done:
		require.NoError(t, err)
	case <-time.After(2 * time.Second):
		t.Fatal("Run did not return within 2s after ctx cancel")
	}
}

func TestNetFlowListener_TemplatePerSampler(t *testing.T) {
	rb := NewRingBuffer(100)
	addr := randomLocalUDP(t)
	var keysMu sync.Mutex
	keys := make(map[string]bool)
	decode := func(p []byte, samplerKey string) ([]FlowRecord, error) {
		keysMu.Lock()
		keys[samplerKey] = true
		keysMu.Unlock()
		return []FlowRecord{{SrcIP: samplerKey, DstIP: "x", Protocol: 6, Bytes: 1, Packets: 1}}, nil
	}
	l := NewListener(addr, rb, zaptest.NewLogger(t), decode)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = l.Run(ctx) }()
	time.Sleep(50 * time.Millisecond)

	// Two different source sockets => two different sampler keys.
	sendUDP(t, addr, []byte("a"))
	sendUDP(t, addr, []byte("b"))

	require.Eventually(t, func() bool {
		keysMu.Lock()
		defer keysMu.Unlock()
		return len(keys) >= 2
	}, 2*time.Second, 20*time.Millisecond, "decoder should see at least 2 distinct sampler keys")
}

// TestNetFlowListener alias matches 10-VALIDATION.md verify command.
func TestNetFlowListener(t *testing.T) { TestNetFlowListener_Happy(t) }
