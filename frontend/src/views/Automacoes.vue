<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AutomationRun, type AutomationStats } from '../api'
import InsightsPanel from '../components/InsightsPanel.vue'

const stats = ref<AutomationStats | null>(null)
const runs = ref<AutomationRun[]>([])
const categoryByDoc = ref<Record<number, string>>({})
const error = ref('')
const loading = ref(true)
const expanded = ref<number | null>(null)
const retrying = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    const [s, r, docs] = await Promise.all([
      api.automationStats(),
      api.listRuns(),
      api.listDocuments(),
    ])
    stats.value = s
    runs.value = r
    categoryByDoc.value = Object.fromEntries(
      docs.filter((d) => d.category).map((d) => [d.id, d.category as string]),
    )
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
onMounted(load)

function toggle(id: number) {
  expanded.value = expanded.value === id ? null : id
}

async function retry(run: AutomationRun) {
  retrying.value = run.id
  try {
    await api.retryRun(run.id)
    await load()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    retrying.value = null
  }
}

const STATUS_CLASS: Record<string, string> = {
  SUCCESS: 'ok',
  DUPLICATE: 'dup',
  FAILED: 'fail',
  PENDING: 'pend',
}
function fmt(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR')
}
</script>

<template>
  <h1 class="page-title">Automações</h1>
  <p class="page-sub">Processamento automático de arquivos da inbox via n8n → FlowMind.</p>

  <p v-if="loading"><span class="spinner" /> Carregando…</p>
  <div v-else-if="error" class="error">{{ error }}</div>

  <template v-else-if="stats">
    <div class="grid grid-5">
      <div class="card"><div class="stat">{{ stats.processed }}</div><div class="stat-label">Processados</div></div>
      <div class="card"><div class="stat">{{ stats.success }}</div><div class="stat-label">Sucessos</div></div>
      <div class="card"><div class="stat">{{ stats.duplicate }}</div><div class="stat-label">Duplicados</div></div>
      <div class="card"><div class="stat">{{ stats.failed }}</div><div class="stat-label">Falhas</div></div>
      <div class="card"><div class="stat">{{ Math.round(stats.avg_duration_ms) }}<small style="font-size:14px">ms</small></div><div class="stat-label">Tempo médio</div></div>
    </div>

    <div class="card" style="margin-top: 16px; padding: 0">
      <table>
        <thead>
          <tr>
            <th></th><th>Arquivo</th><th>Categoria</th><th>Status</th><th>Insights</th>
            <th>Tent.</th><th>Doc</th><th>Data</th><th>Duração</th><th></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="r in runs" :key="r.id">
            <tr class="run-row" @click="toggle(r.id)">
              <td>{{ expanded === r.id ? '▾' : '▸' }}</td>
              <td>{{ r.filename }}</td>
              <td>
                <span v-if="r.document_id && categoryByDoc[r.document_id]" class="badge">
                  {{ categoryByDoc[r.document_id] }}
                </span>
                <span v-else class="muted">—</span>
              </td>
              <td><span class="badge" :class="STATUS_CLASS[r.status]">{{ r.status }}</span></td>
              <td>
                <span v-if="r.insights_status" class="badge" :class="r.insights_status === 'SUCCESS' ? 'ok' : 'fail'">
                  {{ r.insights_status }}
                </span>
                <span v-else class="muted">—</span>
              </td>
              <td>{{ r.attempts }}</td>
              <td class="muted">{{ r.document_id ?? '—' }}</td>
              <td class="muted" style="font-size: 12px">{{ fmt(r.started_at) }}</td>
              <td class="muted">{{ r.duration_ms ? Math.round(r.duration_ms) + ' ms' : '—' }}</td>
              <td>
                <button
                  v-if="r.status === 'FAILED' || r.insights_status === 'FAILED'"
                  class="btn-ghost"
                  style="padding: 4px 10px; font-size: 12px"
                  :disabled="retrying === r.id"
                  @click.stop="retry(r)"
                >{{ retrying === r.id ? '…' : 'Retry' }}</button>
              </td>
            </tr>
            <tr v-if="expanded === r.id">
              <td colspan="10" style="background: var(--surface-2)">
                <div v-if="r.error_message" class="error" style="margin: 8px 0">{{ r.error_message }}</div>
                <div class="muted" style="font-size: 12px; margin: 4px 0 10px">
                  Execução {{ r.run_uid }} · workflow "{{ r.workflow }}" · tentativa {{ r.attempts }}
                  <template v-if="r.finished_at"> · concluída em {{ fmt(r.finished_at) }}</template>
                </div>
                <InsightsPanel v-if="r.document_id" :document-id="r.document_id" :key="r.document_id" />
                <p v-else class="muted">Sem documento associado (ingestão não concluída).</p>
              </td>
            </tr>
          </template>
          <tr v-if="!runs.length">
            <td colspan="10" class="muted" style="padding: 20px">
              Nenhuma execução ainda. Copie um arquivo de <code>automation/samples/</code> para
              <code>automation/inbox/</code> e dispare o workflow no n8n.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>

<style scoped>
.grid-5 { grid-template-columns: repeat(5, 1fr); }
@media (max-width: 760px) { .grid-5 { grid-template-columns: repeat(2, 1fr); } }
.run-row { cursor: pointer; }
.run-row:hover { background: var(--surface-2); }
.badge.dup { color: var(--warn); background: rgba(210, 153, 34, 0.14); }
.badge.fail { color: #f0716f; background: rgba(240, 113, 111, 0.12); }
.badge.pend { color: var(--accent); background: rgba(79, 140, 255, 0.14); }
</style>
