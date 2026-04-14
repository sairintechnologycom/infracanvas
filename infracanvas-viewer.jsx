import { useState, useCallback, useMemo, useRef, useEffect } from "react";

// ─── Sample Infrastructure Data (from our scan pipeline) ─────────────────────
const INFRA_DATA = {
  score: 14,
  estimated_monthly_cost: 312,
  findings: { critical: 1, high: 5, medium: 9, info: 4 },
  resources: [
    { id: "aws_vpc.main", type: "aws_vpc", name: "main", cat: "network", icon: "🌐", group: "vpc", cost: 0, findings: [
      { id: "SEC-010", sev: "high", title: "No CloudTrail", rem: "Add aws_cloudtrail resource" },
      { id: "SEC-011", sev: "medium", title: "VPC No Flow Logs", rem: "Add aws_flow_log resource" },
    ]},
    { id: "aws_subnet.public_a", type: "aws_subnet", name: "public_a", cat: "network", icon: "🌐", group: "public", cost: 0, findings: [] },
    { id: "aws_subnet.public_b", type: "aws_subnet", name: "public_b", cat: "network", icon: "🌐", group: "public", cost: 0, findings: [] },
    { id: "aws_subnet.private_a", type: "aws_subnet", name: "private_a", cat: "network", icon: "🌐", group: "private", cost: 0, findings: [] },
    { id: "aws_subnet.private_b", type: "aws_subnet", name: "private_b", cat: "network", icon: "🌐", group: "private", cost: 0, findings: [] },
    { id: "aws_internet_gateway.main", type: "aws_internet_gateway", name: "main", cat: "network", icon: "🌐", group: "vpc", cost: 0, findings: [] },
    { id: "aws_nat_gateway.main", type: "aws_nat_gateway", name: "main", cat: "network", icon: "🌐", group: "public", cost: 33, findings: [] },
    { id: "aws_eip.nat", type: "aws_eip", name: "nat", cat: "network", icon: "🌐", group: "vpc", cost: 4, findings: [] },
    { id: "aws_security_group.web", type: "aws_security_group", name: "web", cat: "security", icon: "🛡", group: "public", cost: 0, findings: [
      { id: "SEC-004", sev: "critical", title: "SG Open to Internet", rem: "Restrict SSH cidr_blocks to specific IPs" },
    ]},
    { id: "aws_security_group.db", type: "aws_security_group", name: "db", cat: "security", icon: "🛡", group: "private", cost: 0, findings: [] },
    { id: "aws_instance.web_1", type: "aws_instance", name: "web_1", cat: "compute", icon: "🖥", group: "public", cost: 30, findings: [
      { id: "SEC-013", sev: "medium", title: "EC2 No IMDSv2", rem: 'Set metadata_options { http_tokens = "required" }' },
      { id: "SEC-022", sev: "medium", title: "EC2 Has Public IP", rem: "Use ALB/NAT instead of direct public IP" },
    ]},
    { id: "aws_instance.web_2", type: "aws_instance", name: "web_2", cat: "compute", icon: "🖥", group: "public", cost: 30, findings: [
      { id: "SEC-022", sev: "medium", title: "EC2 Has Public IP", rem: "Use ALB/NAT instead of direct public IP" },
    ]},
    { id: "aws_lb.main", type: "aws_lb", name: "main", cat: "network", icon: "⚡", group: "public", cost: 16, findings: [
      { id: "SEC-012", sev: "medium", title: "ALB Without WAF", rem: "Add aws_wafv2_web_acl and associate" },
    ]},
    { id: "aws_lb_target_group.web", type: "aws_lb_target_group", name: "web", cat: "network", icon: "🎯", group: "public", cost: 0, findings: [] },
    { id: "aws_db_instance.primary", type: "aws_db_instance", name: "primary", cat: "database", icon: "🗄", group: "private", cost: 187, findings: [
      { id: "SEC-006", sev: "high", title: "RDS Not Encrypted", rem: "Set storage_encrypted = true" },
      { id: "SEC-017", sev: "medium", title: "RDS No Multi-AZ", rem: "Set multi_az = true" },
      { id: "SEC-018", sev: "high", title: "RDS No Backup", rem: "Set backup_retention_period >= 7" },
    ]},
    { id: "aws_s3_bucket.app_assets", type: "aws_s3_bucket", name: "app_assets", cat: "storage", icon: "📦", group: "global", cost: 5, findings: [
      { id: "SEC-002", sev: "high", title: "S3 Missing Encryption", rem: "Add server_side_encryption_configuration" },
      { id: "SEC-003", sev: "medium", title: "S3 No Versioning", rem: "Enable versioning" },
      { id: "SEC-030", sev: "info", title: "S3 No Lifecycle Rules", rem: "Add lifecycle_rule" },
    ]},
    { id: "aws_s3_bucket.logs", type: "aws_s3_bucket", name: "logs", cat: "storage", icon: "📦", group: "global", cost: 5, findings: [
      { id: "SEC-030", sev: "info", title: "S3 No Lifecycle Rules", rem: "Add lifecycle_rule" },
    ]},
    { id: "aws_kms_key.app", type: "aws_kms_key", name: "app", cat: "security", icon: "🔐", group: "global", cost: 1, findings: [
      { id: "SEC-014", sev: "medium", title: "KMS No Key Rotation", rem: "Set enable_key_rotation = true" },
    ]},
    { id: "aws_lambda_function.processor", type: "aws_lambda_function", name: "processor", cat: "serverless", icon: "λ", group: "global", cost: 0, findings: [
      { id: "SEC-021", sev: "info", title: "Lambda Not in VPC", rem: "Add vpc_config block" },
    ]},
    { id: "aws_iam_role.lambda_role", type: "aws_iam_role", name: "lambda_role", cat: "iam", icon: "🔑", group: "global", cost: 0, findings: [] },
    { id: "aws_iam_role_policy.lambda_policy", type: "aws_iam_role_policy", name: "lambda_policy", cat: "iam", icon: "🔑", group: "global", cost: 0, findings: [
      { id: "SEC-008", sev: "high", title: "IAM Wildcard Resource", rem: "Scope Resource to specific ARNs" },
    ]},
    { id: "aws_cloudwatch_log_group.app", type: "aws_cloudwatch_log_group", name: "app", cat: "monitoring", icon: "📊", group: "global", cost: 0, findings: [
      { id: "SEC-028", sev: "info", title: "Log Group No Retention", rem: "Set retention_in_days" },
    ]},
    { id: "aws_sns_topic.alerts", type: "aws_sns_topic", name: "alerts", cat: "messaging", icon: "📨", group: "global", cost: 0, findings: [
      { id: "SEC-015", sev: "medium", title: "SNS Not Encrypted", rem: "Set kms_master_key_id" },
    ]},
  ],
  edges: [
    { from: "aws_subnet.public_a", to: "aws_vpc.main" },
    { from: "aws_subnet.public_b", to: "aws_vpc.main" },
    { from: "aws_subnet.private_a", to: "aws_vpc.main" },
    { from: "aws_subnet.private_b", to: "aws_vpc.main" },
    { from: "aws_internet_gateway.main", to: "aws_vpc.main" },
    { from: "aws_nat_gateway.main", to: "aws_subnet.public_a" },
    { from: "aws_nat_gateway.main", to: "aws_eip.nat" },
    { from: "aws_security_group.web", to: "aws_vpc.main" },
    { from: "aws_security_group.db", to: "aws_vpc.main" },
    { from: "aws_security_group.db", to: "aws_security_group.web" },
    { from: "aws_instance.web_1", to: "aws_subnet.public_a" },
    { from: "aws_instance.web_1", to: "aws_security_group.web" },
    { from: "aws_instance.web_2", to: "aws_subnet.public_b" },
    { from: "aws_instance.web_2", to: "aws_security_group.web" },
    { from: "aws_lb.main", to: "aws_security_group.web" },
    { from: "aws_lb.main", to: "aws_subnet.public_a" },
    { from: "aws_lb.main", to: "aws_subnet.public_b" },
    { from: "aws_db_instance.primary", to: "aws_security_group.db" },
    { from: "aws_db_instance.primary", to: "aws_subnet.private_a" },
    { from: "aws_lambda_function.processor", to: "aws_iam_role.lambda_role" },
    { from: "aws_lambda_function.processor", to: "aws_db_instance.primary" },
    { from: "aws_iam_role_policy.lambda_policy", to: "aws_iam_role.lambda_role" },
  ],
};

