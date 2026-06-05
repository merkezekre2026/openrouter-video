"""
OpenRouter Video MCP Server – Streamable HTTP Transport
Optimized for deployment on platforms like Render.com.
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
# Initial configuration
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
SITE_URL = os.environ.get("SITE_URL", "")
SITE_NAME = os.environ.get("SITE_NAME", "OpenRouter Video MCP")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))  # Render.com automatically binds PORT

# ---------------------------------------------------------------------------
# FastMCP Server Instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="openrouter-video-mcp",
    instructions=(
        "This server integrates OpenRouter's Video Generation APIs. "
        "Use list_video_models to discover available models, "
        "and generate_video to create video generation jobs. "
        "Since video generation is asynchronous, use wait_for_video "
        "or check_video_status to retrieve the completed URLs."
    ),
)


def _get_client() -> OpenRouterClient:
    """Helper to initialize the API client."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is not set. "
            "Please configure it in your environment or Render dashboard."
        )
    return OpenRouterClient(
        api_key=OPENROUTER_API_KEY,
        site_url=SITE_URL,
        site_name=SITE_NAME,
    )


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "Lists all available video generation models on OpenRouter. "
        "Use this tool to find valid model IDs. Examples include: "
        "google/veo-3.1-fast, kwaivgi/kling-v3.0-pro, etc."
    )
)
async def list_video_models() -> dict:
    """List all supported video generation models."""
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
        logger.exception("Error in list_video_models")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Starts an asynchronous video generation job. "
        "Returns a job_id instantly. Use wait_for_video to poll until "
        "the final video output URLs are ready."
    )
)
async def generate_video(
    prompt: Annotated[str, "Detailed description of the video to generate"],
    model: Annotated[str, "Model ID (e.g., google/veo-3.1-fast)"] = "google/veo-3.1-fast",
    aspect_ratio: Annotated[
        str, "Aspect ratio: '16:9' (landscape), '9:16' (portrait), '1:1' (square)"
    ] = "16:9",
    duration: Annotated[
        Optional[int], "Duration in seconds (1-60). Subject to model capabilities."
    ] = None,
    resolution: Annotated[
        Optional[str], "Resolution profile: '720p', '1080p', or '4k'"
    ] = None,
    generate_audio: Annotated[bool, "Whether to generate audio along with the video"] = False,
    image_url: Annotated[
        Optional[str],
        "Image-to-video source: Image URL or base64 data URI to use as the starting frame"
    ] = None,
    callback_url: Annotated[
        Optional[str],
        "Optional HTTPS endpoint to receive webhook notifications upon completion"
    ] = None,
) -> dict:
    """Trigger a video generation request and return job tracking metadata."""
    client = _get_client()

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
                f"Video generation job successfully submitted! "
                f"Use check_video_status('{job.id}') or wait_for_video('{job.id}') "
                f"to monitor progress and retrieve the final video URLs."
            ),
        }
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("Error in generate_video")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Retrieves the status of a specific video generation job. "
        "Status values: pending, processing, completed, failed."
    )
)
async def check_video_status(
    job_id: Annotated[str, "The unique job identifier returned by generate_video"],
) -> dict:
    """Query current status of a video job."""
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
            result["message"] = "Video is ready! Use the links below to download."
        elif job.status == "failed":
            result["error"] = job.error or "Unknown error occurred"
        elif job.status in ("pending", "processing"):
            result["message"] = "Video is still generating. Check back shortly."
        return result
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("Error in check_video_status")
        return {"error": str(exc)}


@mcp.tool(
    description=(
        "Blocks and polls until the video generation job is completed. "
        "Default timeout is 10 minutes. Suitable for clients running workflows."
    )
)
async def wait_for_video(
    job_id: Annotated[str, "The unique job identifier returned by generate_video"],
    poll_interval_seconds: Annotated[
        int,
        "Polling interval in seconds (recommended: 5-30, default: 8)"
    ] = 8,
) -> dict:
    """Poll a job until completion, returning final video assets."""
    client = _get_client()
    try:
        poll_interval = max(3, min(poll_interval_seconds, 30))
        job = await client.wait_for_video(
            job_id,
            poll_interval=poll_interval,
            max_attempts=int(600 / poll_interval),  # 10 minutes max
        )
        return {
            "job_id": job.id,
            "status": job.status,
            "model": job.model,
            "completed_at": job.completed_at,
            "video_urls": job.unsigned_urls or [],
            "message": (
                f"Video successfully generated! "
                f"Found {len(job.unsigned_urls or [])} asset URL(s)."
            ),
        }
    except OpenRouterError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except Exception as exc:
        logger.exception("Error in wait_for_video")
        return {"error": str(exc)}


@mcp.tool(
    description="Lists your recent video generation jobs history."
)
async def list_my_generations(
    limit: Annotated[int, "Maximum items to return (1-100)"] = 20,
) -> dict:
    """Retrieve history of video generation attempts."""
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
        logger.exception("Error in list_my_generations")
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Health endpoint for Render.com active monitoring
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
# Starlette Application Construction
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
# Direct Entry Point for Development
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting OpenRouter Video MCP server...")
    logger.info("Binding to Host: %s, Port: %d", HOST, PORT)
    logger.info("MCP Endpoint URL: http://%s:%d/mcp", HOST, PORT)
    logger.info("Health Check URL: http://%s:%d/health", HOST, PORT)

    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
