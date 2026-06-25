from __future__ import annotations

from pathlib import Path

from app.services.agent_probe import AgentProbeService
from app.services.cache_store import CacheStore, utc_now
from app.services.config_writer import ConfigWriter
from app.services.provider_service import ProviderService
from app.services.usage_service import UsageService
from app.proxy.manager import ProxyManager


class AppContext:
    def __init__(self, workspace_root: Path | None = None) -> None:
        self.started_at = utc_now()
        self.cache = CacheStore(workspace_root=workspace_root)
        self.agent_probe = AgentProbeService(self.cache)
        self.usage = UsageService(self.cache)
        self.proxy_manager = ProxyManager(self.cache, self.usage)
        self.config_writer = ConfigWriter(self.cache, self.proxy_manager)
        self.providers = ProviderService(
            cache=self.cache,
            agent_probe=self.agent_probe,
            config_writer=self.config_writer,
            proxy_manager=self.proxy_manager,
            usage_service=self.usage,
        )

    def close(self) -> None:
        self.proxy_manager.stop_all()

