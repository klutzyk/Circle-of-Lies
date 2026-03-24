export type Participant = {
  name: string;
  is_human: boolean;
  traits: Record<string, number>;
  occupation?: string;
  backstory?: string;
  persona?: string;
  eliminated_round: number | null;
};

export type RoundLog = {
  round_number: number;
  event: string;
  player_action: { actor_id: string; action_type: string; target_id: string };
  ai_actions: { actor_id: string; action_type: string; target_id: string }[];
  votes: Record<string, string>;
  eliminated_id: string | null;
  summary: {
    player_avg_trust: number;
    player_avg_suspicion: number;
    alive_after_vote: string[];
  };
};

export type GamePayload = {
  summary: {
    game_id: string;
    current_round: number;
    max_rounds: number;
    status: string;
    phase: string;
    winner: string | null;
  };
  state: {
    participants: Record<string, Participant>;
    trust: Record<string, Record<string, number>>;
    suspicion: Record<string, Record<string, number>>;
    alliances: string[][];
    current_event: string;
    history: RoundLog[];
    story_events?: {
      round_number: number;
      scene_step: number;
      player_text: string;
      narration: string;
      dialogue: { speaker_id: string; speaker_name: string; line: string }[];
      eliminated_id: string | null;
      summary: {
        player_avg_trust: number;
        player_avg_suspicion: number;
        alive_after_vote: string[];
      };
    }[];
  };
};

export type ActionCatalogItem = {
  action_type: string;
  label: string;
  needs_target: boolean;
  description: string;
};

export type AnalyticsPayload = {
  game_id: string;
  analytics: {
    survived: boolean;
    winner: string | null;
    strategy_archetype: string;
    trust_timeline: { round: number; value: number }[];
    suspicion_timeline: { round: number; value: number }[];
    turning_points: { round: number; type: string; delta: number; reason: string }[];
    outcome_reason: string;
    game_theory_tags: string[];
  };
};

export type LLMEnhancementPayload = {
  game_id: string;
  use_case: string;
  text: string;
  provider: string;
  model: string;
  cached: boolean;
  enabled: boolean;
  reason: string;
};

export type StoryTurnPayload = GamePayload & {
  story: {
    player_text: string;
    interpreted_action: string;
    interpreted_target_id: string;
    narration: string;
    dialogue?: { speaker_id: string; speaker_name: string; line: string }[];
    vote_resolved?: boolean;
    llm_error?: string;
  };
};
