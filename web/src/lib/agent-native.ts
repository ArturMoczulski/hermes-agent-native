import { EFFORT_OPTIONS, VALID_EFFORTS } from "./reasoning-effort";

export type ModelChoice = { provider: string; model: string; reasoning_effort?: string };
export function reasoningEffortLabel(effort: string | undefined): string {
  return !effort || effort === "default" ? "Runtime automatic" : EFFORT_OPTIONS.find((option) => option.value === effort)?.label ?? effort;
}
export type ModelSelection = ModelChoice & {
  revision: number;
  source: "default" | "override" | "legacy";
  updated_at: string;
};
export type DefaultAgentModel = ModelChoice & { revision: number; updated_at: string };
export type ModelActivity = ModelChoice & {
  agent_id?: string;
  kind: "work" | "chat";
  attempt_id: string;
  revision: number;
  source: ModelSelection["source"];
  created_at: string;
};
export const agentModelsEndpoint = "/api/agent-native/models";
export function modelChoiceLabel(choice: ModelChoice | null | undefined): string {
  return choice?.provider && choice.model ? `${choice.provider} · ${choice.model} · Reasoning: ${reasoningEffortLabel(choice.reasoning_effort)}` : "Model not configured";
}
export function validModelChoice(value: unknown): value is ModelChoice {
  if (!value || typeof value !== "object") return false;
  const choice = value as ModelChoice;
  return typeof choice.provider === "string" && !!choice.provider.trim() && choice.provider.length <= 256
    && typeof choice.model === "string" && !!choice.model.trim() && choice.model.length <= 256
    && Array.from(choice.provider + choice.model).every((character) => character.charCodeAt(0) >= 32)
    && (choice.reasoning_effort === undefined || choice.reasoning_effort === "default" || VALID_EFFORTS.has(choice.reasoning_effort));
}

export type Agent = {
  parent_id: string | null;
  child_ids: string[];
  removed_at?: string | null;
  retirement?: { evaluation_id?: string | null; replacement_id?: string | null; source: "agent" | "parent" | "owner"; decision_agent_id?: string; retired_at: string } | null;
  replacement?: { id: string; role: "predecessor" | "successor"; predecessor_id?: string; successor_id?: string; reason: string; handoff: string; created_at: string } | null;
  pause?: { paused: boolean; sources: { source_agent_id: string; requested_at: string }[] };
  subtree_pause?: { source_agent_id: string; affected_agent_ids: string[]; newly_paused_agent_ids: string[]; stopping_agent_ids: string[] };
  subtree_resume?: { source_agent_id: string; affected_agent_ids: string[]; resumed_agent_ids: string[]; still_paused_agent_ids: string[]; cadence_restored_agent_ids: string[] };
  model_selection?: ModelSelection | null;
  project_workspace?: { root: string; revision: number; active: boolean } | null;
  project_preview?: { relative_root: string; revision: number; published_at: string; url: string } | null;
  model_activity?: ModelActivity[];
  autonomy: AutonomySettings;
  id: string;
  name: string;
  purpose: string;
  soul_revision: number;
  execution: "not_started" | AgentWork["state"];
  created_at: string;
  work: AgentWork | null;
  usage: { agent: UsageTotals; subtree: UsageTotals };
  cadence?: { enabled: boolean; interval_seconds: number | null; next_due: string | null };
  automatic_work?: {
    state: "ready" | "working" | "scheduled" | "waiting_retry" | "owner_paused" | "waiting_owner_review" | "waiting_owner_answer" | "owner_attention" | "framework_reconciliation" | "framework_failure" | "automatic_off" | "setup" | "not_configured" | "retired" | "removed";
    may_start: boolean;
    blocker: string | null;
    release_condition: string | null;
    responsible_actor: "owner" | "framework" | null;
  };
  cadence_skip?: {
    state: string;
    blocker: string | null;
    release_condition: string | null;
    responsible_actor: "owner" | "framework" | null;
    overdue_since: string;
    observed_at: string;
  } | null;
  progress_concerns?: ProgressConcern[];
  progress_concern_settings?: { failure_threshold: number };
  assignment_review_policies?: { agent_id:string; item_id:string; assignment_fingerprint:string; required:boolean; revision:number; updated_at:string }[];
  setup: {
    activation_id: string;
    status: "queued" | "preparing" | "blocked" | "failed" | "unresolved" | "ready" | "superseded";
    phase: "files" | "workspace" | "project" | "discovery" | "ready";
    files_ready: boolean;
    plane_origin: string | null;
    workspace_slug: string | null;
    workspace_id: string | null;
    project_id: string | null;
    discovery_item_id: string | null;
    message: string;
    updated_at: string;
    events: { sequence: number; message: string; created_at: string }[];
  } | null;
  startup: {
    id: string;
    cause: "creation";
    soul_revision: number;
    requested_at: string;
  } | null;
};

