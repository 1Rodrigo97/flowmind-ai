<script setup lang="ts">
import { ref } from 'vue'
import { api, type SearchResponse } from '../api'
import SourceCard from '../components/SourceCard.vue'

const query = ref('')
const topK = ref(5)
const useRerank = ref(false)
const response = ref<SearchResponse | null>(null)
const loading = ref(false)
const error = ref('')
const lastQuery = ref('')

async function run() {
  const q = query.value.trim()
  if (!q || loading.value) return
  error.value = ''
  loading.value = true
  try {
    response.value = await api.search(q, topK.value, useRerank.value)
    lastQuery.value = response.value.query
  } catch (e) {
    error.value = (e as Error).message
    response.value = null
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
    <span class="step">Top-N</span>→
    <span class="step" :class="{ dim: !useRerank }">Reranker</span>→
    <span class="step">Top-K</span>
  </div>

  <div style="display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap">
    <div style="flex: 1; min-width: 220px">
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
    <div>
      <label>Reranking</label>
      <label class="rr-switch">
        <input v-model="useRerank" type="checkbox" />
        <span>{{ useRerank ? 'ligado' : 'desligado' }}</span>
      </label>
    </div>
    <button class="btn" :disabled="loading" @click="run">Buscar</button>
  </div>

  <div v-if="error" class="error" style="margin-top: 14px">{{ error }}</div>
  <div v-if="loading" style="margin-top: 20px"><span class="spinner" /> Buscando…</div>

  <template v-else-if="response">
    <!-- Reranking on: show original vs reranked side by side -->
    <div v-if="response.reranker && response.original" class="rerank-view">
      <div>
        <div class="col-title">Retrieval original <span class="muted">(similaridade)</span></div>
        <SourceCard v-for="(s, i) in response.original" :key="'o' + i" :source="s" :show-bar="true" />
      </div>
      <div>
        <div class="col-title">Após reranking <span class="muted">({{ response.reranker }})</span></div>
        <SourceCard v-for="(s, i) in response.results" :key="'r' + i" :source="s" />
      </div>
    </div>

    <!-- Reranking off: single ranked list -->
    <template v-else>
      <p class="muted" style="margin-top: 20px">
        {{ response.results.length }} trecho(s) para “{{ lastQuery }}”, ordenados por similaridade de cosseno:
      </p>
      <SourceCard v-for="(s, i) in response.results" :key="i" :source="s" :show-bar="true" />
      <p v-if="!response.results.length" class="muted">Nenhum trecho encontrado. Indexe alguns documentos primeiro.</p>
    </template>
  </template>
</template>

<style scoped>
.rerank-view {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: 20px;
}
@media (max-width: 760px) {
  .rerank-view { grid-template-columns: 1fr; }
}
.col-title { font-weight: 700; margin-bottom: 10px; }
.step.dim { opacity: 0.4; }
.rr-switch { display: flex; align-items: center; gap: 8px; color: var(--text); height: 40px; }
.rr-switch input { width: auto; }
</style>
