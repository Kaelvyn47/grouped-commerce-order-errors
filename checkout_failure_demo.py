"""Runnable checkout-to-customer-update example."""

from dataclasses import asdict
import json

from infrai_errors import InfraiErrors
from order_failure_workflow import OrderRequest, run_order_stage


def authorize_checkout() -> str:
    raise ValueError("payment authorization was declined")


if __name__ == "__main__":
    order = OrderRequest(
        order_id="order-1042",
        customer_id="customer-88",
        stage="checkout",
        receipt_email="buyer@example.com",
    )
    result = run_order_stage(order, authorize_checkout, InfraiErrors())
    print(json.dumps(asdict(result) if not isinstance(result, str) else result, indent=2))
