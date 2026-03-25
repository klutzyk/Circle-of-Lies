'use client';

import Image from 'next/image';
import { useEffect, useMemo, useRef, useState } from 'react';

import terminalImage from '../../assets/terminal.jpg';
import terminalFinalImage from '../../assets/terminal4.jpg';
import {
  fetchAnalytics,
  fetchPostGameLLMAnalysis,
  startGame,
  submitStoryTurn,
} from '@/lib/api';
import { AnalyticsPayload, GamePayload, LLMEnhancementPayload } from '@/types/game';

type TabId = 'narrative' | 'characters' | 'signals';
type NarrativeEntry =
  | { type: 'narration'; text: string }
  | { type: 'dialogue'; speakerId: string; speakerName: string; text: string }
  | { type: 'event'; text: string };

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
  const [playerText, setPlayerText] = useState('I want to stay calm and align with someone reliable this round.');
  const [analytics, setAnalytics] = useState<AnalyticsPayload | null>(null);
  const [llmSummary, setLlmSummary] = useState<LLMEnhancementPayload | null>(null);
  const [tab, setTab] = useState<TabId>('narrative');
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const [showFinalTerminal, setShowFinalTerminal] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [revealCounts, setRevealCounts] = useState<number[]>([]);
  const previousNarrativeRef = useRef<string[]>([]);
  const narrativeScrollRef = useRef<HTMLDivElement | null>(null);

  const narrativeEntries = useMemo(() => {
    if (!game) return [] as NarrativeEntry[];
    const entries: NarrativeEntry[] = [];
    const events = game.state.story_events ?? [];
    for (const event of events) {
      if (event.narration) {
        entries.push({ type: 'narration', text: event.narration });
      }
      for (const line of event.dialogue ?? []) {
        const label =
          line.speaker_name?.trim() || game.state.participants[line.speaker_id]?.name || 'Unknown';
        entries.push({
          type: 'dialogue',
          speakerId: line.speaker_id,
          speakerName: label,
          text: line.line,
        });
      }
      if (event.eliminated_id) {
        const eliminatedName = game.state.participants[event.eliminated_id]?.name || event.eliminated_id;
        entries.push({
          type: 'event',
          text: `${eliminatedName} is forced out as the room falls into uneasy silence.`,
        });
      }
    }
    return entries;
  }, [game]);

  const narrativeLines = useMemo(() => narrativeEntries.map((entry) => entry.text), [narrativeEntries]);

  useEffect(() => {
    setRevealCounts((prev) => {
      const next = new Array(narrativeLines.length).fill(0);
      let idx = 0;
      while (
        idx < prev.length &&
        idx < narrativeLines.length &&
        previousNarrativeRef.current[idx] === narrativeLines[idx]
      ) {
        next[idx] = Math.min(prev[idx], narrativeLines[idx].length);
        idx += 1;
      }
      return next;
    });
    previousNarrativeRef.current = narrativeLines;
  }, [narrativeLines]);

  useEffect(() => {
    const hasIncompleteLine = narrativeEntries.some(
      (line, idx) => (revealCounts[idx] ?? 0) < line.text.length
    );
    if (!hasIncompleteLine) return;

    const timer = window.setInterval(() => {
      setRevealCounts((current) => {
        const next = current.slice();
        const lineIdx = narrativeLines.findIndex(
          (line, idx) => (next[idx] ?? 0) < line.length
        );
        if (lineIdx === -1) return current;
        const currentCount = next[lineIdx] ?? 0;
        next[lineIdx] = Math.min(currentCount + 1, narrativeEntries[lineIdx].text.length);
        return next;
      });
    }, 12);

    return () => window.clearInterval(timer);
  }, [narrativeEntries, revealCounts]);

  useEffect(() => {
    if (!narrativeScrollRef.current) return;
    narrativeScrollRef.current.scrollTop = narrativeScrollRef.current.scrollHeight;
  }, [narrativeEntries, revealCounts]);

  const knownIntelByCharacter = useMemo(() => {
    if (!game) return {} as Record<string, { quotes: string[]; disclosures: string[]; behaviors: string[] }>;
    const result: Record<string, { quotes: string[]; disclosures: string[]; behaviors: string[] }> = {};
    const init = (id: string) => {
      if (!result[id]) result[id] = { quotes: [], disclosures: [], behaviors: [] };
      return result[id];
    };

    for (const event of game.state.story_events ?? []) {
      for (const d of event.dialogue ?? []) {
        if (!d.speaker_id || !d.line) continue;
        const intel = init(d.speaker_id);
        if (!intel.quotes.includes(d.line)) intel.quotes.push(d.line);
        const disclosureMatches = d.line.match(
          /\b(i am|i was|i have|i work|i used to|my family|my job|my team|i don't trust|i trust)\b[^.?!]{0,80}/gi
        );
        for (const match of disclosureMatches ?? []) {
          const clean = match.trim();
          if (clean && !intel.disclosures.includes(clean)) intel.disclosures.push(clean);
        }
      }
    }

    for (const round of game.state.history ?? []) {
      for (const action of round.ai_actions ?? []) {
        const actorId = action.actor_id;
        if (!actorId || actorId === 'player') continue;
        const intel = init(actorId);
        const behaviorMap: Record<string, string> = {
          accuse: 'Publicly accuses rivals',
          defend: 'Steps in to defend allies',
          quiet: 'Stays guarded under pressure',
          share_info: 'Shares selective information',
          build_alliance: 'Actively builds alliances',
          spread_doubt: 'Seeds doubt about others',
        };
        const label = behaviorMap[action.action_type] ?? '';
        if (label && !intel.behaviors.includes(label)) intel.behaviors.push(label);
      }
    }

    return result;
  }, [game]);

  const characterColorClass = (speakerId: string) => {
    const palette = [
      'text-[#8de7a2]',
      'text-[#8ad6ff]',
      'text-[#ffd27a]',
      'text-[#f9a8d4]',
      'text-[#c4b5fd]',
      'text-[#fca5a5]',
      'text-[#86efac]',
    ];
    if (speakerId === 'player') return 'text-[#7fffd4]';
    const match = /ai_(\d+)/.exec(speakerId);
    const idx = match ? Math.max(0, Number(match[1]) - 1) : 0;
    return palette[idx % palette.length];
  };

  const avatarGradientClass = (participantId: string) => {
    const palette = [
      'from-[#1f2937] to-[#065f46]',
      'from-[#312e81] to-[#0e7490]',
      'from-[#3f3f46] to-[#7c2d12]',
      'from-[#14532d] to-[#1d4ed8]',
      'from-[#3b0764] to-[#164e63]',
    ];
    const match = /(\d+)/.exec(participantId);
    const idx = match ? Number(match[1]) - 1 : 0;
    return palette[((idx % palette.length) + palette.length) % palette.length];
  };

  async function onStart() {
    setError('');
    setLoading(true);
    try {
      const started = await startGame(playerName.trim() || 'Operator', maxRounds);
      setGame(started);
      setAnalytics(null);
      setLlmSummary(null);
      setTab('narrative');
      setZoomed(true);
      setShowFinalTerminal(false);
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
      if (next.story?.llm_error) {
        setError(`LLM turn issue: ${next.story.llm_error}`);
      }
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

          <section className="absolute left-[19%] top-[10%] h-[60%] w-[62%] rounded-md border border-[#2b7a3a]/35 bg-[#020804]/90 shadow-[0_0_16px_rgba(0,255,128,0.12)]">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-[#2b7a3a]/35 px-3 py-2 text-xs text-[#86de9b]">
                <div className="flex gap-2">
                  {(['narrative', 'characters', 'signals'] as TabId[]).map((id) => (
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
                      <div
                        ref={narrativeScrollRef}
                        className="min-h-0 flex-1 space-y-3 overflow-auto px-4 py-4 text-[13px] leading-relaxed text-[#8de7a2]"
                      >
                        {narrativeEntries.length === 0 && <p>The game has not begun.</p>}
                        {narrativeEntries.map((entry, idx) => {
                          const revealedText = entry.text.slice(0, revealCounts[idx] ?? 0);
                          if (entry.type === 'dialogue') {
                            return (
                              <p key={`${idx}-${entry.speakerId}`}>
                                <button
                                  onClick={() => {
                                    setSelectedCharacterId(entry.speakerId);
                                    setTab('characters');
                                  }}
                                  className={`font-semibold underline-offset-2 hover:underline ${characterColorClass(entry.speakerId)}`}
                                >
                                  {entry.speakerName}
                                </button>
                                <span className="text-[#8de7a2]">: {revealedText}</span>
                              </p>
                            );
                          }
                          const extraClass = entry.type === 'event' ? 'text-[#f9d48a]' : 'text-[#8de7a2]';
                          return (
                            <p key={`${idx}-${entry.type}`} className={extraClass}>
                              {revealedText}
                            </p>
                          );
                        })}
                      </div>
                      <div className="border-t border-[#2b7a3a]/35 px-3 py-2">
                        <div className="flex items-center gap-2">
                        <input
                          value={playerText}
                          onChange={(e) => setPlayerText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              if (!loading && playerText.trim() && game.summary.status === 'active') {
                                void onStoryTurn();
                              }
                            }
                          }}
                          className="w-full rounded border border-[#2b7a3a]/45 bg-[#061008] px-3 py-2 text-base text-[#9cf8ae]"
                          placeholder="Type what you say to the group..."
                        />
                          <button
                            onClick={onStoryTurn}
                            disabled={loading || !playerText.trim() || game.summary.status !== 'active'}
                            className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-4 py-2 text-sm font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                          >
                            {loading ? '...' : 'Enter'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {tab === 'characters' && (
                    <div className="min-h-0 flex flex-1 gap-3 overflow-hidden px-3 py-3 text-xs text-[#8de7a2]">
                      <aside className="w-52 shrink-0 space-y-2 overflow-auto pr-1">
                        {Object.entries(game.state.participants)
                          .filter(([id]) => id !== 'player')
                          .map(([id, p]) => (
                            <button
                              key={id}
                              onClick={() => setSelectedCharacterId(id)}
                              className={`flex w-full items-center gap-2 rounded border px-2 py-2 text-left ${
                                selectedCharacterId === id
                                  ? 'border-[#7aff95]/70 bg-[#0e1d11]'
                                  : 'border-[#2b7a3a]/45 bg-[#061008]'
                              }`}
                            >
                              <div
                                className={`flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br text-[11px] font-bold text-white ${avatarGradientClass(id)}`}
                              >
                                {p.name.slice(0, 2).toUpperCase()}
                              </div>
                              <div className="min-w-0">
                                <p className="truncate font-semibold text-[#aafebd]">{p.name}</p>
                                <p className="truncate text-[10px] text-[#75cd8b]">
                                  {p.eliminated_round ? `out (r${p.eliminated_round})` : 'active'}
                                </p>
                              </div>
                            </button>
                          ))}
                      </aside>

                      <section className="min-w-0 flex-1 overflow-auto rounded border border-[#2b7a3a]/45 bg-[#061008] p-3">
                        {(() => {
                          const fallbackId =
                            selectedCharacterId && game.state.participants[selectedCharacterId] && selectedCharacterId !== 'player'
                              ? selectedCharacterId
                              : Object.keys(game.state.participants).find((id) => id !== 'player');
                          if (!fallbackId) return <p>No characters available.</p>;
                          const p = game.state.participants[fallbackId];
                          const intel = knownIntelByCharacter[fallbackId] ?? {
                            quotes: [],
                            disclosures: [],
                            behaviors: [],
                          };
                          return (
                            <div className="space-y-3">
                              <div className="flex items-center gap-3">
                                <div
                                  className={`flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white ${avatarGradientClass(fallbackId)}`}
                                >
                                  {p.name.slice(0, 2).toUpperCase()}
                                </div>
                                <div>
                                  <p className="text-sm font-semibold text-[#aafebd]">{p.name}</p>
                                  <p className="text-[11px] text-[#75cd8b]">
                                    Status: {p.eliminated_round ? `out in round ${p.eliminated_round}` : 'active'}
                                  </p>
                                </div>
                              </div>

                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9cf8ae]">
                                  Known Facts
                                </p>
                                <p className="mt-1 text-[12px] text-[#87df9d]">
                                  {intel.disclosures.length > 0
                                    ? intel.disclosures.slice(0, 4).join(' | ')
                                    : 'Unknown. No clear self-disclosure yet.'}
                                </p>
                              </div>

                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9cf8ae]">
                                  Observed Behavior
                                </p>
                                <p className="mt-1 text-[12px] text-[#87df9d]">
                                  {intel.behaviors.length > 0
                                    ? intel.behaviors.slice(0, 4).join(' | ')
                                    : 'Insufficient evidence. Keep interacting.'}
                                </p>
                              </div>

                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9cf8ae]">
                                  Recent Quotes
                                </p>
                                {intel.quotes.length > 0 ? (
                                  <div className="mt-1 space-y-1">
                                    {intel.quotes.slice(-4).map((q, i) => (
                                      <p key={`${i}-${q.slice(0, 12)}`} className="text-[12px] text-[#8de7a2]">
                                        "{q}"
                                      </p>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="mt-1 text-[12px] text-[#87df9d]">
                                    No recorded quotes yet.
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })()}
                      </section>
                    </div>
                  )}

                  {tab === 'signals' && (
                    <div className="min-h-0 flex-1 space-y-2 overflow-auto px-3 py-3">
                      <div className="flex justify-end">
                        <button
                          onClick={onGenerateLLMSummary}
                          disabled={loading || game.summary.status !== 'completed'}
                          className="rounded border border-[#2b7a3a]/45 bg-[#0a200f] px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-[#9cf8ae] disabled:opacity-50"
                        >
                          Strategic Debrief
                        </button>
                      </div>
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
