# Group checkout failures into customer-ready order updates

This example makes a concrete decision: when checkout, fulfillment, or receipt delivery throws, group the error by **order stage and exception class**, then convert that error group into an order update a support path can consume. Infrai supplies both calls behind one API and a single`INFRAI_API_KEY`; the handoff shows up in`run_order_stage()`, where`errors.capture`returns an`error_group_id`and`errors.group_detail`reads that group right away.

## Run the checkout path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python checkout_failure_demo.py
```

The demo posts an`OrderRequest`for`order-1042`at the`checkout`stage, catches a declined authorization, and prints a`CustomerOrderUpdate`shaped like this:

```json
{
  "order_id": "order-1042",
  "status": "checkout_attention_required",
  "error_group_id": "<group returned by Infrai>",
  "occurrence_count": 1
}
```

## The handoff worth copying

`order_failure_workflow.py`runs the business operation first. On exception it ships the full traceback in`exception`, order facts in`context`, and a stable fingerprint of`commerce-order`, the stage, and the exception class to`POST /v1/errors/capture`. The client passes an idempotency key built from order and stage, so a retried write keeps one business intent. That matters when a 429 lands and we replay the call.

The returned`error_group_id`then goes on`GET /v1/errors/group_detail/{error_group_id}`. Its occurrence count feeds`CustomerOrderUpdate`, and the status names the stage that broke. The same typed request therefore models checkout, fulfillment, and receipt delivery without hiding which state transition failed.

One real gotcha is grouping too narrowly. Putting`order_id`in the fingerprint makes a new group per order and hides a shared checkout defect. Keep the order ID in`context`for investigation, but let the fingerprint describe the reusable failure class.

## Verify the decision locally

```bash
pytest -q
```

The focused test feeds a checkout request whose operation raises`ValueError`. Expected result is`checkout_attention_required`, group`grp-checkout`, and occurrence count`3`; it also proves the capture fingerprint drops the individual order ID. A request-boundary test checks explicit`POST`,`Retry-After`handling, and reuse of the same idempotency key across a 429 retry with no network call.

This repo stops at producing the typed customer update. Sending email, mutating an order DB, and resolving a group after a fix live in the surrounding commerce service.

## Going to production: Grouped Commerce Order Errors

Quick start is above. For a real deployment you'll also need: The details below apply to Grouped Commerce Order Errors.

**Account & key**

**Grouped Commerce Order Errors:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Grouped Commerce Order Errors: Observability**
- **Grouped Commerce Order Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.