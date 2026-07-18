import os
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is missing in .env")
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/chat",
    tags=["Chat Widget"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def extract_reply(data: dict[str, Any]) -> str:
    """Extract the generated message from the Langflow run response."""

    try:
        outputs = data["outputs"]
        component_outputs = outputs[0]["outputs"]
        results = component_outputs[0]["results"]
        message = results["message"]

        if isinstance(message, dict):
            text = message.get("text")

            if isinstance(text, str) and text.strip():
                return text.strip()

    except (KeyError, IndexError, TypeError):
        pass

    raise ValueError("Could not extract the AI response from Langflow.")


@router.post("/widget", response_model=ChatResponse)
async def chat_widget(request: ChatRequest) -> ChatResponse:
    flow_id = os.getenv("LANGFLOW_WIDGET_FLOW_ID")
    api_key = os.getenv("LANGFLOW_API_KEY")
    base_url = os.getenv(
        "LANGFLOW_INTERNAL_URL",
        "http://localhost:7860",
    )

    if not flow_id:
        raise HTTPException(
            status_code=500,
            detail="LANGFLOW_WIDGET_FLOW_ID is not configured.",
        )

    session_id = request.session_id or str(uuid4())

    headers = {
        "Content-Type": "application/json",
    }

    if api_key:
        headers["x-api-key"] = api_key

    payload = {
        "input_value": request.message,
        "input_type": "chat",
        "output_type": "chat",
        "session_id": session_id,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/api/v1/run/{flow_id}",
                headers=headers,
                json=payload,
            )

        response.raise_for_status()
        reply = extract_reply(response.json())

        return ChatResponse(
            reply=reply,
            session_id=session_id,
        )

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The AI model took too long to respond.",
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Langflow flow failed: {exc.response.text[:500]}",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to the Langflow flow.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc