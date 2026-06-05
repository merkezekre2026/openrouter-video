"""
OpenRouter Video MCP Sunucusu – Streamable HTTP Transport
Render.com'a dağıtım için optimize edilmiştir.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Annotated

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import uvicorn

from models import (
    AspectRatio,
    Resolution,
    VideoGenerationRequest,
    FrameImage,
    InputReference,
    FrameType,
)
from openrouter import OpenRouterClient, OpenRouterError

# ---------------------------------------------------------------------------
# Başlangıç ayarları
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
SITE_URL = os.environ.get("SITE_URL", "https://openrouter-video-mcp.onrender.com")
SITE_NAME = os.environ.get("SITE_NAME", "OpenRouter Video MCP")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))  # Render.com PORT'u otomatik atar

# ---------------------------------------------------------------------------
# FastMCP sunucusu
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="openrouter-video-mcp",
    instructions=(
        "Bu sunucu, OpenRouter üzerindeki video oluşturma modellerini kullanarak "
        "yüksek kaliteli videolar üretmenizi sağlar. "
        "Önce list_video_models ile mevcut modelleri öğrenin, "
        "ardından generate_video ile video oluşturun. "
        "Video üretimi asenkron çalışır; wait_for_video ile tamamlanmasını bekleyin."
    ),
)


def _get_client() -> OpenRouterClient:
    """Her araç çağrısında taze bir istemci oluşturur."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY ortam değişkeni ayarlanmamış. "
            "Render.com'da Environment Variables bölümüne ekleyin."
        )
    return OpenRouterClient(
        api_key=OPENROUTER_API_KEY,
        site_url=SITE_URL,
        site_name=SITE_NAME,
    )


