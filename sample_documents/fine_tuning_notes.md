# Fine-tuning Notes

## What fine-tuning is

Fine-tuning continues the training of a pretrained language model on a smaller,
task-specific dataset. It updates the model's weights so that the model adapts
its behavior, tone, or format to a target domain.

## When to fine-tune

Fine-tuning is a good fit when you need a consistent style, a specialized output
format, or a durable skill that should not depend on external documents at query
time. It is less suitable when the underlying facts change frequently, because
every update requires collecting data and retraining.

## Fine-tuning versus retrieval

The key difference between fine-tuning and RAG is where knowledge lives.
Fine-tuning bakes knowledge and behavior into the weights. RAG keeps knowledge in
an external store and retrieves it on demand. Many production systems combine the
two: fine-tune for style and reliability, and use RAG for up-to-date facts.

## Parameter-efficient methods

Techniques such as LoRA and QLoRA make fine-tuning cheaper by training only a
small number of additional parameters instead of the full model. This lowers the
memory footprint and makes fine-tuning feasible on modest hardware.
