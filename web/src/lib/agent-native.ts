export type Agent = {
  id: string;
  name: string;
  purpose: string;
  soul_revision: number;
  execution: "not_started";
  created_at: string;
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
