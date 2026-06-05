"""
OpenRouter Video API - Pydantic Models
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    WIDE = "21:9"


class Resolution(str, Enum):
    HD = "720p"
    FULL_HD = "1080p"
    FOUR_K = "4k"


class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FrameType(str, Enum):
    FIRST = "first"
    LAST = "last"


class FrameImage(BaseModel):
    url: str = Field(..., description="URL or base64 data URI of the frame image")
    frame_type: FrameType = Field(..., description="Specifies if it is the first or last frame")


class InputReference(BaseModel):
    url: str = Field(..., description="URL of the reference asset")
    type: str = Field(default="image", description="Asset type: image, audio, or video")


class VideoGenerationRequest(BaseModel):
    model: str = Field(
        default="google/veo-3.1-fast",
        description="ID of the video generation model",
    )
    prompt: str = Field(..., description="Text description of the video to generate")
    aspect_ratio: Optional[AspectRatio] = Field(
        default=AspectRatio.LANDSCAPE,
        description="Aspect ratio for the video",
    )
    duration: Optional[int] = Field(
        default=None,
        ge=1,
        le=60,
        description="Duration of the video in seconds (1-60)",
    )
    resolution: Optional[Resolution] = Field(
        default=None,
        description="Desired resolution",
    )
    generate_audio: Optional[bool] = Field(
        default=False,
        description="Whether to generate audio alongside the video",
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="HTTPS webhook URL to receive status notifications",
    )
    frame_images: Optional[List[FrameImage]] = Field(
        default=None,
        description="First/last frame images for image-to-video tasks",
    )
    input_references: Optional[List[InputReference]] = Field(
        default=None,
        description="Reference assets for style or character consistency",
    )


class VideoJob(BaseModel):
    id: str = Field(..., description="Job ID")
    status: VideoStatus = Field(..., description="Current status of the generation job")
    model: Optional[str] = None
    prompt: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    unsigned_urls: Optional[List[str]] = Field(
        default=None,
        description="Generated video download URLs (available when status is completed)",
    )
    polling_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class VideoModel(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    pricing: Optional[dict[str, Any]] = None
    capabilities: Optional[dict[str, Any]] = None
    context_length: Optional[int] = None
    architecture: Optional[dict[str, Any]] = None
    top_provider: Optional[dict[str, Any]] = None
