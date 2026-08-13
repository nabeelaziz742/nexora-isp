import json
import os
from dataclasses import asdict, dataclass, is_dataclass
from decimal import Decimal
from uuid import UUID

from django.utils import timezone
from google import genai

from command_center.services import (
    get_command_center_summary,
    get_operational_alerts,
    get_priority_queues,
    get_recent_operational_activity,
)
from tenancy.models import Organization


class CopilotDomainError(Exception):
    pass


class CopilotProviderError(Exception):
    pass


@dataclass(frozen=True)
class CopilotAnswer:
    answer: str
    generated_at: object
    provider: str
    model: str


def _json_safe(value):
    if isinstance(value, (Decimal, UUID)):
        return str(value)

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if is_dataclass(value):
        return _json_safe(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


def build_operational_snapshot(
    *,
    organization: Organization,
) -> dict:
    return _json_safe(
        {
            "organization": {
                "code": organization.code,
                "name": organization.name,
            },
            "summary": get_command_center_summary(
                organization=organization,
            ),
            "operational_alerts": (
                get_operational_alerts(
                    organization=organization,
                )[:25]
            ),
            "priority_queues": get_priority_queues(
                organization=organization,
            ),
            "recent_operational_activity": (
                get_recent_operational_activity(
                    organization=organization,
                    limit=25,
                )
            ),
        }
    )


def _build_system_instruction() -> str:
    return (
        "You are NEXORA AI Operations Copilot. "
        "You are a read-only ISP operations analyst. "
        "Answer only from the supplied tenant-scoped "
        "operational snapshot. "
        "Never claim that you executed or changed anything. "
        "Never invent customers, amounts, incidents, alerts, "
        "statuses, causes, or operational events. "
        "If evidence is insufficient, say so. "
        "Prioritize operational risk, customer impact, "
        "collections, provisioning failures, incidents, "
        "critical support work, and failed communications. "
        "Give concise actionable analysis."
    )


def _call_gemini_api(
    *,
    question: str,
    snapshot: dict,
) -> CopilotAnswer:
    api_key = os.environ.get(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise CopilotProviderError(
            "GEMINI_API_KEY is not configured."
        )

    model = os.environ.get(
        "NEXORA_COPILOT_MODEL",
        "gemini-2.5-flash",
    ).strip()

    snapshot_json = json.dumps(
        snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    prompt = (
        f"{_build_system_instruction()}\n\n"
        "TENANT OPERATIONAL SNAPSHOT:\n"
        f"{snapshot_json}\n\n"
        "OPERATOR QUESTION:\n"
        f"{question}"
    )

    client = genai.Client(
        api_key=api_key,
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except Exception as exc:
        raise CopilotProviderError(
            "Gemini rejected or failed the Copilot request: "
            f"{exc}"
        ) from exc

    answer = getattr(
        response,
        "text",
        "",
    )

    if not isinstance(answer, str) or not answer.strip():
        raise CopilotProviderError(
            "Gemini returned no text answer."
        )

    return CopilotAnswer(
        answer=answer.strip(),
        generated_at=timezone.now(),
        provider="GEMINI",
        model=model,
    )


def ask_operations_copilot(
    *,
    organization: Organization,
    question: str,
) -> CopilotAnswer:
    normalized_question = question.strip()

    if not normalized_question:
        raise CopilotDomainError(
            "Question is required."
        )

    if len(normalized_question) > 2000:
        raise CopilotDomainError(
            "Question must not exceed 2000 characters."
        )

    if not organization.is_active:
        raise CopilotDomainError(
            "Organization is not active."
        )

    snapshot = build_operational_snapshot(
        organization=organization,
    )

    return _call_gemini_api(
        question=normalized_question,
        snapshot=snapshot,
    )