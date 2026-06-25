import { defineStore } from "pinia";
import { api } from "@/api/client";
import type { AgentInfo, AgentType, ConfigCheckResult } from "@/types/api";

interface State {
  agents: Record<AgentType, AgentInfo | null>;
  configChecks: Record<AgentType, ConfigCheckResult | null>;
  loading: boolean;
}

export const useAgentsStore = defineStore("agents", {
  state: (): State => ({
    agents: { codex: null, claude_code: null },
    configChecks: { codex: null, claude_code: null },
    loading: false,
  }),
  getters: {
    list(state): AgentInfo[] {
      return [state.agents.codex, state.agents.claude_code].filter(
        (a): a is AgentInfo => a !== null,
      );
    },
  },
  actions: {
    async refresh() {
      this.loading = true;
      try {
        const list = await api.listAgents();
        for (const agent of list) {
          this.agents[agent.agent_type] = agent;
        }
      } finally {
        this.loading = false;
      }
    },
    async setConfigPath(agentType: AgentType, path: string) {
      const agent = await api.setConfigPath(agentType, path);
      this.agents[agentType] = agent;
      return agent;
    },
    async probe(agentType: AgentType) {
      const agent = await api.probeAgent(agentType);
      this.agents[agentType] = agent;
      return agent;
    },
    async configCheck(agentType: AgentType) {
      const result = await api.configCheck(agentType);
      this.configChecks[agentType] = result;
      this.agents[agentType] = result.agent;
      return result;
    },
  },
});
