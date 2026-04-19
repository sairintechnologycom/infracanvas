import { useState } from 'react';
import { Network } from 'lucide-react';

const COMMAND = 'infracanvas scan ./terraform --flowmap';

export function FlowMapEmptyState() {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(COMMAND);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: non-HTTPS contexts — no-op; the command is selectable inline
    }
  };

  return (
    <div
      role="status"
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#FAFBFC',
      }}
    >
      <div
        style={{
          width: 520,
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: 12,
          boxShadow: '0 4px 16px rgba(15,23,42,0.04)',
          padding: 32,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          gap: 16,
        }}
      >
        <Network size={40} color="#94A3B8" />
        <h2 style={{ fontSize: 13, fontWeight: 600, color: '#0F172A', margin: 0 }}>
          No network topology collected yet
        </h2>
        <p
          style={{
            fontSize: 11,
            fontWeight: 500,
            color: '#475569',
            lineHeight: 1.45,
            margin: 0,
          }}
        >
          FlowMap needs cloud network data. Re-run with the --flowmap flag to collect AWS TGW, VPC
          routes, Azure vWAN, vNet peering, and ExpressRoute state.
        </p>
        <div
          style={{
            width: '100%',
            background: '#0F172A',
            color: '#E2E8F0',
            padding: '8px 16px',
            borderRadius: 6,
            border: '1px solid #1E293B',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            boxSizing: 'border-box',
          }}
        >
          <code style={{ userSelect: 'all' }}>{COMMAND}</code>
          <button
            onClick={copy}
            style={{
              background: 'transparent',
              border: '1px solid #334155',
              color: copied ? '#22C55E' : '#94A3B8',
              fontSize: 10,
              textTransform: 'uppercase',
              padding: '2px 8px',
              borderRadius: 4,
              cursor: 'pointer',
              transition: 'border-color 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#3B82F6';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#334155';
            }}
          >
            {copied ? 'Copied ✓' : 'Copy'}
          </button>
        </div>
        <p
          style={{
            fontSize: 11,
            fontWeight: 500,
            color: '#64748B',
            lineHeight: 1.45,
            margin: 0,
          }}
        >
          Cloud credentials follow the same chain as --shadow. Missing credentials skip that cloud
          with a warning — no hard fail.
        </p>
        <a
          href="https://infracanvas.dev/docs/flowmap"
          style={{
            fontSize: 11,
            fontWeight: 500,
            color: '#3B82F6',
            textDecoration: 'none',
          }}
          target="_blank"
          rel="noopener noreferrer"
        >
          Read the FlowMap docs →
        </a>
        <span
          style={{
            position: 'absolute',
            bottom: 12,
            right: 12,
            fontSize: 10,
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: 4,
            background: 'rgba(217,119,6,0.12)',
            color: '#D97706',
            border: '1px solid rgba(217,119,6,0.3)',
          }}
        >
          Beta · free during preview
        </span>
      </div>
    </div>
  );
}

export default FlowMapEmptyState;
