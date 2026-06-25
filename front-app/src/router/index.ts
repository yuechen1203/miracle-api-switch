import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "dashboard",
    component: () => import("@/views/DashboardView.vue"),
  },
  {
    path: "/agents/codex",
    name: "agent-codex",
    component: () => import("@/views/AgentView.vue"),
    props: { agentType: "codex" },
  },
  {
    path: "/agents/claude-code",
    name: "agent-claude",
    component: () => import("@/views/AgentView.vue"),
    props: { agentType: "claude_code" },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("@/views/SettingsView.vue"),
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export { routes };
