package netflow

import (
	"bytes"
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"net"
	"sync"
	"time"

	nfdecoders "github.com/netsampler/goflow2/v2/decoders/netflow"
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

// -----------------------------------------------------------------------------
// goflow2/v2 v2.2.6 production decoder
// -----------------------------------------------------------------------------
//
// API actually used (Live Discovery — RESEARCH §Pattern 4 was written before
// v2.2.6 was inspected; the canonical surface differs from the plan's guess):
//
//   - nfdecoders.CreateTemplateSystem() NetFlowTemplateSystem
//   - nfdecoders.DecodeMessageVersion(buf, templates, &nfv9, &ipfix) error
//       — handles both NFv9 and IPFIX; populates whichever packet pointer
//         matches the version field.
//   - NFv9Packet.FlowSets / IPFIXPacket.FlowSets are []interface{}; entries
//     are TemplateFlowSet, DataFlowSet, OptionsDataFlowSet, etc.
//   - DataFlowSet.Records []DataRecord; each DataRecord.Values []DataField;
//     each DataField has .Type uint16 (NFV9_FIELD_* / IPFIX_FIELD_*) and
//     .Value interface{} (almost always []byte from payload.Next(length)).
//
// Per-sampler isolation in v2.2.6 is implicit via the NetFlowTemplateSystem's
// (version, obsDomainId, templateId) keying. We share one template system
// across sampler keys because obsDomainId already partitions templates per
// exporter — but we lock the system with a mutex since the listener is the
// only goroutine calling decode and we want predictable serial decoding.

// NewGoflow2Decode is the exported wiring entry point used by the agent
// main package — internally aliases newGoflow2Decode. Splitting the export
// from the unexported constructor keeps the v2.2.6-specific implementation
// detail private while still letting cmd/infracanvas-agent build a
// production listener without leaking goflow2 types across packages.
func NewGoflow2Decode() DecodeFunc { return newGoflow2Decode() }

// newGoflow2Decode returns the production DecodeFunc backed by goflow2/v2.
// The returned closure owns one NetFlowTemplateSystem; callers keep templates
// alive across packets (RESEARCH Pitfall 3: a sampler that emits a template
// flowset once at startup must remain decodable for the whole session).
func newGoflow2Decode() DecodeFunc {
	templates := nfdecoders.CreateTemplateSystem()
	var mu sync.Mutex

	return func(packet []byte, samplerKey string) ([]FlowRecord, error) {
		mu.Lock()
		defer mu.Unlock()

		buf := bytes.NewBuffer(packet)
		var nfv9 nfdecoders.NFv9Packet
		var ipfix nfdecoders.IPFIXPacket
		if err := nfdecoders.DecodeMessageVersion(buf, templates, &nfv9, &ipfix); err != nil {
			return nil, fmt.Errorf("goflow2 decode (sampler=%s): %w", samplerKey, err)
		}

		var flowSets []interface{}
		switch {
		case nfv9.Version == 9:
			flowSets = nfv9.FlowSets
		case ipfix.Version == 10:
			flowSets = ipfix.FlowSets
		default:
			// Unknown version — DecodeMessageVersion should have errored,
			// but be defensive against future versions silently passing.
			return nil, nil
		}
		return convertGoflow2Records(flowSets), nil
	}
}

// convertGoflow2Records flattens goflow2/v2's FlowSets ([]interface{}) into
// our FlowRecord shape. Only DataFlowSet entries carry actual flow data;
// TemplateFlowSet / OptionsDataFlowSet / OptionsTemplateFlowSet are
// state-update flowsets that yield zero records.
//
// Field-type → FlowRecord mapping (NFv9 / IPFIX share these IE numbers for
// the basic 5-tuple + counters):
//
//	1   = IN_BYTES         -> FlowRecord.Bytes
//	2   = IN_PKTS          -> FlowRecord.Packets
//	4   = PROTOCOL         -> FlowRecord.Protocol
//	7   = L4_SRC_PORT      -> FlowRecord.SrcPort
//	8   = IPV4_SRC_ADDR    -> FlowRecord.SrcIP
//	11  = L4_DST_PORT      -> FlowRecord.DstPort
//	12  = IPV4_DST_ADDR    -> FlowRecord.DstIP
//	23  = OUT_BYTES        -> FlowRecord.Bytes (fallback if no IN_BYTES)
//	24  = OUT_PKTS         -> FlowRecord.Packets (fallback if no IN_PKTS)
//	27  = IPV6_SRC_ADDR    -> FlowRecord.SrcIP
//	28  = IPV6_DST_ADDR    -> FlowRecord.DstIP
//
// Values arrive as []byte (raw wire bytes); we interpret them by length.
// Unknown field types are silently skipped — additional fields can be added
// in future plans without breaking existing decoders.
func convertGoflow2Records(flowSets []interface{}) []FlowRecord {
	var out []FlowRecord
	for _, fs := range flowSets {
		dfs, ok := fs.(nfdecoders.DataFlowSet)
		if !ok {
			continue // template / options / unknown flowset
		}
		for _, rec := range dfs.Records {
			fr := decodeDataRecord(rec)
			out = append(out, fr)
		}
	}
	return out
}

// decodeDataRecord reads one goflow2 DataRecord into a FlowRecord.
func decodeDataRecord(rec nfdecoders.DataRecord) FlowRecord {
	var fr FlowRecord
	for _, f := range rec.Values {
		raw, ok := f.Value.([]byte)
		if !ok || len(raw) == 0 {
			continue
		}
		switch f.Type {
		case 8: // IPV4_SRC_ADDR
			if len(raw) == 4 {
				fr.SrcIP = net.IP(raw).String()
			}
		case 12: // IPV4_DST_ADDR
			if len(raw) == 4 {
				fr.DstIP = net.IP(raw).String()
			}
		case 27: // IPV6_SRC_ADDR
			if len(raw) == 16 {
				fr.SrcIP = net.IP(raw).String()
			}
		case 28: // IPV6_DST_ADDR
			if len(raw) == 16 {
				fr.DstIP = net.IP(raw).String()
			}
		case 7: // L4_SRC_PORT
			fr.SrcPort = int(readUint(raw))
		case 11: // L4_DST_PORT
			fr.DstPort = int(readUint(raw))
		case 4: // PROTOCOL
			fr.Protocol = int(readUint(raw))
		case 1: // IN_BYTES
			fr.Bytes = int(readUint(raw))
		case 2: // IN_PKTS
			fr.Packets = int(readUint(raw))
		case 23: // OUT_BYTES — fallback when IN_BYTES absent
			if fr.Bytes == 0 {
				fr.Bytes = int(readUint(raw))
			}
		case 24: // OUT_PKTS — fallback when IN_PKTS absent
			if fr.Packets == 0 {
				fr.Packets = int(readUint(raw))
			}
		}
	}
	return fr
}

// readUint big-endian-decodes 1/2/4/8-byte raw NetFlow integer fields.
// goflow2 emits the wire bytes verbatim (DataField.Value = payload.Next(len));
// we widen everything into uint64 and the caller narrows.
func readUint(raw []byte) uint64 {
	switch len(raw) {
	case 1:
		return uint64(raw[0])
	case 2:
		return uint64(binary.BigEndian.Uint16(raw))
	case 4:
		return uint64(binary.BigEndian.Uint32(raw))
	case 8:
		return binary.BigEndian.Uint64(raw)
	}
	// Non-power-of-two lengths are NetFlow-illegal for these fields; treat
	// as zero rather than panicking on the listener hot path.
	return 0
}
