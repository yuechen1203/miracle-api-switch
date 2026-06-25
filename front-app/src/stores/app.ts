import { defineStore } from "pinia";
import { api, BackendError } from "@/api/client";
import type { HealthInfo } from "@/types/api";

interface ToastItem {
  id: number;
  level: "info" | "success" | "warn" | "error";
  title: string;
  description?: string;
  timeoutMs?: number;
}

let toastCounter = 0;

export const useAppStore = defineStore("app", {
  state: () => ({
    online: false,
    health: null as HealthInfo | null,
    lastHealthError: "" as string,
    toasts: [] as ToastItem[],
  }),
  actions: {
    async checkHealth() {
      try {
        this.health = await api.health();
        this.online = true;
        this.lastHealthError = "";
      } catch (err) {
        this.online = false;
        this.health = null;
        this.lastHealthError = err instanceof BackendError ? err.message : "后端不可达";
      }
    },
    pushToast(toast: Omit<ToastItem, "id">) {
      const id = ++toastCounter;
      this.toasts.push({ id, timeoutMs: 4000, ...toast });
      const timeout = toast.timeoutMs ?? 4000;
      if (timeout > 0) {
        setTimeout(() => this.dismissToast(id), timeout);
      }
      return id;
    },
    dismissToast(id: number) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    notifyError(err: unknown, fallback = "操作失败") {
      const message =
        err instanceof BackendError ? err.message : err instanceof Error ? err.message : fallback;
      const code = err instanceof BackendError ? err.code : undefined;
      this.pushToast({
        level: "error",
        title: fallback,
        description: code ? `${code}: ${message}` : message,
      });
    },
  },
});
