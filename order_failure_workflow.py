"""Capture an order failure, then hand its group to customer-update triage."""

from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass
from typing import Any, Callable, TypeVar

from infrai_errors import CapturedError, InfraiErrors


T = TypeVar("T")


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    customer_id: str
    stage: str
    receipt_email: str


@dataclass(frozen=True)
class CustomerOrderUpdate:
    order_id: str
    status: str
    error_group_id: str
    occurrence_count: int


def grouping_fingerprint(request: OrderRequest, exc: Exception) -> list[str]:
    """Group repeated failures by business stage and exception class."""
    return ["commerce-order", request.stage, type(exc).__name__]


def run_order_stage(
    request: OrderRequest,
    operation: Callable[[], T],
    errors: InfraiErrors,
) -> T | CustomerOrderUpdate:
    try:
        return operation()
    except Exception as exc:
        captured: CapturedError = errors.capture(
            {
                "title": f"Order {request.stage} failed",
                "message": f"{type(exc).__name__}: {exc}",
                "level": "error",
                "fingerprint": grouping_fingerprint(request, exc),
                "exception": traceback.format_exc(),
                "context": asdict(request),
            },
            idempotency_key=f"order-error:{request.order_id}:{request.stage}",
        )
        group: dict[str, Any] = errors.group_detail(captured.error_group_id)
        return CustomerOrderUpdate(
            order_id=request.order_id,
            status=f"{request.stage}_attention_required",
            error_group_id=captured.error_group_id,
            occurrence_count=int(group.get("event_count", 1)),
        )
