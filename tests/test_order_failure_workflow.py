from order_failure_workflow import OrderRequest, run_order_stage


class RecordingErrors:
    def __init__(self) -> None:
        self.payload = None
        self.idempotency_key = None
        self.group_id = None

    def capture(self, payload, *, idempotency_key):
        from infrai_errors import CapturedError

        self.payload = payload
        self.idempotency_key = idempotency_key
        return CapturedError(event_id="evt-1", error_group_id="grp-checkout")

    def group_detail(self, error_group_id):
        self.group_id = error_group_id
        return {"event_count": 3}


def test_checkout_failure_becomes_grouped_customer_update():
    errors = RecordingErrors()
    request = OrderRequest(
        order_id="order-1042",
        customer_id="customer-88",
        stage="checkout",
        receipt_email="buyer@example.com",
    )

    def declined():
        raise ValueError("declined")

    update = run_order_stage(request, declined, errors)

    assert update.status == "checkout_attention_required"
    assert update.error_group_id == "grp-checkout"
    assert update.occurrence_count == 3
    assert errors.payload["fingerprint"] == ["commerce-order", "checkout", "ValueError"]
    assert "ValueError: declined" in errors.payload["exception"]
    assert errors.idempotency_key == "order-error:order-1042:checkout"
    assert errors.group_id == "grp-checkout"
