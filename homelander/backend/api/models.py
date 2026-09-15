from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.core.schemas import PullModelRequest
from backend.models.base_provider import ProviderError
from backend.models.registry import registry

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def list_all_models():
    """List models across all registered providers, with live status."""
    result = []
    for provider in registry.all():
        status = await provider.health_check()
        models = await provider.list_models() if status.value == "online" else []
        result.append(
            {
                "provider": provider.name,
                "status": status.value,
                "models": [
                    {
                        "name": m.name,
                        "provider": m.provider,
                        "context_size": m.context_size,
                        "size_bytes": m.size_bytes,
                        "family": m.family,
                    }
                    for m in models
                ],
            }
        )
    return {"providers": result}


@router.get("/{provider_name}/health")
async def provider_health(provider_name: str):
    try:
        provider = registry.get(provider_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    status = await provider.health_check()
    return {"provider": provider_name, "status": status.value}


@router.post("/pull")
async def pull_model(req: PullModelRequest):
    """Stream install progress for a model (e.g. 'llama3.1:8b')."""
    try:
        provider = registry.get(req.provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_stream():
        try:
            async for progress in provider.pull_model(req.model):
                yield f"data: {json.dumps(progress)}\n\n"
        except ProviderError as exc:
            yield f"data: {json.dumps({'error': exc.user_message})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/{provider_name}/{model_name}")
async def delete_model(provider_name: str, model_name: str):
    try:
        provider = registry.get(provider_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        await provider.delete_model(model_name)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.user_message) from exc
    return {"deleted": model_name}
