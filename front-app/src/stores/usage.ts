import { defineStore } from "pinia";
import { api } from "@/api/client";
import type { AgentType, UsageRecord } from "@/types/api";

interface State {
  usage: Record<AgentType, Record<string, UsageRecord>>;
}

export const useUsageStore = defineStore("usage", {
  state: (): State => ({
    usage: { codex: {}, claude_code: {} },
  }),
  actions: {
    async refresh(agentType: AgentType) {
      this.usage[agentType] = await api.listUsage(agentType);
    },
    async resetAgent(agentType: AgentType) {
      this.usage[agentType] = await api.resetAgentUsage(agentType);
      return this.usage[agentType];
    },
    async reset(agentType: AgentType, providerId: string) {
      const record = await api.resetUsage(agentType, providerId);
      this.usage[agentType] = { ...this.usage[agentType], [providerId]: record };
      return record;
    },
  },
});
