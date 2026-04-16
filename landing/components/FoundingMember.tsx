export default function FoundingMember({ spotsRemaining }: { spotsRemaining: number }) {
  return (
    <section id="founding-member" className="py-16 max-w-2xl mx-auto text-center px-6">
      <div className="bg-slate-900 border border-amber-400/20 rounded-2xl p-10">
        <p className="text-amber-400 font-mono text-sm mb-2">
          {spotsRemaining} of 50 founding member spots remaining
        </p>
        <h2 className="text-3xl font-bold text-slate-50 mb-2">Lock in $49/mo — forever</h2>
        <p className="text-slate-300 text-base mb-6">
          Price locks at $49/mo for founding members. When we launch publicly, pricing goes up.
          You&apos;ll also get a private Discord channel for direct roadmap input.
        </p>
        <ul className="text-left max-w-sm mx-auto mb-8 space-y-2">
          <li className="text-slate-300 text-sm">✓ $49/mo locked forever (no price increases, ever)</li>
          <li className="text-slate-300 text-sm">✓ Private Discord channel — direct access to the founder</li>
          <li className="text-slate-300 text-sm">✓ Input on which features ship first</li>
          <li className="text-slate-300 text-sm">✓ Early access to every phase as it ships</li>
        </ul>
        <a
          href={process.env.NEXT_PUBLIC_STRIPE_PAYMENT_LINK}
          className="block bg-amber-400 text-slate-950 font-bold text-lg px-10 py-4 rounded-xl w-full hover:bg-amber-500 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Claim your founding member spot for $49 per month"
        >
          Claim Your Founding Member Spot
        </a>
        <p className="text-slate-500 text-xs mt-4">
          Secure checkout via Stripe. Cancel anytime. No questions asked.
        </p>
      </div>
    </section>
  )
}