// ─── Layout positions ────────────────────────────────────────────────────────
const POSITIONS = {
  "aws_vpc.main": { x: 60, y: 44 },
  "aws_internet_gateway.main": { x: 206, y: 44 },
  "aws_eip.nat": { x: 352, y: 44 },
  "aws_subnet.public_a": { x: 60, y: 140 },
  "aws_subnet.public_b": { x: 206, y: 140 },
  "aws_security_group.web": { x: 352, y: 140 },
  "aws_lb.main": { x: 60, y: 230 },
  "aws_instance.web_1": { x: 206, y: 230 },
  "aws_instance.web_2": { x: 352, y: 230 },
  "aws_nat_gateway.main": { x: 498, y: 140 },
  "aws_lb_target_group.web": { x: 498, y: 230 },
  "aws_subnet.private_a": { x: 60, y: 350 },
  "aws_subnet.private_b": { x: 206, y: 350 },
  "aws_security_group.db": { x: 352, y: 350 },
  "aws_db_instance.primary": { x: 206, y: 440 },
  "aws_s3_bucket.app_assets": { x: 680, y: 60 },
  "aws_s3_bucket.logs": { x: 680, y: 150 },
  "aws_kms_key.app": { x: 680, y: 240 },
  "aws_lambda_function.processor": { x: 680, y: 330 },
  "aws_iam_role.lambda_role": { x: 830, y: 330 },
  "aws_iam_role_policy.lambda_policy": { x: 830, y: 420 },
  "aws_cloudwatch_log_group.app": { x: 680, y: 420 },
  "aws_sns_topic.alerts": { x: 830, y: 150 },
};

