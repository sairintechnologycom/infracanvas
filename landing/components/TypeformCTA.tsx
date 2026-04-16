export default function TypeformCTA() {
  return (
    <section className="py-16 text-center max-w-2xl mx-auto px-6">
      <h2 className="text-2xl font-bold text-slate-50 mb-3">
        Not ready to pay yet? Help us build this right.
      </h2>
      <p className="text-slate-300 text-base mb-6">
        We&apos;re talking to engineers who manage Terraform-managed infrastructure. 2 minutes. No sales
        call.
      </p>
      <a
        href={process.env.NEXT_PUBLIC_TYPEFORM_URL}
        className="inline-block border border-slate-600 text-slate-50 font-medium px-8 py-3 rounded-lg hover:bg-slate-800 transition-colors"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Answer 7 questions about your infrastructure needs"
      >
        Answer 7 questions →
      </a>
      <p className="text-slate-500 text-sm mt-3">
        We read every response. High-signal respondents get invited for a 15-min call.
      </p>
    </section>
  )
}
