import os
from fastapi import APIRouter
from backend.ml.infer import MODEL_PATH

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
def health_check():
    """
    Public health check endpoint for host application liveness probe.
    """
    model_exists = os.path.exists(MODEL_PATH)
    return {
        "status": "ok",
        "service": "stock-research-module",
        "version": "1.0.0",
        "model_loaded": model_exists,
        "model_path": MODEL_PATH if model_exists else "using_baseline_fallback"
    }
