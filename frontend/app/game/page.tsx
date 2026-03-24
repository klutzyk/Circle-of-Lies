'use client';

import { useMemo, useState } from 'react';

import { fetchActionCatalog, fetchAnalytics, startGame, submitAction } from '@/lib/api';
import { ActionCatalogItem, AnalyticsPayload, GamePayload } from '@/types/game';

function TimelineChart({
  title,
  data,
  color,
}: {
  title: string;
  data: { round: number; value: number }[];
  color: string;
}) {
  const maxX = Math.max(...data.map((d) => d.round), 1);
  const points = data
    .map((d) => `${(d.round / maxX) * 100},${100 - d.value}`)
    .join(' ');

  return (
    <div className="card p-4">
      <h4 className="font-display text-base text-slate">{title}</h4>
      <svg viewBox="0 0 100 100" className="mt-3 h-40 w-full rounded-lg bg-slate/5 p-2">
        <polyline fill="none" stroke={color} strokeWidth="2.2" points={points} />
      </svg>
    </div>
  );
}

function ParticipantTable({ game }: { game: GamePayload }) {
  const entries = Object.entries(game.state.participants);
  const alive = entries.filter(([, p]) => p.eliminated_round === null).length;

  return (
    <div className="card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-lg text-slate">Social Field</h3>
        <span className="text-xs font-medium text-slate/75">Alive: {alive}/6</span>
      </div>
      <div className="space-y-2 text-sm">
        {entries.map(([id, p]) => {
          const trust = id === 'player' ? 0 : game.state.trust[id].player;
          const suspicion = id === 'player' ? 0 : game.state.suspicion[id].player;
          return (
            <div key={id} className="rounded-lg border border-black/10 bg-white p-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate">{p.name}</span>
                  {id === 'player' ? ' (You)' : ''}
                </div>
                <span className="text-xs text-slate/70">
                  {p.eliminated_round ? `Out R${p.eliminated_round}` : 'Active'}
                </span>
              </div>
              {id !== 'player' && (
                <div className="mt-2 flex gap-2 text-xs text-slate/80">
                  <span className="metric-chip">Trust in You: {trust.toFixed(1)}</span>
                  <span className="metric-chip">Suspicion on You: {suspicion.toFixed(1)}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function GamePage() {
  const [playerName, setPlayerName] = useState('Strategist');
  const [maxRounds, setMaxRounds] = useState(7);
  const [game, setGame] = useState<GamePayload | null>(null);
  const [actions, setActions] = useState<ActionCatalogItem[]>([]);
  const [actionType, setActionType] = useState('quiet');
  const [targetId, setTargetId] = useState<string>('');
  const [analytics, setAnalytics] = useState<AnalyticsPayload | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const aliveTargets = useMemo(() => {
    if (!game) return [] as { id: string; name: string }[];
    return Object.entries(game.state.participants)
      .filter(([id, p]) => id !== 'player' && p.eliminated_round === null)
      .map(([id, p]) => ({ id, name: p.name }));
  }, [game]);

  const selectedAction = actions.find((a) => a.action_type === actionType);

  async function onStart() {
    setError('');
    setLoading(true);
    try {
      const [catalog, started] = await Promise.all([
        fetchActionCatalog(),
        startGame(playerName.trim() || 'Strategist', maxRounds),
      ]);
      setActions(catalog.actions);
      setGame(started);
      setAnalytics(null);
      setActionType(catalog.actions[0]?.action_type ?? 'quiet');
      setTargetId('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }

  async function onSubmitAction() {
    if (!game) return;
    setError('');
    setLoading(true);
    try {
      const next = await submitAction(
        game.summary.game_id,
        actionType,
        selectedAction?.needs_target ? targetId : null
      );
      setGame(next);
      setTargetId('');
      if (next.summary.status === 'completed') {
        const report = await fetchAnalytics(next.summary.game_id);
        setAnalytics(report);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit action');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#edf3f0_0%,#f6f8f6_100%)] px-4 py-8 md:px-8">
      <div className="mx-auto max-w-6xl space-y-5">
        <div className="card p-5">
          <h1 className="font-display text-3xl text-slate">Circle of Lies</h1>
          <p className="mt-2 text-sm text-slate/85">Deterministic social strategy simulation with explainable outcomes.</p>
        </div>

        {!game && (
          <div className="card grid gap-4 p-5 md:grid-cols-[1fr_180px_160px] md:items-end">
            <label className="text-sm">
              Alias
              <input
                className="mt-1 w-full rounded-lg border border-black/15 bg-white px-3 py-2"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
              />
            </label>
            <label className="text-sm">
              Rounds
              <select
                className="mt-1 w-full rounded-lg border border-black/15 bg-white px-3 py-2"
                value={maxRounds}
                onChange={(e) => setMaxRounds(Number(e.target.value))}
              >
                <option value={6}>6</option>
                <option value={7}>7</option>
                <option value={8}>8</option>
              </select>
            </label>
            <button
              onClick={onStart}
              disabled={loading}
              className="rounded-lg bg-moss px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {loading ? 'Starting...' : 'Start Match'}
            </button>
          </div>
        )}

        {game && (
          <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
            <div className="space-y-5">
              <div className="card p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-display text-xl text-slate">
                    Round {game.summary.current_round} / {game.summary.max_rounds}
                  </h2>
                  <span className="metric-chip">Status: {game.summary.status}</span>
                </div>
                <p className="mt-3 text-sm text-slate/85">Event: {game.state.current_event}</p>

                {game.summary.status === 'active' && (
                  <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                    <select
                      value={actionType}
                      onChange={(e) => setActionType(e.target.value)}
                      className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm"
                    >
                      {actions.map((action) => (
                        <option key={action.action_type} value={action.action_type}>
                          {action.label}
                        </option>
                      ))}
                    </select>

                    <select
                      value={targetId}
                      onChange={(e) => setTargetId(e.target.value)}
                      disabled={!selectedAction?.needs_target}
                      className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm disabled:opacity-50"
                    >
                      <option value="">Select target</option>
                      {aliveTargets.map((target) => (
                        <option key={target.id} value={target.id}>
                          {target.name}
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={onSubmitAction}
                      disabled={loading || (selectedAction?.needs_target && !targetId)}
                      className="rounded-lg bg-ember px-4 py-2 text-sm font-semibold text-white disabled:opacity-55"
                    >
                      {loading ? 'Resolving...' : 'Play Round'}
                    </button>
                  </div>
                )}

                <p className="mt-3 text-xs text-slate/75">
                  {selectedAction?.description ?? 'Select an action to proceed.'}
                </p>
                {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
              </div>

              <div className="card p-4">
                <h3 className="font-display text-lg text-slate">Round Feed</h3>
                <div className="mt-3 max-h-[360px] space-y-2 overflow-auto pr-1">
                  {game.state.history.length === 0 && <p className="text-sm text-slate/70">No rounds played yet.</p>}
                  {[...game.state.history].reverse().map((log) => (
                    <div key={log.round_number} className="rounded-lg border border-black/10 bg-white p-3 text-sm">
                      <p className="font-semibold text-slate">Round {log.round_number}</p>
                      <p className="text-slate/80">
                        You used <span className="font-medium">{log.player_action.action_type}</span>
                        {log.player_action.target_id ? ` on ${game.state.participants[log.player_action.target_id]?.name}` : ''}.
                      </p>
                      <p className="text-slate/80">
                        Eliminated: {log.eliminated_id ? game.state.participants[log.eliminated_id]?.name : 'None'}
                      </p>
                      <p className="text-slate/80">
                        Trust {log.summary.player_avg_trust.toFixed(1)} | Suspicion {log.summary.player_avg_suspicion.toFixed(1)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-5">
              <ParticipantTable game={game} />

              {analytics && (
                <div className="space-y-3">
                  <div className="card p-4">
                    <h3 className="font-display text-lg text-slate">Endgame Analysis</h3>
                    <p className="mt-2 text-sm text-slate/85">
                      Archetype: <span className="font-semibold">{analytics.analytics.strategy_archetype}</span>
                    </p>
                    <p className="mt-1 text-sm text-slate/85">{analytics.analytics.outcome_reason}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {analytics.analytics.game_theory_tags.map((tag) => (
                        <span key={tag} className="rounded-md bg-slate/10 px-2 py-1 text-slate/85">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  <TimelineChart
                    title="Trust Timeline"
                    data={analytics.analytics.trust_timeline}
                    color="#2f6f5e"
                  />
                  <TimelineChart
                    title="Suspicion Timeline"
                    data={analytics.analytics.suspicion_timeline}
                    color="#b7582d"
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
