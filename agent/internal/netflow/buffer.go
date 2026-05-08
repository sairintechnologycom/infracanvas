// Package netflow holds the NetFlow v9/IPFIX collector pipeline (DCA-04):
//   - FlowRecord (types.go) — wire shape shared with backend
//   - RingBuffer (buffer.go) — fixed-capacity circular store, mutex-guarded
//   - Listener (listener.go) — UDP:2055 + goflow2/v2 decoder + template cache
//
// Capacity sizing per D-07: ~5 minutes of records. Default 100,000 leaves
// headroom over typical small-to-medium DC sites (~1k flows/sec).
package netflow

import "sync"

// RingBuffer is a fixed-capacity circular store of FlowRecords.
// Once full, oldest entries are overwritten on Append. Drain returns the
// currently-held records in arrival order and resets the buffer.
type RingBuffer struct {
	mu       sync.Mutex
	data     []FlowRecord
	head     int // total appends (mod capacity gives slot)
	capacity int
}

// NewRingBuffer returns a buffer that holds up to `capacity` records.
// Caller MUST pass capacity > 0.
func NewRingBuffer(capacity int) *RingBuffer {
	if capacity <= 0 {
		capacity = 1
	}
	return &RingBuffer{
		data:     make([]FlowRecord, capacity),
		capacity: capacity,
	}
}

// Append writes records to the buffer. If the buffer is full, oldest
// records are silently overwritten (circular semantics — D-07 retry-twice-
// then-drop behavior is enforced by the push client, not the buffer).
func (r *RingBuffer) Append(records []FlowRecord) {
	if len(records) == 0 {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, rec := range records {
		r.data[r.head%r.capacity] = rec
		r.head++
	}
}

// Drain returns up to capacity records in arrival order and resets state.
// Returns an empty slice (never nil) when no records have been Appended.
func (r *RingBuffer) Drain() []FlowRecord {
	r.mu.Lock()
	defer r.mu.Unlock()

	n := r.head
	if n > r.capacity {
		n = r.capacity
	}
	out := make([]FlowRecord, n)
	if n == 0 {
		r.head = 0
		return out
	}
	// Compute the starting slot for the oldest currently-held record.
	var start int
	if r.head > r.capacity {
		start = r.head % r.capacity
	}
	for i := 0; i < n; i++ {
		out[i] = r.data[(start+i)%r.capacity]
	}
	r.head = 0
	return out
}

// Len returns the number of records currently held (0..capacity).
func (r *RingBuffer) Len() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.head > r.capacity {
		return r.capacity
	}
	return r.head
}
