<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type DocumentOut } from '../api'
import InsightsPanel from '../components/InsightsPanel.vue'

const docs = ref<DocumentOut[]>([])
const openInsights = ref<number | null>(null)
function toggleInsights(id: number) {
  openInsights.value = openInsights.value === id ? null : id
}
const error = ref('')
const notice = ref('')
const uploading = ref(false)
const dragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

async function load() {
  try {
    docs.value = await api.listDocuments()
  } catch (e) {
    error.value = (e as Error).message
  }
}

onMounted(load)

async function handleFiles(files: FileList | null) {
  if (!files || !files.length) return
  error.value = ''
  notice.value = ''
  uploading.value = true
  try {
    for (const file of Array.from(files)) {
      const res = await api.uploadDocument(file)
      notice.value = res.duplicate
        ? `"${res.filename}" já está indexado (ignorado).`
        : `"${res.filename}" indexado em ${res.chunks} trechos.`
    }
    await load()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  handleFiles(e.dataTransfer?.files ?? null)
}

async function remove(id: number) {
  try {
    await api.deleteDocument(id)
    await load()
  } catch (e) {
    error.value = (e as Error).message
  }
}

function fmtSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(0)} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const STATUS_PT: Record<string, string> = {
  indexed: 'indexado',
  duplicate: 'duplicado',
  processing: 'processando',
}
function statusPt(s: string): string {
  return STATUS_PT[s] ?? s
}
</script>

<template>
  <h1 class="page-title">Documentos</h1>
  <p class="page-sub">Envie arquivos para indexá-los na base de conhecimento.</p>

  <div
    class="dropzone"
    :class="{ drag: dragging }"
    @click="fileInput?.click()"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.docx,.md,.txt"
      multiple
      hidden
      @change="handleFiles(($event.target as HTMLInputElement).files)"
    />
    <p v-if="uploading"><span class="spinner" /> Indexando…</p>
    <template v-else>
      <p style="margin: 0; font-weight: 600; color: var(--text)">
        Arraste e solte os arquivos aqui, ou clique para selecionar
      </p>
      <p style="margin: 6px 0 0">Suportados: PDF, DOCX, MD, TXT</p>
    </template>
  </div>

  <p v-if="notice" class="badge ok" style="margin-top: 14px">{{ notice }}</p>
  <div v-if="error" class="error" style="margin-top: 14px">{{ error }}</div>

  <div class="card" style="margin-top: 20px; padding: 0">
    <table>
      <thead>
        <tr><th>Nome</th><th>Tipo</th><th>Categoria</th><th>Tags</th><th>Trechos</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        <template v-for="d in docs" :key="d.id">
          <tr>
            <td>{{ d.filename }}</td>
            <td><span class="badge">{{ d.file_type }}</span></td>
            <td>
              <span v-if="d.category" class="badge">{{ d.category }}</span>
              <span v-else class="muted">—</span>
            </td>
            <td>
              <span v-for="t in (d.tags || []).slice(0, 3)" :key="t" class="badge" style="margin: 0 3px 3px 0">{{ t }}</span>
              <span v-if="!d.tags || !d.tags.length" class="muted">—</span>
            </td>
            <td>{{ d.chunk_count }}</td>
            <td><span class="badge ok">{{ statusPt(d.status) }}</span></td>
            <td style="text-align: right; white-space: nowrap">
              <button class="btn-ghost" style="padding: 5px 10px; font-size: 12px" @click="toggleInsights(d.id)">
                {{ openInsights === d.id ? 'Ocultar' : 'Ver insights' }}
              </button>
              <button class="btn-danger" style="margin-left: 6px" @click="remove(d.id)">Excluir</button>
            </td>
          </tr>
          <tr v-if="openInsights === d.id">
            <td colspan="7" style="background: var(--surface-2)">
              <InsightsPanel :document-id="d.id" :key="d.id" />
            </td>
          </tr>
        </template>
        <tr v-if="!docs.length">
          <td colspan="7" class="muted" style="padding: 20px">Nenhum documento indexado ainda.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
