#!/usr/bin/env python3
"""Main MCP server implementation for Radarr and Sonarr."""

from __future__ import annotations

import argparse
import json
import logging
from typing import Optional

from fastmcp import FastMCP

from .config import (
    Config,
    load_config,
    RadarrConfig,
    SonarrConfig,
)
from .services.radarr_service import RadarrService
from .services.sonarr_service import SonarrService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions for watched status
# ---------------------------------------------------------------------------

def _is_series_watched(title: str, config: Config, sonarr_service: SonarrService) -> bool:
    statuses = []
    if hasattr(config, "jellyfin_config") and config.jellyfin_config.get("baseUrl"):
        from .services.jellyfin_service import JellyfinService

        jellyfin = JellyfinService(config.jellyfin_config)
        try:
            statuses.append(jellyfin.is_series_watched(title))
        except Exception as exc:  # pragma: no cover - network failures
            logger.error("Jellyfin check failed for %s: %s", title, exc)
    if hasattr(config, "plex_config") and config.plex_config.get("baseUrl"):
        from .services.plex_service import PlexService

        plex = PlexService(config.plex_config)
        try:
            statuses.append(plex.is_series_watched(title))
        except Exception as exc:  # pragma: no cover
            logger.error("Plex check failed for %s: %s", title, exc)
    if statuses:
        return any(statuses)
    return sonarr_service.is_series_watched(title)


def _is_movie_watched(title: str, config: Config) -> bool:
    statuses = []
    if hasattr(config, "jellyfin_config") and config.jellyfin_config.get("baseUrl"):
        from .services.jellyfin_service import JellyfinService

        jellyfin = JellyfinService(config.jellyfin_config)
        try:
            statuses.append(jellyfin.is_movie_watched(title))
        except Exception as exc:  # pragma: no cover
            logger.error("Jellyfin movie check failed for %s: %s", title, exc)
    if hasattr(config, "plex_config") and config.plex_config.get("baseUrl"):
        from .services.plex_service import PlexService

        plex = PlexService(config.plex_config)
        try:
            statuses.append(plex.is_movie_watched(title))
        except Exception as exc:  # pragma: no cover
            logger.error("Plex movie check failed for %s: %s", title, exc)
    return any(statuses)


# ---------------------------------------------------------------------------
# MCP Server implementation
# ---------------------------------------------------------------------------

class RadarrSonarrMCPServer:
    """MCP server exposing Radarr and Sonarr data."""

    def __init__(self, config: Config):
        self.config = config
        self.server = FastMCP(
            name="radarr-sonarr-mcp-server",
            instructions="MCP Server for Radarr and Sonarr media management",
        )
        self.sonarr_service = SonarrService(config.sonarr_config)
        self._register_tools()
        self._register_resources()

    # ------------------------------------------------------------------
    def _register_tools(self) -> None:
        @self.server.tool()
        def get_available_series(
            year: Optional[int] = None,
            downloaded: Optional[bool] = None,
            watched: Optional[bool] = None,
            actors: Optional[str] = None,
        ) -> dict:
            """Return series from Sonarr with optional filters."""

            service = SonarrService(self.config.sonarr_config)
            all_series = service.get_all_series()
            filtered = all_series
            if year is not None:
                filtered = [s for s in filtered if s.year == year]
            if downloaded is not None:
                filtered = [
                    s
                    for s in filtered
                    if (s.statistics and s.statistics.episode_file_count > 0)
                    == downloaded
                ]
            if watched is not None:
                if watched:
                    filtered = [
                        s
                        for s in filtered
                        if _is_series_watched(s.title, self.config, service)
                    ]
                else:
                    filtered = [
                        s
                        for s in filtered
                        if not _is_series_watched(s.title, self.config, service)
                    ]
            if actors:
                filtered = [
                    s
                    for s in filtered
                    if s.data.get("credits")
                    and any(
                        actors.lower() in cast.get("name", "").lower()
                        for cast in s.data.get("credits", {}).get("cast", [])
                    )
                ]
            return json.dumps({
                "count": len(filtered),
                "series": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "year": s.year,
                        "overview": s.overview,
                        "status": s.status,
                        "network": s.network,
                        "genres": s.genres,
                        "watched": _is_series_watched(s.title, self.config, service),
                    }
                    for s in filtered
                ],
            })

        @self.server.tool()
        def lookup_series(term: str) -> dict:
            service = SonarrService(self.config.sonarr_config)
            results = service.lookup_series(term)
            return json.dumps({
                "count": len(results),
                "series": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "year": s.year,
                        "overview": s.overview,
                    }
                    for s in results
                ],
            })

        @self.server.tool()
        def get_available_movies(
            year: Optional[int] = None,
            downloaded: Optional[bool] = None,
            watched: Optional[bool] = None,
            actors: Optional[str] = None,
        ) -> dict:
            """Return movies from Radarr with optional filters."""

            radarr_service = RadarrService(self.config.radarr_config)
            all_movies = radarr_service.get_all_movies()
            filtered = all_movies
            if year is not None:
                filtered = [m for m in filtered if m.year == year]
            if downloaded is not None:
                filtered = [m for m in filtered if m.has_file == downloaded]
            if watched is not None:
                if watched:
                    filtered = [
                        m for m in filtered if _is_movie_watched(m.title, self.config)
                    ]
                else:
                    filtered = [
                        m for m in filtered if not _is_movie_watched(m.title, self.config)
                    ]
            if actors:
                filtered = [
                    m
                    for m in filtered
                    if m.data.get("credits")
                    and any(
                        actors.lower() in cast.get("name", "").lower()
                        for cast in m.data.get("credits", {}).get("cast", [])
                    )
                ]
            return json.dumps({
                "count": len(filtered),
                "movies": [
                    {
                        "id": m.id,
                        "title": m.title,
                        "year": m.year,
                        "overview": m.overview,
                        "hasFile": m.has_file,
                        "status": m.status,
                        "genres": m.genres,
                        "watched": _is_movie_watched(m.title, self.config),
                    }
                    for m in filtered
                ],
            })

    # ------------------------------------------------------------------
    def _register_resources(self) -> None:
        @self.server.resource(
            "http://example.com/series", description="TV series collection from Sonarr"
        )
        def series() -> dict:
            service = SonarrService(self.config.sonarr_config)
            items = service.get_all_series()
            return {
                "count": len(items),
                "series": [{"id": s.id, "title": s.title, "year": s.year} for s in items],
            }

        @self.server.resource(
            "http://example.com/movies", description="Movie collection from Radarr"
        )
        def movies() -> dict:
            radarr_service = RadarrService(self.config.radarr_config)
            items = radarr_service.get_all_movies()
            return {
                "count": len(items),
                "movies": [{"id": m.id, "title": m.title, "year": m.year} for m in items],
            }

    # ------------------------------------------------------------------
    def start(self) -> None:
        port = self.config.server_config.port
        logger.info("Starting Radarr-Sonarr MCP Server on port %s", port)
        logger.info("Connect Claude Desktop to: http://localhost:%s", port)
        self.server.run()


# ---------------------------------------------------------------------------
# Factory and CLI entry point
# ---------------------------------------------------------------------------

def create_server(config_path: str | None = None) -> RadarrSonarrMCPServer:
    config = load_config(config_path)
    return RadarrSonarrMCPServer(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Radarr/Sonarr MCP Server")
    parser.add_argument("--config", help="Path to config.json", default=None)
    args = parser.parse_args()
    server = create_server(args.config)
    server.start()


if __name__ == "__main__":
    main()
