# Retrieval-Augmented Generation (RAG)

## What is RAG

Retrieval-Augmented Generation (RAG) is a technique that combines a retrieval
system with a generative language model. Instead of relying only on the
parameters learned during training, a RAG system first retrieves relevant
passages from an external knowledge base and then conditions the model's answer
on that retrieved context.

## Why use RAG

RAG grounds answers in a specific corpus. This reduces hallucination because the
model is instructed to answer from the retrieved context rather than from its
prior knowledge. It also lets you update the knowledge base without retraining
the model: adding a new document immediately changes what the system can answer.

## RAG vs fine-tuning

RAG and fine-tuning solve different problems. Fine-tuning changes the weights of
the model to adjust its style or teach durable skills, while RAG injects fresh,
source-grounded facts at query time. RAG is usually cheaper to keep current
because knowledge lives in a vector store, not in the weights.

## Core pipeline

A typical RAG pipeline is: document ingestion, text extraction, chunking,
embedding generation, storage in a vector database, retrieval of the top matching
chunks for a query, context assembly, and finally generation by the language
model. Each retrieved chunk should carry metadata such as the source document and
section so that answers can be cited.