const SEV_COLORS = { critical: "#ef4444", high: "#ff6b35", medium: "#f59e0b", info: "#3b82f6" };
const CAT_COLORS = {
  network: "#3b82f6", compute: "#8b5cf6", database: "#ec4899", storage: "#f59e0b",
  security: "#ef4444", iam: "#06d6a0", serverless: "#14b8a6", monitoring: "#6366f1",
  messaging: "#f97316", other: "#64748b",
};

const GROUPS = [
  { id: "vpc", label: "VPC — production (10.0.0.0/16)", x: 30, y: 20, w: 590, h: 490, color: "#3b82f6" },
  { id: "public", label: "Public Subnets", x: 40, y: 115, w: 520, h: 170, color: "#06d6a0" },
  { id: "private", label: "Private Subnets", x: 40, y: 325, w: 520, h: 150, color: "#f59e0b" },
  { id: "global", label: "Global Services", x: 650, y: 30, w: 240, h: 430, color: "#8b5cf6" },
];

// ─── Components ──────────────────────────────────────────────────────────────

function SummaryBar({ data, filter, setFilter }) {
  const { score, findings, estimated_monthly_cost, resources } = data;
  const total = findings.critical + findings.high + findings.medium + findings.info;
  const scoreColor = score >= 80 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 16, padding: "10px 16px",
      background: "#111827", borderBottom: "1px solid #1e293b", flexWrap: "wrap",
      fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#06d6a0", fontWeight: 700, fontSize: 14 }}>
        <span style={{ width: 20, height: 20, border: "2px solid #06d6a0", borderRadius: 4, display: "grid", placeItems: "center", fontSize: 9 }}>◇</span>
        InfraCanvas
      </div>
      <div style={{ width: 1, height: 20, background: "#1e293b" }} />
      <Stat label="SCORE" value={score} color={scoreColor} suffix="/100" />
      <Stat label="RESOURCES" value={resources.length} color="#e2e8f0" />
      <div style={{ width: 1, height: 20, background: "#1e293b" }} />
      <FilterChip label="ALL" count={resources.length} active={filter === "all"} onClick={() => setFilter("all")} color="#94a3b8" />
      <FilterChip label="CRIT" count={findings.critical} active={filter === "critical"} onClick={() => setFilter("critical")} color="#ef4444" />
      <FilterChip label="HIGH" count={findings.high} active={filter === "high"} onClick={() => setFilter("high")} color="#ff6b35" />
      <FilterChip label="MED" count={findings.medium} active={filter === "medium"} onClick={() => setFilter("medium")} color="#f59e0b" />
      <FilterChip label="INFO" count={findings.info} active={filter === "info"} onClick={() => setFilter("info")} color="#3b82f6" />
      <div style={{ flex: 1 }} />
      <Stat label="EST. COST" value={`$${estimated_monthly_cost}`} color="#06d6a0" suffix="/mo" />
    </div>
  );
}

