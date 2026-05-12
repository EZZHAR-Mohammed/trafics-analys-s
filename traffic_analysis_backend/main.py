"""
Traffic Analysis Backend — point d'entrée principal
FastAPI + OpenCV + Optical Flow (Lucas-Kanade & Horn-Schunck/Farneback)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from routers import video, camera, tracking, analysis, alerts, export
from core.config import settings
from core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Logique de démarrage et d'arrêt de l'application."""
    logger.info("🚀 Traffic Analysis API démarrage...")

    # Création des dossiers nécessaires si absent
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.FRAMES_DIR, exist_ok=True)

    logger.info(
        f"📁 Dossiers prêts : {settings.UPLOAD_DIR}, {settings.OUTPUT_DIR}, {settings.FRAMES_DIR}"
    )

    yield

    # Exécution au moment de l'arrêt de l'application
    logger.info("🛑 Traffic Analysis API arrêt...")


# Création de l'application FastAPI avec documentation et métadonnées
app = FastAPI(
    title="Traffic Analysis API",
    description="""
## 🚗 Plateforme d'analyse de circulation

API avancée pour analyser les mouvements de véhicules en utilisant :
- **Lucas–Kanade** flux optique clairsemé
- **Farneback (approximation Horn–Schunck)** flux optique dense

### Fonctionnalités
- 📹 Téléversement et traitement de vidéos
- 📷 Traitement de flux webcam en temps réel
- 🔵 Flux clairsemé Lucas–Kanade
- 🔴 Flux dense Farneback
- 🚗 Suivi de véhicule et estimation de vitesse
- 📊 Comparaison de méthodes et analyses FPS
- 🔥 Alertes de mouvement et détection d'anomalies
- 💾 Export des résultats en vidéo/JSON/CSV
    """,
    version="2.0.0",
    contact={"name": "Traffic Analysis Team", "email": "dev@traffic-analysis.ai"},
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configuration CORS pour autoriser les requêtes depuis n'importe quelle origine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montre le dossier outputs comme dossier statique accessible via /outputs
if not os.path.exists("outputs"):
    os.makedirs("outputs")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Enregistrement des routers de l'API avec leurs préfixes et tags
app.include_router(video.router, prefix="/api/v1/video", tags=["📹 Video Processing"])
app.include_router(camera.router, prefix="/api/v1/camera", tags=["📷 Camera / Webcam"])
app.include_router(tracking.router, prefix="/api/v1/tracking", tags=["🚗 Vehicle Tracking"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["📊 Analysis & Comparison"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["🔥 Alerts & Anomalies"])
app.include_router(export.router, prefix="/api/v1/export", tags=["💾 Export"])


@app.get("/", tags=["🏠 Root"])
async def root():
    """Point de terminaison racine pour vérifier que l'API fonctionne."""
    return {
        "message": "Traffic Analysis API",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "running",
    }


@app.get("/health", tags=["🏠 Root"])
async def health():
    """Point de terminaison de santé pour vérifier OpenCV et CUDA."""
    import cv2

    return {
        "status": "healthy",
        "opencv_version": cv2.__version__,
        "cuda_available": cv2.cuda.getCudaEnabledDeviceCount() > 0,
    }
