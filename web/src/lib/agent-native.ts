export type Agent = {
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

export type AgentWork = {
  id: string;
  state: "queued" | "preparing" | "running" | "stopping" | "paused" | "completed" | "failed" | "unknown";
  limits: WorkLimits;
  session_id: string;
  model_calls: number;
  events: { id: number; kind: string; summary: string; created_at: string }[];
  summary: string | null;
  error: string | null;
  stories: StoryMetadata[];
};

export function validWorkLimits(value: unknown): value is WorkLimits {
  if (!value || typeof value !== "object") return false;
  const limits = value as WorkLimits;
  return Number.isInteger(limits.timeout_seconds) && limits.timeout_seconds >= 1 && limits.timeout_seconds <= 3600
    && Number.isInteger(limits.max_iterations) && limits.max_iterations >= 1 && limits.max_iterations <= 100;
}

export function agentWorkStatus(agent: Agent): string {
  const work = agent.work;
  if (!work) return "Not started";
  if (work.state === "queued" && agent.setup?.status !== "ready") return "Waiting for setup";
  const labels: Record<AgentWork["state"], string> = {
    queued: "Queued", preparing: "Preparing", running: "Running", stopping: "Stopping",
    paused: "Paused", completed: "Completed", failed: "Failed", unknown: "Outcome unknown",
  };
  return labels[work.state];
}
