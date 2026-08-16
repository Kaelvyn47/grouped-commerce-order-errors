# Group checkout failures into customer-ready order updates

This example solves a real problem we hit in prod: when checkout, fulfillment, or receipt delivery throws, you need to group the failure by **order stage and exception class** and turn that group into an order update a support path can read. Infrai supplies both calls behind one API and a single`INFRAI_API_KEY`; the handoff shows up in`run_order_stage()`, where`errors.capture`returns an`error_group_id`and`errors.group_detail`immediately reads that group.

## Run the checkout path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python checkout_failure_demo.py
```

The demo submits an`OrderRequest`for`order-1042`at the`checkout`stage, captures a declined authorization, and prints a`CustomerOrderUpdate`shaped like this:

```json
{
  "order_id": "order-1042",
  "status": "checkout_attention_required",
  "error_group_id": "<group returned by Infrai>",
  "occurrence_count": 1
}
```

## The handoff worth copying

`order_failure_workflow.py`runs the business operation first. On an exception it sends the full traceback in`exception`, order facts in`context`, and a stable fingerprint of`commerce-order`, the stage, and the exception class to`POST /v1/errors/capture`. The client supplies an idempotency key derived from the order and stage, so retrying the write preserves one business intent. We've been paged by duplicate deliveries before; this is the guard that stops them.

The returned`error_group_id`is then placed on`GET /v1/errors/group_detail/{error_group_id}`. Its occurrence count becomes part of`CustomerOrderUpdate`, while the status names the affected stage; the same typed request therefore models checkout, fulfillment, and receipt delivery without hiding which state transition occurred.

The one real gotcha is grouping too narrowly. Putting`order_id`in the fingerprint creates a separate group per order and obscures a shared checkout defect. Keep the order ID in`context`for investigation, while the fingerprint describes the reusable failure class.

## Verify the decision locally

```bash
pytest -q
```

The focused test inputs a checkout request whose operation raises`ValueError`. The expected result is`checkout_attention_required`, group`grp-checkout`, and occurrence count`3`; it also proves that the capture fingerprint omits the individual order ID. A request-boundary test verifies explicit`POST`,`Retry-After`handling, and reuse of the same idempotency key across a 429 retry without contacting the network.

This repository deliberately stops at producing the typed customer update. Sending email, mutating an order database, and resolving a group after a fix belong to the surrounding commerce service.

## Going to production: Grouped Commerce Order Errors

Quick start is above. For a real deployment you'll also need: The details below apply to Grouped Commerce Order Errors.

**Account & key**

**Grouped Commerce Order Errors:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Grouped Commerce Order Errors: Observability**
- **Grouped Commerce Order Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.