"""
OpenRouter Video API İstemcisi
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional, List, Any

import httpx

from models import (
    VideoGenerationRequest,
    VideoJob,
    VideoModel,
    VideoStatus,
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT = 30.0
POLL_INTERVAL = 5  # saniye
MAX_POLL_ATTEMPTS = 120  # 10 dakika (120 × 5s)


class OpenRouterError(Exception):
    """OpenRouter API hatası"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OpenRouterClient:
    """OpenRouter Video API ile iletişim kuran asenkron istemci."""

    def __init__(self, api_key: str, site_url: str = "", site_name: str = ""):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": site_url or "https://openrouter-video-mcp.onrender.com",
            "X-Title": site_name or "OpenRouter Video MCP",
        }

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers=self.headers,
            timeout=DEFAULT_TIMEOUT,
        )

    async def list_video_models(self) -> List[VideoModel]:
        """Kullanılabilir video modellerini listeler."""
        async with self._make_client() as client:
            response = await client.get("/videos/models")
            self._raise_for_status(response)
            data = response.json()

            # OpenRouter'ın yanıt formatı: {"data": [...]} veya düz liste
            if isinstance(data, dict):
                models_data = data.get("data", [])
            else:
                models_data = data

            return [VideoModel(**m) for m in models_data]

    async def generate_video(self, request: VideoGenerationRequest) -> VideoJob:
        """Video oluşturma işi başlatır ve job bilgisini döner."""
        # Sadece dolu alanları gönder
        payload = request.model_dump(exclude_none=True, mode="json")

        async with self._make_client() as client:
            response = await client.post("/videos", json=payload)
            self._raise_for_status(response)
            data = response.json()

        return VideoJob(**data)

    async def get_video_status(self, job_id: str) -> VideoJob:
        """Belirtilen iş ID'sinin durumunu sorgular."""
        async with self._make_client() as client:
            response = await client.get(f"/videos/{job_id}")
            self._raise_for_status(response)
            data = response.json()

        return VideoJob(**data)

    async def wait_for_video(
        self,
        job_id: str,
        poll_interval: int = POLL_INTERVAL,
        max_attempts: int = MAX_POLL_ATTEMPTS,
    ) -> VideoJob:
        """
        Video tamamlanana (completed/failed) kadar yoklar.
        Her poll_interval saniyede bir kontrol eder.
        """
        for attempt in range(max_attempts):
            job = await self.get_video_status(job_id)

            if job.status == VideoStatus.COMPLETED:
                logger.info("Video tamamlandı: %s", job_id)
                return job

            if job.status == VideoStatus.FAILED:
                raise OpenRouterError(
                    f"Video oluşturma başarısız: {job.error or 'Bilinmeyen hata'}",
                )

            logger.debug(
                "Video bekleniyor (%s/%s): job_id=%s status=%s",
                attempt + 1,
                max_attempts,
                job_id,
                job.status,
            )
            await asyncio.sleep(poll_interval)

        raise OpenRouterError(
            f"Video {max_attempts * poll_interval} saniye içinde tamamlanamadı: {job_id}"
        )

    async def list_generations(self, limit: int = 20) -> List[VideoJob]:
        """Son video oluşturma işlerini listeler."""
        async with self._make_client() as client:
            response = await client.get("/videos", params={"limit": limit})
            self._raise_for_status(response)
            data = response.json()

        if isinstance(data, dict):
            items = data.get("data", [])
        else:
            items = data

        return [VideoJob(**item) for item in items]

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """HTTP hatalarını anlaşılır mesajlarla fırlatır."""
        if response.is_success:
            return

        try:
            error_body = response.json()
            message = (
                error_body.get("error", {}).get("message")
                or error_body.get("message")
                or response.text
            )
        except Exception:
            message = response.text or f"HTTP {response.status_code}"

        raise OpenRouterError(message, status_code=response.status_code)