export type ProgressConcern = {
  id: string;
  kind: "repeated_unproductive_failure" | "repeated_empty_completion";
  status: "open" | "resolved";
  attempt_ids: string[];
  summary: string;
  created_at: string;
  resolved_at: string | null;
  response: string | null;
};

export type AutonomySettings = { level: number; require_owner_review: boolean; revision: number; updated_at: string | null };
export const autonomyLabels: Record<number, string> = {
  1: "1 · Approval-driven", 2: "2 · Cautious", 3: "3 · Balanced",
  4: "4 · Proactive", 5: "5 · Highly autonomous",
};

export const agentsEndpoint = "/api/agent-native/agents";

export type WorkLimits = { timeout_seconds: number; max_iterations: number };

export type UsageTotals = {
  record_count: number;
  api_calls: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  reasoning_tokens: number;
  estimated_cost_usd: number | null;
  actual_cost_usd: number | null;
  cost_kind: "measured" | "estimated" | "included" | "unavailable";
};

export type RunUsage = Omit<UsageTotals, "record_count" | "cost_kind"> & {
  run_id: string;
  agent_id: string;
  provider: string;
  model: string;
  cost_status: "known" | "estimated" | "included" | "free" | "unknown";
  cost_source: string;
  recorded_at: string;
};

export type StoryMetadata = {
  story_id: string;
  version: number;
  title: string;
  item_id: string;
  relative_path: string;
  evaluation: string | Record<string, unknown> | null;
  created_at: string;
};

export type StoryVersion = StoryMetadata & { content: string };

export type OutputReference = { output_id: string; version: number };

export type OutputMetadata = OutputReference & {
  agent_id: string;
  run_id: string;
  item_id: string;
  title: string;
  format: "markdown" | "text";
  relative_path: string;
  content_sha256: string;
  created_at: string;
  evaluation?: string | Record<string, unknown> | null;
};

export type OutputVersion = OutputMetadata & { content: string };

export type MediaOutput = {
  artifact_id: string;
  agent_id: string;
  run_id: string;
  item_id: string;
  title: string;
  filename: string;
  mime_type: string;
  content_sha256: string;
  byte_count: number;
  created_at: string;
};

export type WorkResult = {
  id: string;
  run_id: string;
  item_id: string;
  criteria_revision: string;
  outcome: "submitted" | "discovery" | "waiting" | "blocked";
  summary: string;
  evaluation: { report: string; source: "agent" };
  acceptance: "not_evaluated" | "accepted" | "revision_requested";
  review: { required: boolean; source: "autonomy" | "owner_policy" | "assignment_policy" | "legacy"; reason: string | null };
  owner_decision?: { id: string; decision: "accepted" | "revision_requested"; note: string | null; created_at: string } | null;
  outputs: OutputReference[];
  created_at: string;
};

export function outputVersionLink(agentId: string, output: OutputReference): string {
  return `/agents/${encodeURIComponent(agentId)}?output=${encodeURIComponent(output.output_id)}&version=${output.version}`;
}

