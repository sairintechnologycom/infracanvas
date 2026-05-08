package netflow

import (
	"encoding/json"
	"sync"
	"testing"

	"github.com/stretchr/testify/require"
)

func sampleRecord(i int) FlowRecord {
	return FlowRecord{
		SrcIP: "10.0.0.1", DstIP: "10.0.0.2",
		SrcPort: 1000 + i, DstPort: 80,
		Protocol: 6, Bytes: 1500, Packets: 1,
	}
}

func TestRingBuffer_AppendAndDrain(t *testing.T) {
	b := NewRingBuffer(10)
	b.Append([]FlowRecord{sampleRecord(0), sampleRecord(1), sampleRecord(2)})
	require.Equal(t, 3, b.Len())
	out := b.Drain()
	require.Len(t, out, 3)
	require.Equal(t, 0, b.Len())
	require.Equal(t, 1000, out[0].SrcPort)
	require.Equal(t, 1001, out[1].SrcPort)
	require.Equal(t, 1002, out[2].SrcPort)
}

func TestRingBuffer_Overflow(t *testing.T) {
	b := NewRingBuffer(5)
	var recs []FlowRecord
	for i := 0; i < 8; i++ {
		recs = append(recs, sampleRecord(i))
	}
	b.Append(recs)
	require.Equal(t, 5, b.Len())
	out := b.Drain()
	require.Len(t, out, 5)
	// Last 5 records survived — first 3 overwritten in circular order.
	require.Equal(t, 1003, out[0].SrcPort) // index 3
	require.Equal(t, 1007, out[4].SrcPort) // index 7
}

func TestRingBuffer_DrainOrder(t *testing.T) {
	b := NewRingBuffer(10)
	var recs []FlowRecord
	for i := 0; i < 5; i++ {
		recs = append(recs, sampleRecord(i))
	}
	b.Append(recs)
	out := b.Drain()
	require.Len(t, out, 5)
	for i, r := range out {
		require.Equal(t, 1000+i, r.SrcPort, "drain must preserve append order at index %d", i)
	}
}

func TestRingBuffer_Empty(t *testing.T) {
	b := NewRingBuffer(5)
	out := b.Drain()
	require.NotNil(t, out, "empty Drain must return non-nil slice")
	require.Len(t, out, 0)
}

// -race must catch any concurrent access bugs.
func TestRingBuffer_ConcurrentAppend(t *testing.T) {
	b := NewRingBuffer(2000)
	var wg sync.WaitGroup
	for g := 0; g < 10; g++ {
		wg.Add(1)
		go func(g int) {
			defer wg.Done()
			for i := 0; i < 100; i++ {
				b.Append([]FlowRecord{sampleRecord(g*100 + i)})
			}
		}(g)
	}
	wg.Wait()
	// 10 * 100 = 1000 records appended; capacity 2000 holds them all.
	require.Equal(t, 1000, b.Len())
	out := b.Drain()
	require.Len(t, out, 1000)
	require.Equal(t, 0, b.Len())
}

// TestRingBuffer alias matches the verify-command from 10-VALIDATION.md.
func TestRingBuffer(t *testing.T) { TestRingBuffer_AppendAndDrain(t) }

func TestFlowRecordJSONShape(t *testing.T) {
	r := FlowRecord{
		SrcIP: "10.0.0.1", DstIP: "10.0.0.2",
		SrcPort: 1024, DstPort: 80,
		Protocol: 6, Bytes: 1500, Packets: 1,
	}
	b, err := json.Marshal(r)
	require.NoError(t, err)
	s := string(b)
	require.Contains(t, s, `"src_ip":"10.0.0.1"`)
	require.Contains(t, s, `"dst_ip":"10.0.0.2"`)
	require.Contains(t, s, `"src_port":1024`)
	require.Contains(t, s, `"dst_port":80`)
	require.Contains(t, s, `"protocol":6`)
	require.Contains(t, s, `"bytes":1500`)
	require.Contains(t, s, `"packets":1`)
}
