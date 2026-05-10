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

// TestGoflow2Decode regression-locks convertGoflow2Records: feed the
// production newGoflow2Decode() the exact NFv9 template + data bytes from
// goflow2/v2 v2.2.6's own decoder unit test, and assert we return at least
// one FlowRecord with non-empty SrcIP. If convertGoflow2Records ever stops
// extracting fields from the v2 ProducerMessage (or the typed assertion
// fails), this test fails — the path is hot enough that a silent regression
// would lose all flow data.
//
// The template + first data record bytes below are lifted directly from
// goflow2/v2's TestDecodeNetFlowV9 — one template flowset announcing
// template id 260 with 23 fields, followed by NFv9 data flowsets keyed
// to that template. SrcAddr in the first record decodes to 198.38.120.222.
func TestGoflow2Decode(t *testing.T) {
	// First send: template-only packet — primes the per-sampler template
	// store. Decode returns 0 FlowRecords (template flowsets carry no data).
	templatePkt := []byte{
		0x00, 0x09, 0x00, 0x01, 0xb3, 0xbf, 0xf6, 0x83, 0x61, 0x8a, 0xa3, 0xa8, 0x32, 0x01, 0xee, 0x98,
		0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x64, 0x01, 0x04, 0x00, 0x17, 0x00, 0x02, 0x00, 0x04,
		0x00, 0x01, 0x00, 0x04, 0x00, 0x08, 0x00, 0x04, 0x00, 0x0c, 0x00, 0x04, 0x00, 0x0a, 0x00, 0x04,
		0x00, 0x0e, 0x00, 0x04, 0x00, 0x15, 0x00, 0x04, 0x00, 0x16, 0x00, 0x04, 0x00, 0x07, 0x00, 0x02,
		0x00, 0x0b, 0x00, 0x02, 0x00, 0x10, 0x00, 0x04, 0x00, 0x11, 0x00, 0x04, 0x00, 0x12, 0x00, 0x04,
		0x00, 0x09, 0x00, 0x01, 0x00, 0x0d, 0x00, 0x01, 0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x00, 0x01,
		0x00, 0x05, 0x00, 0x01, 0x00, 0x3d, 0x00, 0x01, 0x00, 0x59, 0x00, 0x01, 0x00, 0x30, 0x00, 0x02,
		0x00, 0xea, 0x00, 0x04, 0x00, 0xeb, 0x00, 0x04,
	}
	// Second send: same source, NFv9 data packet using template 260.
	// 94 bytes total = 20-byte NFv9 header + 4-byte FlowSet header (id=260,
	// length=1372 advertised) + one full 70-byte record. The template
	// requires 70 bytes per record (sum of field lengths), so anything less
	// yields zero parsed records — goflow2's own unit test happens to use
	// `data[:89]` as a truncation but its `data` array extends much further;
	// here we hand-craft exactly enough bytes to produce one complete record
	// with SrcIP populated.
	dataPkt := []byte{
		// NFv9 header (20 bytes): version=9, count=21, sysuptime, unixsec, seqno, sourceid=256
		0x00, 0x09, 0x00, 0x15, 0xb3, 0xbf, 0xf6, 0x83, 0x61, 0x8a, 0xa3, 0xa8, 0x32, 0x01, 0xee, 0x9c,
		0x00, 0x00, 0x01, 0x00,
		// FlowSet header (4 bytes): id=260 (matches template), length=1372
		0x01, 0x04, 0x05, 0x5c,
		// Record (70 bytes per template field sizes 4+4+4+4+4+4+4+4+2+2+4+4+4+1+1+1+1+1+1+1+2+4+4):
		0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x05, 0xdc,
		0xc6, 0x26, 0x78, 0xde, 0x58, 0x79, 0xd9, 0xd0, 0x00, 0x00, 0x01, 0x62, 0x00, 0x00, 0x01, 0x30,
		0xb3, 0xbf, 0xe6, 0xf9, 0xb3, 0xbf, 0xe6, 0xf9, 0x01, 0xbb, 0x3b, 0x50, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0xfc, 0xdf, 0x00, 0x00, 0x18, 0x0e, 0x06, 0x10, 0x00, 0x00, 0x40, 0x00,
		0x01, 0x60, 0x00, 0x00, 0x02, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	}

	decode := newGoflow2Decode()

	// Template flowset — must succeed and return 0 records.
	recsT, err := decode(templatePkt, "127.0.0.1:9999")
	require.NoError(t, err)
	require.Empty(t, recsT, "template flowset should yield 0 FlowRecords")

	// Data flowset — must produce at least 1 FlowRecord with non-empty SrcIP.
	recs, err := decode(dataPkt, "127.0.0.1:9999")
	require.NoError(t, err)
	require.GreaterOrEqual(t, len(recs), 1, "data flowset must yield ≥ 1 FlowRecord")
	require.NotEmpty(t, recs[0].SrcIP,
		"convertGoflow2Records must extract IPV4_SRC_ADDR (NFv9 type=8) — empty string indicates the typed assertion in convertGoflow2Records is returning nil")
	require.Equal(t, "198.38.120.222", recs[0].SrcIP,
		"first data record's IPV4_SRC_ADDR is 0xc6267 8de = 198.38.120.222")
}
