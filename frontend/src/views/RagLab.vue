<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type Experiment, type CompareResponse } from '../api'

const experiments = ref<Experiment[]>([])
const running = ref(false)
const error = ref('')

const form = ref({
  name: 'baseline-nomic-k5',
  chunk_size: 700,
  chunk_overlap: 100,
  top_k: 5,
  similarity_threshold: 0.55,
  reranker_enabled: false,
})

const selected = ref<number[]>([])
const comparison = ref<CompareResponse | null>(null)

async function load() {
  try {
    experiments.value = await api.listExperiments()
  } catch (e) {
    error.value = (e as Error).message
  }
}
onMounted(load)

async function run() {
  error.value = ''
  running.value = true
  try {
    await api.runExperiment({
      name: form.value.name,
      chunk_size: form.value.chunk_size,
      chunk_overlap: form.value.chunk_overlap,
      top_k: form.value.top_k,
      similarity_threshold: form.value.similarity_threshold,
      reranker_enabled: form.value.reranker_enabled,
      reranker_model: 'lexical',
      reranker_candidates: 15,
    })
    await load()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    running.value = false
  }
}

function toggleSelect(id: number) {
  const i = selected.value.indexOf(id)
  if (i >= 0) selected.value.splice(i, 1)
  else selected.value.push(id)
  comparison.value = null
}

async function compare() {
  error.value = ''
  try {
    comparison.value = await api.compareExperiments(selected.value)
  } catch (e) {
    error.value = (e as Error).message
  }
}

const pct = (v: number) => `${Math.round(v * 100)}%`
const cmpExps = computed(() => comparison.value?.experiments ?? [])

function delta(metric: string, id: number): number | null {
  const d = comparison.value?.deltas?.[metric]
  if (!d || !(id in d)) return null
  return d[id]
}
</script>

