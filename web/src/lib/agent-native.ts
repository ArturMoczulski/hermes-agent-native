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
  removed_at?: string | null;
  model_selection?: ModelSelection | null;
  model_activity?: ModelActivity[];
  id: string;
  name: string;
  purpose: string;
  soul_revision: number;
  execution: "not_started" | AgentWork["state"];
  created_at: string;
  work: AgentWork | null;
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

export const agentsEndpoint = "/api/agent-native/agents";

export type WorkLimits = { timeout_seconds: number; max_iterations: number };

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

export type WorkResult = {
  id: string;
  item_id: string;
  outcome: "submitted" | "discovery" | "waiting" | "blocked";
  summary: string;
  evaluation: { report: string; source: "agent" };
  acceptance: "not_evaluated";
  outputs: OutputReference[];
  created_at: string;
};

export function outputVersionLink(agentId: string, output: OutputReference): string {
  return `/agents/${encodeURIComponent(agentId)}?output=${encodeURIComponent(output.output_id)}&version=${output.version}`;
}

export type AgentWork = {
  output_sections?: { item_id: string; status: "pending"; reason: "conditional_write_unavailable"; text: string;
    entries: { source_id: string; summary: string; comment_status: "pending" | "confirmed" | "failed" | "unknown"; link_url: string | null; link_label: string | null }[] }[];
  progress?: { operation_id: string; source_id: string; item_id: string; summary: string; status: "pending" | "confirmed" | "failed" | "unknown"; comment_id: string | null; created_at: string; link_url?: string | null; link_label?: string | null }[];
  model_selection?: ModelActivity | null;
  id: string;
  focus?: WorkFocus | null;
  state: "queued" | "preparing" | "running" | "stopping" | "paused" | "limit_reached" | "completed" | "failed" | "unknown";
  limits: WorkLimits;
  session_id: string;
  model_calls: number;
  events: { id: number; kind: string; summary: string; created_at: string }[];
  summary: string | null;
  error: string | null;
  stories: StoryMetadata[];
  outputs: OutputMetadata[];
  results: WorkResult[];
};

export function validWorkLimits(value: unknown): value is WorkLimits {
  if (!value || typeof value !== "object") return false;
  const limits = value as WorkLimits;
  return Number.isInteger(limits.timeout_seconds) && limits.timeout_seconds >= 1 && limits.timeout_seconds <= 3600
    && Number.isInteger(limits.max_iterations) && limits.max_iterations >= 1 && limits.max_iterations <= 100;
}

export function agentWorkStatus(agent: Agent): string {
  if (agent.removed_at) return "Removed";
  const work = agent.work;
  if (!work) return "Not started";
  if (work.state === "queued" && agent.setup?.status !== "ready") return "Waiting for setup";
  const labels: Record<AgentWork["state"], string> = {
    queued: "Queued", preparing: "Preparing", running: "Running", stopping: "Stopping",
    paused: "Paused", limit_reached: "Run limit reached", completed: "Completed", failed: "Failed", unknown: "Outcome unknown",
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
