'use client'

/**
 * /settings/billing — v1 stub.
 *
 * The Stripe portal endpoint is deferred to a later phase. For now the
 * "Open billing portal" CTA shows an alert noting the feature is coming
 * soon — the slot exists so the navigation surfaces correctly.
 */
export default function BillingPage() {
  function handleOpenPortal() {
    if (typeof window !== 'undefined') {
      window.alert('Billing portal — coming soon')
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 max-w-md">
      <h2 className="text-base font-semibold text-slate-900">
        Billing &amp; invoices
      </h2>
      <p className="text-sm text-slate-500 mt-2">
        Manage your subscription, view invoices, and update payment methods in
        the Stripe portal.
      </p>
      <button
        type="button"
        onClick={handleOpenPortal}
        data-testid="billing-portal-btn"
        className="mt-4 inline-flex items-center bg-amber-400 hover:bg-amber-300 text-slate-900 font-medium px-4 py-2 rounded-md transition-colors"
      >
        Open billing portal
      </button>
      <p className="text-xs text-slate-400 mt-3">
        Coming soon — billing portal integration ships after Phase 7.
      </p>
    </div>
  )
}
