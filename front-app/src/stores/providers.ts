import { defineStore } from "pinia";
import { api } from "@/api/client";
import type {
  AgentType,
  Provider,
  ProviderCreatePayload,
  ProviderUpdatePayload,
} from "@/types/api";

interface State {
  providers: Record<AgentType, Provider[]>;
  loading: Record<AgentType, boolean>;
}

export const useProvidersStore = defineStore("providers", {
  state: (): State => ({
    providers: { codex: [], claude_code: [] },
    loading: { codex: false, claude_code: false },
  }),
  actions: {
    async refresh(agentType: AgentType) {
      this.loading[agentType] = true;
      try {
        this.providers[agentType] = await api.listProviders(agentType);
      } finally {
        this.loading[agentType] = false;
      }
    },
    async create(agentType: AgentType, payload: ProviderCreatePayload) {
      const provider = await api.createProvider(agentType, payload);
      await this.refresh(agentType);
      return provider;
    },
    async update(agentType: AgentType, providerId: string, payload: ProviderUpdatePayload) {
      const provider = await api.updateProvider(agentType, providerId, payload);
      await this.refresh(agentType);
      return provider;
    },
    async remove(agentType: AgentType, providerId: string) {
      await api.deleteProvider(agentType, providerId);
      await this.refresh(agentType);
    },
    async revealApiKey(agentType: AgentType, providerId: string) {
      return api.revealProviderApiKey(agentType, providerId);
    },
    async apply(
      agentType: AgentType,
      providerId: string,
      opts: { dryRun: boolean; startProxy: boolean },
    ) {
      const result = await api.applyProvider(agentType, providerId, {
        dry_run: opts.dryRun,
        start_proxy: opts.startProxy,
      });
      await this.refresh(agentType);
      return result;
    },
    async startProxy(agentType: AgentType, providerId: string) {
      const status = await api.startProxy(providerId);
      await this.refresh(agentType);
      return status;
    },
    async stopProxy(agentType: AgentType, providerId: string) {
      const status = await api.stopProxy(providerId);
      await this.refresh(agentType);
      return status;
    },
    async restartProxy(agentType: AgentType, providerId: string) {
      const status = await api.restartProxy(providerId);
      await this.refresh(agentType);
      return status;
    },
  },
});
