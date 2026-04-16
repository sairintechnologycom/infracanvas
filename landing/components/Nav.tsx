export default function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-sm bg-slate-950/80 h-14 px-6 flex items-center justify-between">
      <span className="font-bold text-slate-50 text-lg">InfraCanvas</span>
      <a
        href="#founding-member"
        className="text-amber-400 text-sm font-medium hover:text-amber-300 transition-colors"
        aria-label="Get early access to InfraCanvas founding member plan"
      >
        Get Early Access
      </a>
    </nav>
  )
}
