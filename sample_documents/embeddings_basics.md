# Embeddings Basics

## What an embedding is

An embedding is a dense vector of floating-point numbers that represents the
meaning of a piece of text. Texts with similar meaning are mapped to vectors that
are close together in the embedding space.

## Similarity measures

Cosine similarity is the most common way to compare embeddings. It measures the
angle between two vectors and ignores their magnitude, returning a value where
higher means more similar. Vector databases such as pgvector can compute cosine
distance directly and return the nearest chunks for a query.

## Role in RAG

In a RAG pipeline, both the stored chunks and the incoming query are embedded
with the same model. Retrieval finds the chunks whose embeddings are closest to
the query embedding. Using the same embedding model for indexing and querying is
essential, otherwise the vectors are not comparable.

## Choosing a model

Small local embedding models are often enough for personal knowledge bases. They
run offline, cost nothing per call, and produce vectors of a fixed dimension such
as 384 or 768. Larger models can improve retrieval quality at higher cost.
