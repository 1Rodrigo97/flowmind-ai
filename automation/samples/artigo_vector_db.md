# Bancos de Dados Vetoriais: uma visão geral

Bancos de dados vetoriais armazenam representações numéricas (embeddings) de textos,
imagens ou outros dados e permitem buscar itens semanticamente semelhantes.

## Como funcionam

Cada item é convertido em um vetor de dimensão fixa. A busca calcula a distância
(por exemplo, cosseno) entre o vetor da consulta e os vetores armazenados, retornando
os itens mais próximos.

## Índices

Para acelerar a busca em grandes coleções, esses bancos usam índices aproximados como
HNSW ou IVF, que trocam um pouco de precisão por muita velocidade.

## Uso em RAG

Em sistemas de Geração Aumentada por Recuperação, o banco vetorial guarda os trechos
dos documentos e devolve os mais relevantes para fundamentar a resposta do modelo.

Este é um artigo puramente conceitual, sem ações a executar nem prazos.
