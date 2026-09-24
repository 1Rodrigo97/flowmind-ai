<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Insights } from '../api'

const props = defineProps<{ documentId: number }>()
const insights = ref<Insights | null>(null)
const loading = ref(true)
const generating = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  try {
    insights.value = await api.getInsights(props.documentId)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function generate() {
  error.value = ''
  generating.value = true
  try {
    insights.value = await api.generateInsights(props.documentId)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <div class="insights">
    <p v-if="loading" class="muted"><span class="spinner" /> Carregando insights…</p>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="!insights">
      <p class="muted" style="margin-top: 0">Este documento ainda não tem insights.</p>
      <button class="btn" :disabled="generating" @click="generate">
        <span v-if="generating" class="spinner" /> {{ generating ? 'Analisando…' : 'Gerar insights' }}
      </button>
    </div>

    <template v-else>
      <div class="ins-block">
        <div class="ins-label">Resumo</div>
        <p style="margin: 0">{{ insights.summary || '—' }}</p>
      </div>

      <div class="ins-cols">
        <div class="ins-block">
          <div class="ins-label">Categoria</div>
          <span class="badge">{{ insights.category || '—' }}</span>
        </div>
        <div class="ins-block">
          <div class="ins-label">Tags</div>
          <span v-for="t in insights.tags" :key="t" class="badge" style="margin: 0 4px 4px 0">{{ t }}</span>
          <span v-if="!insights.tags.length" class="muted">—</span>
        </div>
      </div>

      <div class="ins-cols">
        <div class="ins-block">
          <div class="ins-label">Tarefas extraídas ({{ insights.tasks.length }})</div>
          <ul v-if="insights.tasks.length" style="margin: 0; padding-left: 18px">
            <li v-for="(t, i) in insights.tasks" :key="i">
              {{ t.text }}
              <span v-if="t.due_date" class="badge" style="margin-left: 6px">📅 {{ t.due_date }}</span>
            </li>
          </ul>
          <span v-else class="muted">Nenhuma tarefa no documento.</span>
        </div>
        <div class="ins-block">
          <div class="ins-label">Datas encontradas ({{ insights.dates.length }})</div>
          <span v-for="d in insights.dates" :key="d" class="badge" style="margin: 0 4px 4px 0">{{ d }}</span>
          <span v-if="!insights.dates.length" class="muted">Nenhuma data no documento.</span>
        </div>
      </div>

      <p class="muted" style="font-size: 12px; margin-bottom: 0">
        Gerado por {{ insights.model }} · fundamentado apenas no conteúdo do documento.
      </p>
    </template>
  </div>
</template>

<style scoped>
.insights { padding: 4px 2px; }
.ins-block { margin-bottom: 14px; }
.ins-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-dim);
  margin-bottom: 6px;
}
.ins-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 640px) { .ins-cols { grid-template-columns: 1fr; } }
</style>