<template>
  <h1 class="page-title">Laboratório RAG</h1>
  <p class="page-sub">
    Execute experimentos reproduzíveis e meça objetivamente qual configuração recupera melhor.
  </p>

  <!-- Config -->
  <div class="card">
    <h3 style="margin-top: 0">Configuração do experimento</h3>
    <div class="lab-grid">
      <div>
        <label>Nome</label>
        <input v-model="form.name" type="text" />
      </div>
      <div>
        <label>chunk_size</label>
        <select v-model.number="form.chunk_size"><option>400</option><option>700</option><option>1000</option></select>
      </div>
      <div>
        <label>chunk_overlap</label>
        <input v-model.number="form.chunk_overlap" type="number" min="0" max="400" />
      </div>
      <div>
        <label>top_k</label>
        <select v-model.number="form.top_k"><option>3</option><option>5</option><option>8</option></select>
      </div>
      <div>
        <label>similarity_threshold</label>
        <select v-model.number="form.similarity_threshold"><option>0.45</option><option>0.55</option><option>0.65</option></select>
      </div>
      <div>
        <label>Reranking</label>
        <label class="switch">
          <input v-model="form.reranker_enabled" type="checkbox" />
          <span>{{ form.reranker_enabled ? 'ligado (lexical)' : 'desligado' }}</span>
        </label>
      </div>
    </div>
    <div style="margin-top: 14px">
      <button class="btn" :disabled="running" @click="run">
        <span v-if="running" class="spinner" /> {{ running ? 'Executando…' : 'Executar avaliação' }}
      </button>
    </div>
  </div>

  <div v-if="error" class="error" style="margin-top: 14px">{{ error }}</div>

  <!-- Experiments table -->
  <div class="card" style="margin-top: 16px; padding: 0">
    <div style="padding: 14px 18px 0"><h3 style="margin: 0">Experimentos</h3></div>
    <table>
      <thead>
        <tr>
          <th></th><th>Nome</th><th>Profile</th><th>Rerank</th>
          <th>Hit@K</th><th>MRR</th><th>P@K</th><th>R@K</th><th>Recusa</th><th>Retr. ms</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in experiments" :key="e.id">
          <td><input type="checkbox" :checked="selected.includes(e.id)" @change="toggleSelect(e.id)" /></td>
          <td>{{ e.name }}</td>
          <td class="muted" style="font-size: 12px">{{ e.index_profile }}</td>
          <td>
            <span class="badge" :class="{ ok: e.config?.reranker_enabled }">
              {{ e.config?.reranker_enabled ? 'on' : '—' }}
            </span>
          </td>
          <td>{{ pct(e.metrics.hit_at_k) }}</td>
          <td>{{ e.metrics.mrr.toFixed(2) }}</td>
          <td>{{ e.metrics.precision_at_k.toFixed(2) }}</td>
          <td>{{ pct(e.metrics.recall_at_k) }}</td>
          <td>{{ pct(e.metrics.correct_refusal_rate) }}</td>
          <td>{{ Math.round(e.metrics.latency_retrieval_ms) }}</td>
        </tr>
        <tr v-if="!experiments.length">
          <td colspan="10" class="muted" style="padding: 20px">
            Nenhum experimento ainda. Configure acima e execute uma avaliação.
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="selected.length >= 2" style="margin-top: 14px">
    <button class="btn-ghost" @click="compare">Comparar selecionados ({{ selected.length }})</button>
  </div>

  <!-- Comparison -->
  <div v-if="comparison" class="card" style="margin-top: 16px">
    <h3 style="margin-top: 0">Comparação</h3>
    <div class="compare">
      <div v-for="(e, idx) in cmpExps" :key="e.id" class="compare-col">
        <div class="compare-head">
          {{ e.name }}
          <span class="badge">{{ idx === 0 ? 'baseline' : 'variante' }}</span>
        </div>
        <div class="metric-row"><span>Hit@K</span><b>{{ pct(e.metrics.hit_at_k) }}</b></div>
        <div class="metric-row">
          <span>MRR</span>
          <b>{{ e.metrics.mrr.toFixed(2) }}
            <em v-if="delta('mrr', e.id) !== null" :class="(delta('mrr', e.id) ?? 0) >= 0 ? 'up' : 'down'">
              {{ (delta('mrr', e.id) ?? 0) >= 0 ? '▲' : '▼' }} {{ (delta('mrr', e.id) ?? 0).toFixed(2) }}
            </em>
          </b>
        </div>
        <div class="metric-row"><span>Precision@K</span><b>{{ e.metrics.precision_at_k.toFixed(2) }}</b></div>
        <div class="metric-row"><span>Recall@K</span><b>{{ pct(e.metrics.recall_at_k) }}</b></div>
        <div class="metric-row"><span>Recusa correta</span><b>{{ pct(e.metrics.correct_refusal_rate) }}</b></div>
        <div class="metric-row">
          <span>Latência retrieval</span>
          <b>{{ Math.round(e.metrics.latency_retrieval_ms) }} ms
            <em v-if="delta('latency_retrieval_ms', e.id) !== null" :class="(delta('latency_retrieval_ms', e.id) ?? 0) <= 0 ? 'up' : 'down'">
              {{ (delta('latency_retrieval_ms', e.id) ?? 0) >= 0 ? '+' : '' }}{{ Math.round(delta('latency_retrieval_ms', e.id) ?? 0) }}
            </em>
          </b>
        </div>
      </div>
    </div>
    <p class="muted" style="margin-bottom: 0; margin-top: 12px; font-size: 12px">
      Deltas relativos ao primeiro experimento selecionado (baseline). Ganho/perda mostrado sem julgamento.
    </p>
  </div>
</template>

<style scoped>
.lab-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
@media (max-width: 760px) {
  .lab-grid { grid-template-columns: 1fr; }
}
select {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  padding: 10px 12px;
  font-family: inherit;
  font-size: 14px;
}
.switch { display: flex; align-items: center; gap: 8px; color: var(--text); }
.switch input { width: auto; }
.compare { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 760px) { .compare { grid-template-columns: 1fr; } }
.compare-col { border: 1px solid var(--border); border-radius: 8px; padding: 14px; background: var(--surface-2); }
.compare-head { font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
.metric-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }
.metric-row:last-child { border-bottom: none; }
.up { color: var(--good); font-style: normal; font-size: 12px; margin-left: 4px; }
.down { color: #f0716f; font-style: normal; font-size: 12px; margin-left: 4px; }
</style>
