# n8n Automation (planned — V2)

This directory is a placeholder for the **V2** document-automation layer. It is
**not implemented in V1**.

## Intended scope

n8n will orchestrate automations around the FlowMind AI backend, for example:

- Watch a folder / inbox and auto-upload new documents to `POST /api/documents/upload`.
- Schedule periodic re-indexing or health checks.
- Route grounded answers from `POST /api/chat` to external channels.

## Planned integration

Workflows will call the existing REST API — no backend changes required. Exported
workflow JSON files will live in this directory once V2 begins.

See the [Roadmap](../README.md#roadmap) for the full phase plan.
