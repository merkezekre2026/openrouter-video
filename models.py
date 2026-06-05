"""
OpenRouter Video API - Pydantic modeller
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
    url: str = Field(..., description="Kare görselinin URL'si veya base64 data URI")
    frame_type: FrameType = Field(..., description="Başlangıç veya bitiş karesi")


class InputReference(BaseModel):
    url: str = Field(..., description="Referans varlığın URL'si")
    type: str = Field(default="image", description="Varlık tipi: image, audio, video")


class VideoGenerationRequest(BaseModel):
    model: str = Field(
        default="google/veo-3.1-fast",
        description="Video modeli ID'si",
    )
    prompt: str = Field(..., description="Video açıklaması")
    aspect_ratio: Optional[AspectRatio] = Field(
        default=AspectRatio.LANDSCAPE,
        description="En-boy oranı",
    )
    duration: Optional[int] = Field(
        default=None,
        ge=1,
        le=60,
        description="Saniye cinsinden video süresi (1-60)",
    )
    resolution: Optional[Resolution] = Field(
        default=None,
        description="Video çözünürlüğü",
    )
    generate_audio: Optional[bool] = Field(
        default=False,
        description="Ses oluşturulsun mu?",
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Tamamlandığında bildirim gönderilecek HTTPS webhook URL'si",
    )
    frame_images: Optional[List[FrameImage]] = Field(
        default=None,
        description="İlk/son kare görselleri (image-to-video için)",
    )
    input_references: Optional[List[InputReference]] = Field(
        default=None,
        description="Stil veya karakter tutarlılığı için referans varlıklar",
    )


class VideoJob(BaseModel):
    id: str = Field(..., description="İş ID'si")
    status: VideoStatus = Field(..., description="Mevcut durum")
    model: Optional[str] = None
    prompt: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    unsigned_urls: Optional[List[str]] = Field(
        default=None,
        description="Oluşturulan video URL'leri (completed durumunda)",
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
