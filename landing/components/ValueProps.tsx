export default function ValueProps() {
  return (
    <section className="py-16 max-w-4xl mx-auto px-6">
      <h2 className="text-3xl font-bold text-slate-50 text-center mb-12">
        Everything you need to understand your infrastructure
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1 — Canvas */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-amber-400"
            aria-hidden="true"
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
          </svg>
          <h3 className="text-xl font-semibold text-slate-50 mt-4">Visual infrastructure map</h3>
          <p className="text-slate-300 text-sm mt-2">
            One command generates an interactive diagram of your AWS and Azure resources, grouped by
            VPC and subnet, with dependency edges. No manual drawing.
          </p>
          <span className="text-xs font-mono text-slate-400 mt-3 block">AWS + Azure</span>
        </div>

        {/* Card 2 — Security */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-red-400"
            aria-hidden="true"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <h3 className="text-xl font-semibold text-slate-50 mt-4">
            Security blind spots, surfaced
          </h3>
          <p className="text-slate-300 text-sm mt-2">
            10 built-in AWS security rules (S3 public access, IAM wildcards, unencrypted RDS) with
            severity ratings and remediation steps. No config required.
          </p>
          <span className="text-xs font-mono text-slate-400 mt-3 block">10 rules at launch</span>
        </div>

        {/* Card 3 — Cost + Drift */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-green-400"
            aria-hidden="true"
          >
            <line x1="18" y1="20" x2="18" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
          </svg>
          <h3 className="text-xl font-semibold text-slate-50 mt-4">Cost and drift in the same view</h3>
          <p className="text-slate-300 text-sm mt-2">
            See cost estimates per resource and flag drift between your Terraform state and what&apos;s
            actually deployed. No more surprises on the AWS bill.
          </p>
          <span className="text-xs font-mono text-orange-400 mt-3 block">Coming in v1.0</span>
        </div>
      </div>
    </section>
  )
}