function Stat({ label, value, color, suffix = "" }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ color, fontWeight: 700, fontSize: 16 }}>{value}<span style={{ fontSize: 10, opacity: 0.6 }}>{suffix}</span></div>
      <div style={{ color: "#64748b", fontSize: 9, letterSpacing: 1 }}>{label}</div>
    </div>
  );
}

function FilterChip({ label, count, active, onClick, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "3px 10px", borderRadius: 4, fontSize: 10, fontWeight: 600,
        fontFamily: "'JetBrains Mono', monospace", cursor: "pointer",
        border: `1px solid ${active ? color : "#1e293b"}`,
        background: active ? `${color}18` : "transparent",
        color: active ? color : "#64748b",
        transition: "all 0.15s",
      }}
    >
      {label} {count}
    </button>
  );
}

function ResourceNode({ resource, pos, selected, onClick, visible }) {
  const maxSev = resource.findings.length > 0
    ? resource.findings.reduce((a, b) => {
        const order = ["critical", "high", "medium", "info"];
        return order.indexOf(a.sev) <= order.indexOf(b.sev) ? a : b;
      }).sev
    : null;
  const borderColor = maxSev ? SEV_COLORS[maxSev] : (selected ? "#06d6a0" : "#1e293b");
  const catColor = CAT_COLORS[resource.cat] || "#64748b";

  if (!visible) return null;

  return (
    <g
      transform={`translate(${pos.x}, ${pos.y})`}
      onClick={() => onClick(resource)}
      style={{ cursor: "pointer" }}
    >
      <rect
        x={0} y={0} width={130} height={48} rx={8}
        fill="#1a2332"
        stroke={borderColor}
        strokeWidth={selected ? 2 : 1.2}
        style={{ transition: "all 0.2s", filter: selected ? `drop-shadow(0 0 8px ${borderColor}40)` : "none" }}
      />
      <rect x={0} y={0} width={4} height={48} rx={2} fill={catColor} opacity={0.6} />
      <text x={34} y={20} fontSize={9.5} fontWeight={600} fill="#e2e8f0" fontFamily="'JetBrains Mono', monospace">
        {resource.name}
      </text>
      <text x={34} y={34} fontSize={7.5} fill="#64748b" fontFamily="'JetBrains Mono', monospace">
        {resource.type.replace("aws_", "")}
      </text>
      <text x={16} y={28} fontSize={14} textAnchor="middle" dominantBaseline="central">
        {resource.icon}
      </text>
      {resource.cost > 0 && (
        <text x={124} y={42} fontSize={7} fill="#06d6a0" textAnchor="end" fontFamily="'JetBrains Mono', monospace">
          ${resource.cost}
        </text>
      )}
      {resource.findings.length > 0 && (
        <g transform={`translate(122, -6)`}>
          <circle cx={0} cy={0} r={9} fill={SEV_COLORS[maxSev]} />
          <text x={0} y={0.5} fontSize={8} fontWeight={700} fill="white" textAnchor="middle" dominantBaseline="central">
            {resource.findings.length}
          </text>
        </g>
      )}
    </g>
  );
}

function EdgeLine({ from, to, resources, visible }) {
  const fromRes = resources.find(r => r.id === from);
  const toRes = resources.find(r => r.id === to);
  if (!fromRes || !toRes || !visible) return null;

  const fromPos = POSITIONS[from];
  const toPos = POSITIONS[to];
  if (!fromPos || !toPos) return null;

  const x1 = fromPos.x + 65;
  const y1 = fromPos.y + 24;
  const x2 = toPos.x + 65;
  const y2 = toPos.y + 24;

  return (
    <line
      x1={x1} y1={y1} x2={x2} y2={y2}
      stroke="#1e293b" strokeWidth={1} strokeDasharray="4,3" opacity={0.6}
    />
  );
}

