<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import AppShell from "./layouts/AppShell.vue";
import { useAppStore } from "./stores/app";
import { useAgentsStore } from "./stores/agents";
import { useProvidersStore } from "./stores/providers";
import { useUsageStore } from "./stores/usage";

const appStore = useAppStore();
const agents = useAgentsStore();
const providers = useProvidersStore();
const usage = useUsageStore();

let pollHandle: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  await appStore.checkHealth();
  await agents.refresh();
  await Promise.all([
    providers.refresh("codex"),
    providers.refresh("claude_code"),
    agents.configCheck("codex"),
    agents.configCheck("claude_code"),
    usage.refresh("codex"),
    usage.refresh("claude_code"),
  ]);
  pollHandle = setInterval(async () => {
    if (!appStore.online) {
      await appStore.checkHealth();
      return;
    }
    await Promise.all([
      providers.refresh("codex"),
      providers.refresh("claude_code"),
      agents.configCheck("codex"),
      agents.configCheck("claude_code"),
      usage.refresh("codex"),
      usage.refresh("claude_code"),
    ]);
  }, 10_000);
});

onBeforeUnmount(() => {
  if (pollHandle) clearInterval(pollHandle);
});
</script>

<template>
  <AppShell>
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </AppShell>
</template>
