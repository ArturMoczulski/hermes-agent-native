import { describe, expect, it } from "vitest";

import { agentWorkStatus, type Agent } from "./agent-native";

describe("agentWorkStatus", () => {
  it("renders the retry-wait readiness decision instead of inferring from work state", () => {
    const agent = {
      automatic_work: {
        state: "waiting_retry",
        may_start: false,
        blocker: "Waiting for the automatic retry backoff to elapse.",
        release_condition:
          "The next automatic retry becomes eligible at 2099-01-01T00:00:06+00:00.",
        responsible_actor: "framework",
      },
    } as unknown as Agent;

    expect(agentWorkStatus(agent)).toBe("Waiting to retry");
  });
});
