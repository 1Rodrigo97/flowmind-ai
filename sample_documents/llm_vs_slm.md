# LLM vs SLM

## Large Language Models

A Large Language Model (LLM) is a neural network with billions of parameters
trained on broad text corpora. LLMs are capable generalists but require
significant memory and compute to run, which often means relying on a remote API.

## Small Language Models

A Small Language Model (SLM) has far fewer parameters, typically a few billion or
less. SLMs trade some raw capability for speed, low memory use, and the ability to
run locally on a laptop or a single GPU. Models like Llama 3.2 3B are examples of
SLMs suitable for local inference.

## Why SLMs suit local RAG

In a grounded RAG system, the model does not need to know everything: the relevant
facts are supplied in the retrieved context. This makes a small local model a
practical choice, because its main job is to read the provided context and write a
faithful answer rather than to recall knowledge from its weights.

## Trade-offs

LLMs tend to reason better on complex, multi-step questions, while SLMs are
cheaper, private, and faster for focused tasks. A common strategy is to start with
a local SLM and move to a larger model only if answer quality demands it.