# ---------------------------------------------------------------------------
# MCP Araçları
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "OpenRouter üzerinde mevcut tüm video oluşturma modellerini listeler. "
        "Hangi modelin kullanılabileceğini öğrenmek için bu aracı çalıştırın. "
        "Örnek modeller: google/veo-3.1-fast, kwaivgi/kling-v3.0-pro, vb."
    )
)
async def list_video_models() -> dict:
    """Kullanılabilir video modellerini listeler."""
    client = _get_client()
    try:
        models = await client.list_video_models()
        return {
            "count": len(models),
            "models": [
                {
                    "id": m.id,
                    "name": m.name or m.id,
                    "description": m.description,
                    "capabilities": m.capabilities,
                    "pricing": m.pricing,
                }
                for m in models
            ],
        }
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("list_video_models hatası")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Verilen prompt'a göre bir video oluşturma işi başlatır. "
        "İşlem asenkron olduğu için hemen bir job_id döner. "
        "Videonun tamamlanmasını beklemek için wait_for_video aracını kullanın. "
        "Desteklenen modeller için list_video_models'i çalıştırın."
    )
)
async def generate_video(
    prompt: Annotated[str, "Videonun nasıl olacağını açıklayan metin (İngilizce veya Türkçe)"],
    model: Annotated[str, "Video modeli ID'si (örn: google/veo-3.1-fast)"] = "google/veo-3.1-fast",
    aspect_ratio: Annotated[
        str, "En-boy oranı: '16:9' (yatay), '9:16' (dikey), '1:1' (kare)"
    ] = "16:9",
    duration: Annotated[
        Optional[int], "Video süresi (saniye, 1-60). Model destekliyorsa geçerlidir."
    ] = None,
    resolution: Annotated[
        Optional[str], "Çözünürlük: '720p', '1080p', '4k'"
    ] = None,
    generate_audio: Annotated[bool, "Ses oluşturulsun mu?"] = False,
    image_url: Annotated[
        Optional[str],
        "Image-to-video: başlangıç karesi olarak kullanılacak görsel URL'si veya base64 URI"
    ] = None,
    callback_url: Annotated[
        Optional[str],
        "Video tamamlandığında POST isteği gönderilecek HTTPS webhook URL'si"
    ] = None,
) -> dict:
    """Video oluşturma işi başlatır, job_id ve polling_url döner."""
    client = _get_client()

    # Kare görseli varsa ekle
    frame_images = None
    if image_url:
        frame_images = [FrameImage(url=image_url, frame_type=FrameType.FIRST)]

    request = VideoGenerationRequest(
        model=model,
        prompt=prompt,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        duration=duration,
        resolution=resolution,  # type: ignore[arg-type]
        generate_audio=generate_audio,
        frame_images=frame_images,
        callback_url=callback_url,
    )

    try:
        job = await client.generate_video(request)
        return {
            "job_id": job.id,
            "status": job.status,
            "model": job.model or model,
            "prompt": prompt,
            "polling_url": job.polling_url,
            "message": (
                f"Video oluşturma işi başlatıldı! "
                f"job_id='{job.id}' ile durumu takip edebilirsiniz. "
                f"Tamamlanmasını beklemek için wait_for_video('{job.id}') kullanın."
            ),
        }
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("generate_video hatası")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Belirli bir video oluşturma işinin güncel durumunu kontrol eder. "
        "Durumlar: pending (beklemede), processing (işleniyor), "
        "completed (tamamlandı), failed (başarısız). "
        "Tamamlandığında video URL'leri döner."
    )
)
async def check_video_status(
    job_id: Annotated[str, "generate_video tarafından döndürülen iş ID'si"],
) -> dict:
    """Bir video işinin durumunu sorgular."""
    client = _get_client()
    try:
        job = await client.get_video_status(job_id)
        result: dict = {
            "job_id": job.id,
            "status": job.status,
            "model": job.model,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        }
        if job.status == "completed" and job.unsigned_urls:
            result["video_urls"] = job.unsigned_urls
            result["message"] = "Video hazır! Aşağıdaki URL'lerden indirebilirsiniz."
        elif job.status == "failed":
            result["error"] = job.error or "Bilinmeyen hata"
        elif job.status in ("pending", "processing"):
            result["message"] = "Video henüz hazır değil. Biraz bekleyip tekrar kontrol edin."
        return result
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("check_video_status hatası")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Video oluşturma işini tamamlanana kadar bekler ve bitince video URL'lerini döner. "
        "Bu araç en fazla 10 dakika bekler. "
        "Video oluşturma genellikle 30 saniye ile birkaç dakika arasında sürer. "
        "Uzun bekleme sürelerine toleranslı olun."
    )
)
async def wait_for_video(
    job_id: Annotated[str, "generate_video tarafından döndürülen iş ID'si"],
    poll_interval_seconds: Annotated[
        int,
        "Kaç saniyede bir kontrol edilsin? (5-30 arasında önerilir, varsayılan: 8)"
    ] = 8,
) -> dict:
    """Video tamamlanana kadar bekler, tamamlandığında URL'leri döner."""
    client = _get_client()
    try:
        poll_interval = max(3, min(poll_interval_seconds, 30))
        job = await client.wait_for_video(
            job_id,
            poll_interval=poll_interval,
            max_attempts=int(600 / poll_interval),  # 10 dakika
        )
        return {
            "job_id": job.id,
            "status": job.status,
            "model": job.model,
            "completed_at": job.completed_at,
            "video_urls": job.unsigned_urls or [],
            "message": (
                f"Video başarıyla oluşturuldu! "
                f"{len(job.unsigned_urls or [])} adet URL mevcut."
            ),
        }
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("wait_for_video hatası")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Hesabınızdaki son video oluşturma geçmişini listeler. "
        "Her kaydın job_id'si, durumu ve varsa video URL'leri gösterilir."
    )
)
async def list_my_generations(
    limit: Annotated[int, "Listenecek maksimum kayıt sayısı (1-100)"] = 20,
) -> dict:
    """Son video oluşturma geçmişini listeler."""
    client = _get_client()
    try:
        clamped_limit = max(1, min(limit, 100))
        jobs = await client.list_generations(limit=clamped_limit)
        return {
            "count": len(jobs),
            "generations": [
                {
                    "job_id": j.id,
                    "status": j.status,
                    "model": j.model,
                    "prompt": j.prompt,
                    "created_at": j.created_at,
                    "completed_at": j.completed_at,
                    "video_urls": j.unsigned_urls or [],
                }
                for j in jobs
            ],
        }
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("list_my_generations hatası")
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Sağlık kontrolü endpoint'i (Render.com için)
# ---------------------------------------------------------------------------
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "openrouter-video-mcp",
            "transport": "streamable-http",
            "mcp_endpoint": "/mcp",
            "api_key_configured": bool(OPENROUTER_API_KEY),
        }
    )


# ---------------------------------------------------------------------------
# Starlette uygulaması – MCP + health endpoint birleşimi
# ---------------------------------------------------------------------------
def build_app() -> Starlette:
    mcp_app = mcp.http_app(path="/mcp")

    routes = [
        Route("/health", health_check, methods=["GET"]),
        Route("/", health_check, methods=["GET"]),
        Mount("/", app=mcp_app),
    ]

    app = Starlette(routes=routes, lifespan=mcp_app.router.lifespan_context)
    return app


app = build_app()

# ---------------------------------------------------------------------------
# Doğrudan çalıştırma (geliştirme ortamı)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("OpenRouter Video MCP sunucusu başlatılıyor...")
    logger.info("Host: %s, Port: %d", HOST, PORT)
    logger.info("MCP endpoint: http://%s:%d/mcp", HOST, PORT)
    logger.info("Health check: http://%s:%d/health", HOST, PORT)

    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
