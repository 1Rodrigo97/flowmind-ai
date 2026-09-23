# Fine-tuning (planned — V5)

This directory is a placeholder for the **V5** dataset-curation and fine-tuning
work. It is **not implemented in V1**.

## Intended scope

- Curate a dataset from indexed documents and grounded Q&A pairs.
- Fine-tune a small local model (e.g. via LoRA/QLoRA) to improve answer style and
  faithfulness on the personal corpus.
- Keep RAG as the source of fresh facts; use fine-tuning for behavior and format.

## Why it is deferred

V1 deliberately relies on retrieval + grounding rather than fine-tuning, because
knowledge that changes often is cheaper to keep current in a vector store than in
model weights.

See the [Roadmap](../README.md#roadmap) for the full phase plan.
