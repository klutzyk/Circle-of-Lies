'use client';

import Image from 'next/image';
import { useEffect, useMemo, useState } from 'react';

import terminalImage from '../../assets/terminal.jpg';
import terminalFinalImage from '../../assets/terminal4.jpg';
import {
  fetchActionCatalog,
  fetchAnalytics,
  fetchFlavorDialogue,
  fetchPostGameLLMAnalysis,
  startGame,
  submitAction,
  submitStoryTurn,
} from '@/lib/api';
import {
  ActionCatalogItem,
  AnalyticsPayload,
  GamePayload,
  LLMEnhancementPayload,
} from '@/types/game';

type TabId = 'narrative' | 'dossier' | 'signals' | 'controls';

function TimelineChart({
  title,
  data,
}: {
  title: string;
  data: { round: number; value: number }[];
}) {
  const maxX = Math.max(...data.map((d) => d.round), 1);
  const points = data.map((d) => `${(d.round / maxX) * 100},${100 - d.value}`).join(' ');

  return (
    <div className="rounded-md border border-[#2b7a3a]/45 bg-[#061008] p-3">
      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[#9cf8ae]">{title}</h4>
      <svg viewBox="0 0 100 100" className="mt-2 h-28 w-full rounded bg-[#030905] p-2">
        <polyline fill="none" stroke="#7aff95" strokeWidth="2" points={points} />
      </svg>
    </div>
  );
}

export default function GamePage() {
  const [playerName, setPlayerName] = useState('Operator');
  const [maxRounds, setMaxRounds] = useState(7);
  const [game, setGame] = useState<GamePayload | null>(null);
  const [actions, setActions] = useState<ActionCatalogItem[]>([]);
  const [actionType, setActionType] = useState('quiet');
  const [targetId, setTargetId] = useState('');
  const [playerText, setPlayerText] = useState('I want to stay calm and align with someone reliable this round.');
  const [analytics, setAnalytics] = useState<AnalyticsPayload | null>(null);
  const [llmSummary, setLlmSummary] = useState<LLMEnhancementPayload | null>(null);
  const [llmDialogue, setLlmDialogue] = useState<LLMEnhancementPayload | null>(null);
  const [dialogueSpeakerId, setDialogueSpeakerId] = useState('ai_1');
  const [storyLine, setStoryLine] = useState('The room is silent. Six minds scan for weakness.');
  const [tab, setTab] = useState<TabId>('narrative');
  const [zoomed, setZoomed] = useState(false);
  const [showFinalTerminal, setShowFinalTerminal] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const aliveTargets = useMemo(() => {
    if (!game) return [] as { id: string; name: string }[];
    return Object.entries(game.state.participants)
      .filter(([id, p]) => id !== 'player' && p.eliminated_round === null)
      .map(([id, p]) => ({ id, name: p.name }));
  }, [game]);

  const selectedAction = actions.find((a) => a.action_type === actionType);

  const narrativeLines = useMemo(() => {
    if (!game) return [] as string[];
    const lines: string[] = [];
    for (const log of game.state.history) {
      const targetName = log.player_action.target_id
        ? game.state.participants[log.player_action.target_id]?.name
        : '';
      const eliminatedName = log.eliminated_id ? game.state.participants[log.eliminated_id]?.name : 'no one';
      lines.push(`Round ${log.round_number}: ${log.event}.`);
      lines.push(
        targetName
          ? `You chose ${log.player_action.action_type} toward ${targetName}.`
          : `You chose ${log.player_action.action_type}.`
      );
      lines.push(`The vote ended with ${eliminatedName} removed from the table.`);
      lines.push(
        `Your social readings: trust ${log.summary.player_avg_trust.toFixed(1)} | suspicion ${log.summary.player_avg_suspicion.toFixed(1)}.`
      );
    }
    if (storyLine) lines.push(storyLine);
    if (llmDialogue?.text) lines.push(llmDialogue.text);
    return lines;
  }, [game, storyLine, llmDialogue]);

  async function onStart() {
    setError('');
    setLoading(true);
    try {
      const [catalog, started] = await Promise.all([
        fetchActionCatalog(),
        startGame(playerName.trim() || 'Operator', maxRounds),
      ]);
      setActions(catalog.actions);
      setGame(started);
      setAnalytics(null);
      setLlmSummary(null);
      setLlmDialogue(null);
      setTab('narrative');
      setZoomed(true);
      setShowFinalTerminal(false);
      setStoryLine('The first whisper spreads through the room. Everyone is performing for survival.');
      setActionType(catalog.actions[0]?.action_type ?? 'quiet');
      setTargetId('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!zoomed) {
      setShowFinalTerminal(false);
      return;
    }
    const timer = window.setTimeout(() => {
      setShowFinalTerminal(true);
    }, 120);
    return () => window.clearTimeout(timer);
  }, [zoomed]);

  async function onStoryTurn() {
    if (!game) return;
    setError('');
    setLoading(true);
    try {
      const next = await submitStoryTurn(game.summary.game_id, playerText);
      setGame(next);
      setStoryLine(next.story?.narration ?? 'You hold your cards close.');
      if (next.summary.status === 'completed') {
        const report = await fetchAnalytics(next.summary.game_id);
        setAnalytics(report);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Story turn failed');
    } finally {
      setLoading(false);
    }
  }

  async function onGenerateFlavorDialogue() {
    if (!game) return;
    setLoading(true);
    setError('');
    try {
      const dialogue = await fetchFlavorDialogue(game.summary.game_id, dialogueSpeakerId);
      setLlmDialogue(dialogue);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Dialogue generation failed');
    } finally {
      setLoading(false);
    }
  }

  async function onGenerateLLMSummary() {
    if (!game) return;
    setLoading(true);
    setError('');
    try {
      const summary = await fetchPostGameLLMAnalysis(game.summary.game_id);
      setLlmSummary(summary);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Strategic report unavailable');
    } finally {
      setLoading(false);
    }
  }

  async function onManualAction() {
    if (!game) return;
    setLoading(true);
    setError('');
    try {
      const next = await submitAction(
        game.summary.game_id,
        actionType,
        selectedAction?.needs_target ? targetId : null
      );
      setGame(next);
      setStoryLine(`You forced a direct move: ${actionType}.`);
      if (next.summary.status === 'completed') {
        const report = await fetchAnalytics(next.summary.game_id);
        setAnalytics(report);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Manual action failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="scanlines flex h-screen w-screen items-center justify-center overflow-hidden p-2 md:p-3">
      <div className="relative aspect-[16/9] w-[min(96vw,1700px)] max-h-[94vh] overflow-hidden rounded-xl border border-[#2b7a3a]/45 bg-black/40">
        <div
          className={`relative h-full w-full transition-transform duration-[900ms] ease-[cubic-bezier(0.2,0.7,0.2,1)] ${
            zoomed ? 'scale-[1.06] md:scale-[1]' : 'scale-100'
          }`}
        >
          <Image
            src={terminalImage}
            alt="Terminal workstation initial"
            fill
            priority
            className={`object-contain transition-all duration-[1200ms] ease-[cubic-bezier(0.2,0.7,0.2,1)] ${
              showFinalTerminal ? 'scale-[1.08] opacity-0 blur-[1px]' : 'scale-100 opacity-100 blur-0'
            }`}
          />
          <Image
            src={terminalFinalImage}
            alt="Terminal workstation final"
            fill
            priority
            className={`object-contain transition-all duration-[1200ms] ease-[cubic-bezier(0.2,0.7,0.2,1)] ${
              showFinalTerminal ? 'scale-100 opacity-100 blur-0' : 'scale-[0.94] opacity-0 blur-[2px]'
            }`}
          />

          <section className="absolute left-[19%] top-[13%] h-[47%] w-[62%] rounded-md border border-[#2b7a3a]/35 bg-[#020804]/90 shadow-[0_0_16px_rgba(0,255,128,0.12)]">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-[#2b7a3a]/35 px-3 py-2 text-xs text-[#86de9b]">
                <div className="flex gap-2">
                  {(['narrative', 'dossier', 'signals', 'controls'] as TabId[]).map((id) => (
                    <button
                      key={id}
                      onClick={() => setTab(id)}
                      className={`rounded px-2 py-1 uppercase tracking-wider ${
                        tab === id ? 'bg-[#0f2a14] text-[#acffbd]' : 'text-[#69c67f]'
                      }`}
                    >
                      {id}
                    </button>
                  ))}
                </div>
                {game && <span>Round {game.summary.current_round}/{game.summary.max_rounds}</span>}
              </div>

              {!game && (
                <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
                  <p className="text-sm text-[#93f6ab]">Night settles over the compound. Six contestants enter. One will control the room.</p>
                  <div className="grid w-full max-w-lg gap-2 md:grid-cols-[1fr_120px_140px]">
                    <input
                      value={playerName}
                      onChange={(e) => setPlayerName(e.target.value)}
                      className="rounded border border-[#2b7a3a]/45 bg-[#061008] px-3 py-2 text-xs text-[#9cf8ae]"
                      placeholder="Your alias"
                    />
                    <select
                      value={maxRounds}
                      onChange={(e) => setMaxRounds(Number(e.target.value))}
                      className="rounded border border-[#2b7a3a]/45 bg-[#061008] px-2 py-2 text-xs text-[#9cf8ae]"
                    >
                      <option value={6}>6 rounds</option>
                      <option value={7}>7 rounds</option>
                      <option value={8}>8 rounds</option>
                    </select>
                    <button
                      onClick={onStart}
                      disabled={loading}
                      className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-3 py-2 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                    >
                      {loading ? 'Entering...' : 'Enter House'}
                    </button>
                  </div>
                </div>
              )}

              {game && (
                <>
                  {tab === 'narrative' && (
                    <div className="flex min-h-0 flex-1 flex-col">
                      <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-3 text-sm text-[#8de7a2]">
                        {narrativeLines.length === 0 && <p>The game has not begun.</p>}
                        {narrativeLines.map((line, idx) => (
                          <p key={`${idx}-${line.slice(0, 10)}`}>{line}</p>
                        ))}
                      </div>
                      <div className="border-t border-[#2b7a3a]/35 px-3 py-2">
                        <textarea
                          value={playerText}
                          onChange={(e) => setPlayerText(e.target.value)}
                          rows={2}
                          className="w-full rounded border border-[#2b7a3a]/45 bg-[#061008] px-3 py-2 text-sm text-[#9cf8ae]"
                          placeholder="Type what you say to the group..."
                        />
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <button
                            onClick={onStoryTurn}
                            disabled={loading || !playerText.trim() || game.summary.status !== 'active'}
                            className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                          >
                            {loading ? 'Thinking...' : 'Send'}
                          </button>
                          <select
                            value={dialogueSpeakerId}
                            onChange={(e) => setDialogueSpeakerId(e.target.value)}
                            className="rounded border border-[#2b7a3a]/45 bg-[#061008] px-2 py-1.5 text-xs text-[#9cf8ae]"
                          >
                            {aliveTargets.map((t) => (
                              <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                          </select>
                          <button
                            onClick={onGenerateFlavorDialogue}
                            disabled={loading || aliveTargets.length === 0}
                            className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                          >
                            Trigger Dialogue
                          </button>
                          {game.summary.status === 'completed' && (
                            <button
                              onClick={onGenerateLLMSummary}
                              disabled={loading}
                              className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                            >
                              Debrief
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {tab === 'dossier' && (
                    <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-3 text-xs text-[#8de7a2]">
                      {Object.entries(game.state.participants).map(([id, p]) => (
                        <article key={id} className="rounded border border-[#2b7a3a]/45 bg-[#061008] p-2">
                          <p className="font-semibold text-[#aafebd]">{p.name}{id === 'player' ? ' [YOU]' : ''}</p>
                          {p.occupation && <p>{p.occupation}</p>}
                          {p.persona && <p className="text-[#75cd8b]">{p.persona}</p>}
                          {p.backstory && <p className="mt-1 text-[#6cc482]">{p.backstory}</p>}
                          <p className="mt-1">Status: {p.eliminated_round ? `out in round ${p.eliminated_round}` : 'active'}</p>
                        </article>
                      ))}
                    </div>
                  )}

                  {tab === 'signals' && (
                    <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-3">
                      {analytics ? (
                        <>
                          <TimelineChart title="Trust" data={analytics.analytics.trust_timeline} />
                          <TimelineChart title="Suspicion" data={analytics.analytics.suspicion_timeline} />
                          {llmSummary && (
                            <pre className="rounded-md border border-[#2b7a3a]/45 bg-[#061008] p-3 text-xs text-[#88e79e] whitespace-pre-wrap">{llmSummary.text}</pre>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-[#78d18e]">Signals appear after the game concludes.</p>
                      )}
                    </div>
                  )}

                  {tab === 'controls' && (
                    <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-3 text-xs text-[#8de7a2]">
                      <p className="text-[#75cd8b]">Manual move override</p>
                      <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
                        <select
                          value={actionType}
                          onChange={(e) => setActionType(e.target.value)}
                          className="rounded border border-[#2b7a3a]/45 bg-[#061008] px-3 py-2 text-xs text-[#9cf8ae]"
                        >
                          {actions.map((a) => (
                            <option key={a.action_type} value={a.action_type}>{a.label}</option>
                          ))}
                        </select>
                        <select
                          value={targetId}
                          onChange={(e) => setTargetId(e.target.value)}
                          disabled={!selectedAction?.needs_target}
                          className="rounded border border-[#2b7a3a]/45 bg-[#061008] px-3 py-2 text-xs text-[#9cf8ae] disabled:opacity-50"
                        >
                          <option value="">Target</option>
                          {aliveTargets.map((t) => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                          ))}
                        </select>
                        <button
                          onClick={onManualAction}
                          disabled={loading || (selectedAction?.needs_target && !targetId)}
                          className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-3 py-2 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                        >
                          Execute
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}

              {error && <p className="border-t border-[#2b7a3a]/35 px-3 py-1 text-[11px] text-[#ff8f8f]">{error}</p>}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
