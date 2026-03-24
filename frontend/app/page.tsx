import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#dbe7e2_0%,#f4f6f4_50%,#eef3ef_100%)] px-6 py-12">
      <div className="mx-auto max-w-5xl">
        <section className="card overflow-hidden p-8 md:p-12">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-moss">Game Theory Simulator</p>
          <h1 className="font-display text-4xl text-slate md:text-6xl">Circle of Lies</h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-slate/90 md:text-lg">
            A portfolio-grade social strategy game where trust, suspicion, and alliances evolve through deterministic,
            explainable AI heuristics.
          </p>
          <div className="mt-8 grid gap-3 text-sm text-slate/90 md:grid-cols-3">
            <div className="metric-chip">1 human player vs 5 AI strategists</div>
            <div className="metric-chip">6-8 round elimination loop</div>
            <div className="metric-chip">Post-game behavioral analytics</div>
          </div>
          <div className="mt-9">
            <Link
              href="/game"
              className="inline-flex items-center rounded-xl bg-moss px-5 py-3 text-sm font-semibold text-white transition hover:bg-moss/90"
            >
              Launch Simulation
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