export type AgentWork = {
  purpose_evaluations?: { id:string; run_id:string; soul_revision:number; purpose:string; judgment:"continue"|"wait"|"clarify"|"retire_candidate"; evidence:string[]; remaining_obligations:string[]; uncertainty:string|null; next_action:string; question_id:string|null; created_at:string }[];
  output_sections?: { item_id: string; status: "pending"; reason: "conditional_write_unavailable"; text: string;
    entries: { source_id: string; summary: string; comment_status: "pending" | "confirmed" | "failed" | "unknown"; link_url: string | null; link_label: string | null }[] }[];
  progress?: { operation_id: string; source_id: string; item_id: string; summary: string; status: "pending" | "confirmed" | "failed" | "unknown"; comment_id: string | null; created_at: string; link_url?: string | null; link_label?: string | null }[];
  model_selection?: ModelActivity | null;
  id: string;
  focus?: WorkFocus | null;
  state: "queued" | "preparing" | "running" | "stopping" | "paused" | "interrupted" | "limit_reached" | "completed" | "retryable_failure" | "failed" | "unknown";
  limits: WorkLimits;
  session_id: string;
  model_calls: number;
  events: { id: number; kind: string; summary: string; created_at: string; detail?: Record<string, unknown> | null }[];
  summary: string | null;
  error: string | null;
  stories: StoryMetadata[];
  outputs: OutputMetadata[];
  media_outputs: MediaOutput[];
  results: WorkResult[];
  usage: RunUsage | null;
  usage_by_run: Record<string, RunUsage>;
};

export function validWorkLimits(value: unknown): value is WorkLimits {
  if (!value || typeof value !== "object") return false;
  const limits = value as WorkLimits;
  return Number.isInteger(limits.timeout_seconds) && limits.timeout_seconds >= 1 && limits.timeout_seconds <= 3600
    && Number.isInteger(limits.max_iterations) && limits.max_iterations >= 1 && limits.max_iterations <= 100;
}

export function agentWaitingForOwner(agent: Agent): boolean {
  const work = agent.work;
  if (!work) return false;
  const latestEvaluation = work.purpose_evaluations?.[0];
  const requiredReview = work.results.some(result => result.review.required && !result.owner_decision);
  return requiredReview || latestEvaluation?.judgment === "clarify";
}

export function agentWorkStatus(agent: Agent): string {
  if (agent.retirement) return "Retired";
  if (agent.removed_at) return "Removed";
  if (agent.automatic_work?.state === "owner_paused") return "Paused";
  if (agent.automatic_work?.state === "waiting_owner_review" || agent.automatic_work?.state === "waiting_owner_answer") return "Needs your decision";
  if (agent.automatic_work?.state === "waiting_retry") return "Waiting to retry";
  if (agent.automatic_work?.state === "framework_reconciliation") return "Framework recovery needed";
  if (agent.automatic_work?.state === "framework_failure") return "Framework failure";
  if (agent.automatic_work?.state === "owner_attention") return "Needs your attention";
  if (agent.automatic_work?.state === "scheduled") return "Active · waiting for next check-in";
  const work = agent.work;
  if (!work) return "Not started";
  if (work.state === "queued" && agent.setup?.status !== "ready") return "Waiting for setup";
  if (agent.cadence?.enabled && ["interrupted", "retryable_failure"].includes(work.state)) {
    return "Recovering · waiting for next check-in";
  }
  if (agent.cadence?.enabled && work.state === "paused") {
    return "Active · reconsidering after pause";
  }
  if (!agent.pause?.paused && work.state === "paused") {
    return "Automatic work off";
  }
  if (agent.cadence?.enabled && ["completed", "limit_reached"].includes(work.state)) {
    return agentWaitingForOwner(agent)
      ? "Active · waiting for your decision"
      : "Active · waiting for next check-in";
  }
  if (agent.cadence && !agent.cadence.enabled && ["completed", "limit_reached"].includes(work.state)) {
    return "Automatic work off";
  }
  const labels: Record<AgentWork["state"], string> = {
    queued: "Queued", preparing: "Preparing", running: "Running", stopping: "Stopping",
    paused: "Paused", interrupted: "Interrupted", limit_reached: "Run limit reached", completed: "Completed",
    retryable_failure: "Retry scheduled", failed: "Failed", unknown: "Outcome unknown",
  };
  return labels[work.state];
}

export type WorkFocus = {
  selection_id: string;
  item_id: string;
  cycle_id: string | null;
  name: string;
  description_html: string | null;
  selected_at: string;
  soul_revision: number;
  run_id: string;
};

export type AgentPlanning = {
  agent_id: string;
  soul_revision: number;
  setup_activation_id: string;
  observed_at: string;
  plane_origin: string;
  workspace_slug: string;
  project: { id: string; name: string; description?: string | null };
  items: { id: string; name: string; description_html?: string | null; state?: string | null }[];
  cycles: { id: string; name: string; description?: string | null }[];
  states: { id: string; name: string; group?: string }[];
};