function GroupBox({ group }) {
  return (
    <g>
      <rect
        x={group.x} y={group.y} width={group.w} height={group.h}
        rx={12} fill="none"
        stroke={group.color} strokeWidth={1.2} strokeDasharray="6,4" opacity={0.3}
      />
      <rect
        x={group.x + 12} y={group.y - 8} width={group.label.length * 6.5 + 16} height={16}
        rx={3} fill="#0a0e17"
      />
      <text
        x={group.x + 20} y={group.y + 3}
        fontSize={9} fontWeight={600} fill={group.color}
        fontFamily="'JetBrains Mono', monospace" opacity={0.7}
      >
        {group.label}
      </text>
    </g>
  );
}

function DetailPanel({ resource, onClose }) {
  if (!resource) return null;

  const maxSev = resource.findings.length > 0
    ? resource.findings.reduce((a, b) => {
        const order = ["critical", "high", "medium", "info"];
        return order.indexOf(a.sev) <= order.indexOf(b.sev) ? a : b;
      }).sev
    : null;

  return (
    <div style={{
      position: "absolute", top: 0, right: 0, width: 320, height: "100%",
      background: "#111827", borderLeft: "1px solid #1e293b",
      overflow: "auto", zIndex: 20, fontFamily: "'DM Sans', sans-serif",
      animation: "slideIn 0.2s ease-out",
    }}>
      <style>{`@keyframes slideIn { from { transform: translateX(20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
      <div style={{ padding: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 20, marginBottom: 2 }}>{resource.icon}</div>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 14, color: "#e2e8f0" }}>
              {resource.id}
            </div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{resource.type}</div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "1px solid #1e293b", borderRadius: 6,
              color: "#94a3b8", cursor: "pointer", padding: "4px 8px", fontSize: 12,
            }}
          >✕</button>
        </div>

        {resource.cost > 0 && (
          <div style={{
            background: "#06d6a010", border: "1px solid #06d6a030", borderRadius: 8,
            padding: "10px 14px", marginBottom: 16,
          }}>
            <div style={{ fontSize: 10, color: "#64748b", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>EST. MONTHLY COST</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#06d6a0", fontFamily: "'JetBrains Mono', monospace" }}>
              ${resource.cost}<span style={{ fontSize: 12, opacity: 0.6 }}>/mo</span>
            </div>
          </div>
        )}

        {resource.findings.length > 0 && (
          <div>
            <div style={{
              fontSize: 10, fontWeight: 600, color: "#64748b", fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: 1, marginBottom: 10,
            }}>
              FINDINGS ({resource.findings.length})
            </div>
            {resource.findings.map((f, i) => (
              <div key={i} style={{
                background: "#0d1117", border: "1px solid #1e293b", borderRadius: 8,
                padding: 12, marginBottom: 8, borderLeft: `3px solid ${SEV_COLORS[f.sev]}`,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                  <span style={{
                    padding: "2px 6px", borderRadius: 3, fontSize: 9, fontWeight: 700,
                    background: SEV_COLORS[f.sev], color: "white",
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>{f.sev.toUpperCase()}</span>
                  <span style={{ fontSize: 11, color: "#64748b", fontFamily: "'JetBrains Mono', monospace" }}>{f.id}</span>
                </div>
                <div style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 500, marginBottom: 6 }}>{f.title}</div>
                <div style={{
                  fontSize: 11, color: "#94a3b8", background: "#111827",
                  padding: "6px 8px", borderRadius: 4, lineHeight: 1.4,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  ↳ {f.rem}
                </div>
              </div>
            ))}
          </div>
        )}

        {resource.findings.length === 0 && (
          <div style={{
            background: "#22c55e10", border: "1px solid #22c55e30", borderRadius: 8,
            padding: "16px", textAlign: "center", color: "#22c55e", fontSize: 13,
          }}>
            ✓ No security findings
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────────────

export default function InfraCanvasViewer() {
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState("all");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  const data = INFRA_DATA;

  const visibleResources = useMemo(() => {
    if (filter === "all") return new Set(data.resources.map(r => r.id));
    return new Set(
      data.resources
        .filter(r => r.findings.some(f => f.sev === filter))
        .map(r => r.id)
    );
  }, [filter, data.resources]);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.08 : 0.08;
    setZoom(z => Math.max(0.4, Math.min(2.5, z + delta)));
  }, []);

  const handleMouseDown = useCallback((e) => {
    if (e.target.closest("g[style*='cursor: pointer']")) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback((e) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
  }, [isPanning, panStart]);

  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  useEffect(() => {
    const svg = svgRef.current;
    if (svg) svg.addEventListener("wheel", handleWheel, { passive: false });
    return () => { if (svg) svg.removeEventListener("wheel", handleWheel); };
  }, [handleWheel]);

  const selectedResource = data.resources.find(r => r.id === selected);

  return (
    <div style={{
      width: "100%", height: "100vh", background: "#0a0e17",
      display: "flex", flexDirection: "column", overflow: "hidden",
      fontFamily: "'DM Sans', -apple-system, sans-serif",
      position: "relative",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      <SummaryBar data={data} filter={filter} setFilter={setFilter} />

      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {/* Grid background */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 0,
          backgroundImage: "linear-gradient(rgba(6,214,160,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(6,214,160,0.04) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }} />

        <svg
          ref={svgRef}
          width="100%" height="100%"
          style={{ position: "relative", zIndex: 1, cursor: isPanning ? "grabbing" : "grab" }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Groups */}
            {GROUPS.map(g => <GroupBox key={g.id} group={g} />)}

            {/* Edges */}
            {data.edges.map((e, i) => (
              <EdgeLine
                key={i} from={e.from} to={e.to}
                resources={data.resources}
                visible={filter === "all" || (visibleResources.has(e.from) && visibleResources.has(e.to))}
              />
            ))}

            {/* Nodes */}
            {data.resources.map(r => {
              const pos = POSITIONS[r.id];
              if (!pos) return null;
              return (
                <ResourceNode
                  key={r.id}
                  resource={r}
                  pos={pos}
                  selected={selected === r.id}
                  onClick={(res) => setSelected(selected === res.id ? null : res.id)}
                  visible={filter === "all" || visibleResources.has(r.id)}
                />
              );
            })}
          </g>
        </svg>

        {/* Zoom controls */}
        <div style={{
          position: "absolute", bottom: 16, left: 16, display: "flex", gap: 4, zIndex: 10,
        }}>
          {[
            { label: "−", action: () => setZoom(z => Math.max(0.4, z - 0.15)) },
            { label: `${Math.round(zoom * 100)}%`, action: () => { setZoom(1); setPan({ x: 0, y: 0 }); } },
            { label: "+", action: () => setZoom(z => Math.min(2.5, z + 0.15)) },
          ].map((btn, i) => (
            <button key={i} onClick={btn.action} style={{
              padding: "4px 10px", background: "#111827", border: "1px solid #1e293b",
              borderRadius: 4, color: "#94a3b8", cursor: "pointer", fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
            }}>{btn.label}</button>
          ))}
        </div>

        {/* Legend */}
        <div style={{
          position: "absolute", bottom: 16, right: selected ? 336 : 16,
          display: "flex", gap: 12, background: "#111827ee", border: "1px solid #1e293b",
          borderRadius: 8, padding: "8px 14px", zIndex: 10, flexWrap: "wrap",
          transition: "right 0.2s",
        }}>
          {Object.entries(SEV_COLORS).map(([sev, color]) => (
            <div key={sev} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
              <span style={{ fontSize: 10, color: "#94a3b8", fontFamily: "'JetBrains Mono', monospace", textTransform: "capitalize" }}>{sev}</span>
            </div>
          ))}
        </div>

        {/* Detail panel */}
        <DetailPanel resource={selectedResource} onClose={() => setSelected(null)} />
      </div>
    </div>
  );
}
