<script setup lang="ts">
import { ref } from 'vue'
import { api, type RetrievedChunk } from '../api'
import SourceCard from '../components/SourceCard.vue'

const query = ref('')
const topK = ref(5)
const results = ref<RetrievedChunk[] | null>(null)
const loading = ref(false)
const error = ref('')
const lastQuery = ref('')

async function run() {
  const q = query.value.trim()
  if (!q || loading.value) return
  error.value = ''
  loading.value = true
  try {
    const res = await api.search(q, topK.value)
    results.value = res.results
    lastQuery.value = res.query
  } catch (e) {
    error.value = (e as Error).message
    results.value = null
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <h1 class="page-title">RAG Explorer</h1>
  <p class="page-sub">Inspect pure retrieval — the chunks and similarity scores, no LLM.</p>

  <div class="flow">
    <span class="step">Query</span>→
    <span class="step">Embedding</span>→
    <span class="step">pgvector search</span>→
    <span class="step">Top-k chunks</span>→
    <span class="step">Similarity score</span>
  </div>

  <div style="display: flex; gap: 10px; align-items: flex-end">
    <div style="flex: 1">
      <label>Query</label>
      <input
        v-model="query"
        type="text"
        placeholder="e.g. how are embeddings compared?"
        @keydown.enter="run"
      />
    </div>
    <div style="width: 90px">
      <label>top_k</label>
      <input v-model.number="topK" type="number" min="1" max="20" />
    </div>
    <button class="btn" :disabled="loading" @click="run">Retrieve</button>
  </div>

  <div v-if="error" class="error" style="margin-top: 14px">{{ error }}</div>

  <div v-if="loading" style="margin-top: 20px"><span class="spinner" /> Retrieving…</div>

  <template v-else-if="results">
    <p class="muted" style="margin-top: 20px">
      {{ results.length }} chunk(s) for “{{ lastQuery }}”, ranked by cosine similarity:
    </p>
    <SourceCard v-for="(s, i) in results" :key="i" :source="s" :show-bar="true" />
    <p v-if="!results.length" class="muted">No chunks found. Index some documents first.</p>
  </template>
</template>
