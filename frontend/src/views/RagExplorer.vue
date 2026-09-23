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
  <h1 class="page-title">Explorador RAG</h1>
  <p class="page-sub">Inspecione a recuperação pura — os trechos e scores de similaridade, sem LLM.</p>

  <div class="flow">
    <span class="step">Consulta</span>→
    <span class="step">Embedding</span>→
    <span class="step">Busca pgvector</span>→
    <span class="step">Top-k trechos</span>→
    <span class="step">Score de similaridade</span>
  </div>

  <div style="display: flex; gap: 10px; align-items: flex-end">
    <div style="flex: 1">
      <label>Consulta</label>
      <input
        v-model="query"
        type="text"
        placeholder="ex.: como os embeddings são comparados?"
        @keydown.enter="run"
      />
    </div>
    <div style="width: 90px">
      <label>top_k</label>
      <input v-model.number="topK" type="number" min="1" max="20" />
    </div>
    <button class="btn" :disabled="loading" @click="run">Buscar</button>
  </div>

  <div v-if="error" class="error" style="margin-top: 14px">{{ error }}</div>

  <div v-if="loading" style="margin-top: 20px"><span class="spinner" /> Buscando…</div>

  <template v-else-if="results">
    <p class="muted" style="margin-top: 20px">
      {{ results.length }} trecho(s) para “{{ lastQuery }}”, ordenados por similaridade de cosseno:
    </p>
    <SourceCard v-for="(s, i) in results" :key="i" :source="s" :show-bar="true" />
    <p v-if="!results.length" class="muted">Nenhum trecho encontrado. Indexe alguns documentos primeiro.</p>
  </template>
</template>
