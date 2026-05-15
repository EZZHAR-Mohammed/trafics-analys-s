# schemas/models.py
# Modèles Pydantic utilisés pour valider les requêtes et les réponses de l'API.
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class FlowMethod(str, Enum):
    """Méthodes de calcul du flux optique supportées."""
    lucas_kanade = "lucas_kanade"
    farneback = "farneback"
    both = "both"


class LucasKanadeParams(BaseModel):
    max_corners: int = Field(300, ge=10, le=2000, description="Maximum corners to detect")
    quality_level: float = Field(0.3, gt=0.0, le=1.0, description="Corner quality threshold")
    min_distance: float = Field(7.0, ge=1.0, description="Min distance between corners")
    block_size: int = Field(7, ge=3, le=31, description="Neighborhood block size")
    win_size: int = Field(15, ge=5, le=51, description="Optical flow window size")
    max_level: int = Field(2, ge=0, le=5, description="Max pyramid level")


class FarnebackParams(BaseModel):
    pyr_scale: float = Field(0.5, gt=0.0, lt=1.0, description="Pyramid scale factor")
    levels: int = Field(3, ge=1, le=10, description="Number of pyramid levels")
    winsize: int = Field(15, ge=5, le=51, description="Averaging window size")
    iterations: int = Field(3, ge=1, le=20, description="Iterations per level")
    poly_n: int = Field(5, ge=3, le=15, description="Polynomial expansion size")
    poly_sigma: float = Field(1.2, ge=0.5, le=5.0, description="Gaussian sigma for polynomial")


class ROIParams(BaseModel):
    x: int = Field(0, ge=0, description="ROI top-left x")
    y: int = Field(0, ge=0, description="ROI top-left y")
    width: int = Field(640, ge=10, description="ROI width")
    height: int = Field(480, ge=10, description="ROI height")


class ProcessVideoRequest(BaseModel):
    method: FlowMethod = FlowMethod.both
    lk_params: Optional[LucasKanadeParams] = None
    fb_params: Optional[FarnebackParams] = None
    roi: Optional[ROIParams] = None
    enable_tracking: bool = True
    enable_alerts: bool = True
    speed_alert_threshold: float = Field(15.0, ge=1.0)
    motion_threshold: float = Field(2.0, ge=0.1)
    save_output: bool = True
    max_frames: Optional[int] = Field(None, ge=1, description="Limit frames processed (None = all)")


class VehicleTrack(BaseModel):
    track_id: int
    positions: List[List[float]]
    speed_pixels_per_frame: float
    direction_angle_deg: float
    is_fast: bool
    color: List[int]


class FrameFlowResult(BaseModel):
    frame_index: int
    timestamp_sec: float
    lk_point_count: Optional[int] = None
    lk_avg_magnitude: Optional[float] = None
    fb_avg_magnitude: Optional[float] = None
    fb_max_magnitude: Optional[float] = None
    motion_detected: bool = False
    alert_triggered: bool = False
    active_tracks: int = 0
    processing_time_ms: float


class VideoProcessingResult(BaseModel):
    job_id: str
    video_path: str
    total_frames: int
    processed_frames: int
    fps_original: float
    avg_processing_fps: float
    method: str
    frame_results: List[FrameFlowResult]
    tracks: List[VehicleTrack]
    alerts: List[Dict[str, Any]]
    output_video_url: Optional[str] = None
    stats: Dict[str, Any]


class ComparisonResult(BaseModel):
    job_id: str
    lk_avg_fps: float
    fb_avg_fps: float
    lk_avg_magnitude: float
    fb_avg_magnitude: float
    lk_total_processing_ms: float
    fb_total_processing_ms: float
    winner_speed: str
    winner_accuracy: str
    recommendation: str
    frame_by_frame: List[Dict[str, Any]]


class AlertRecord(BaseModel):
    frame_index: int
    timestamp_sec: float
    alert_type: str
    magnitude: float
    description: str
    region: Optional[str] = None


class StreamStatus(BaseModel):
    active: bool
    frame_count: int
    fps: float
    method: str
    avg_magnitude: float
    active_tracks: int
    alert_count: int


class ExportRequest(BaseModel):
    job_id: str
    format: str = Field("json", pattern="^(json|csv|video)$")
    include_tracks: bool = True
    include_alerts: bool = True
    include_frame_data: bool = False
