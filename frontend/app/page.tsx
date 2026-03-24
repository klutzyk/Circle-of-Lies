import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="scanlines min-h-screen px-6 py-12">
      <div className="mx-auto max-w-5xl">
        <section className="card overflow-hidden p-8 md:p-12">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-[#7cd892]">Neon Terminal Simulation</p>
          <h1 className="text-4xl font-bold uppercase tracking-[0.14em] text-[#adffbe] md:text-5xl">Circle of Lies</h1>
          <p className="mt-5 max-w-2xl text-sm leading-relaxed text-[#79d48f] md:text-base">
            Enter a dark social arena. Type your intent, shape alliances, and survive the vote as trust and suspicion evolve round by round.
          </p>
          <div className="mt-8 grid gap-3 text-xs text-[#7ad18f] md:grid-cols-3">
            <div className="metric-chip">1 human player vs 5 AI strategists</div>
            <div className="metric-chip">6-8 round elimination loop</div>
            <div className="metric-chip">Unstable alliances, private motives, public votes</div>
          </div>
          <div className="mt-9">
            <Link
              href="/game"
              className="inline-flex items-center rounded-md border border-[#2b7a3a]/45 bg-[#0a200f] px-5 py-3 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae]"
            >
              Launch Terminal
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
