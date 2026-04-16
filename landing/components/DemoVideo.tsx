export default function DemoVideo({ embedUrl }: { embedUrl: string }) {
  return (
    <section className="py-16 max-w-4xl mx-auto px-6">
      <p className="text-sm font-mono text-amber-400 uppercase tracking-widest mb-4">
        See it in action
      </p>
      {embedUrl ? (
        <iframe
          src={embedUrl}
          className="w-full aspect-video rounded-xl border border-slate-800"
          title="InfraCanvas demo video"
          allowFullScreen
        />
      ) : (
        <div className="bg-slate-900 w-full aspect-video rounded-xl border border-slate-800 flex items-center justify-center">
          <span className="text-slate-500">Video coming soon</span>
        </div>
      )}
      <p className="text-sm text-slate-400 mt-3 text-center">
        2-minute walkthrough: scan → diagram → security findings → score card
      </p>
    </section>
  )
}
