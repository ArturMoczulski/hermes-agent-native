export type Agent = {
  id: string;
  name: string;
  purpose: string;
  soul_revision: number;
  execution: "not_started";
  created_at: string;
  startup: {
    id: string;
    cause: "creation";
    soul_revision: number;
    requested_at: string;
  } | null;
};

export const agentsEndpoint = "/api/agent-native/agents";
