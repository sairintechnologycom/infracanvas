export default function Hero({ spotsRemaining }: { spotsRemaining: number }) {
  return (
    <section className="pt-32 pb-20 max-w-3xl mx-auto text-center px-6">
      <p className="text-amber-400 text-sm font-mono uppercase tracking-widest">
        5 tabs open. 0 clarity.
      </p>
      <h1 className="text-5xl lg:text-6xl font-extrabold text-slate-50 leading-tight mt-4">
        One command. Your entire infrastructure — visualised, scored, explained.
      </h1>
      <p className="text-lg text-slate-300 mt-4 max-w-2xl mx-auto">
        InfraCanvas scans your Terraform directory and opens an interactive diagram with security
        findings, cost estimates, and drift detection. AWS, Azure, and physical data centres — in a
        single view.
      </p>
      <div className="mt-8 bg-slate-900 border border-slate-800 rounded-lg px-6 py-4 font-mono text-sm text-slate-50 inline-block">
        $ infracanvas scan ./terraform
      </div>
      <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
        <a
          href={process.env.NEXT_PUBLIC_STRIPE_PAYMENT_LINK}
          className="bg-amber-400 text-slate-950 font-bold px-8 py-3 rounded-lg hover:bg-amber-500 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Claim your founding member spot for $49 per month"
        >
          Claim Founding Member Spot — $49/mo
        </a>
        <a
          href={process.env.NEXT_PUBLIC_TYPEFORM_URL}
          className="border border-slate-600 text-slate-50 font-medium px-8 py-3 rounded-lg hover:bg-slate-800 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Tell us what you need — answer our survey"
        >
          Tell us what you need
        </a>
      </div>
      <p className="text-sm text-amber-400 font-mono mt-4">
        {spotsRemaining} of 50 founding member spots remaining
      </p>
    </section>
  )
}
