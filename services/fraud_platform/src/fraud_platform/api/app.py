from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fraud_platform.api.service import FraudPlatformService
from fraud_platform.config import AppConfig
from fraud_platform.schemas import BatchPredictionRequest, PredictionRequest


def create_app():
    try:
        from fastapi import FastAPI
        from fastapi.responses import StreamingResponse
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI is not installed. Install optional API dependencies with "
            "`pip install -e \".[api]\"` or run `make bootstrap`."
        ) from exc

    config = AppConfig()
    service = FraudPlatformService(config)
    app = FastAPI(title="Real-Time Streaming Fraud Detection Platform")

    @app.get("/health")
    def health():
        return service.health()

    @app.post("/predict")
    def predict(request: PredictionRequest):
        return service.predict(request.transaction)

    @app.post("/batch-predict")
    def batch_predict(request: BatchPredictionRequest):
        return service.batch_predict(request.transactions)

    @app.get("/metrics/current")
    def metrics_current():
        return service.current_metrics()

    @app.get("/drift/events")
    def drift_events(limit: int = 50):
        return service.drift_events(limit)

    @app.get("/stream/recent")
    def stream_recent(limit: int = 50):
        return service.stream_recent(limit)

    @app.post("/retrain")
    def retrain():
        return service.retrain()

    async def event_generator() -> AsyncIterator[str]:
        while True:
            yield service.live_stream_snapshot()
            await asyncio.sleep(1.5)

    @app.get("/stream/live")
    async def stream_live():
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return app

