<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { api, type RetrievedChunk } from '../api'
import SourceCard from '../components/SourceCard.vue'

interface Message {
  role: 'user' | 'ai'
  text: string
  sources?: RetrievedChunk[]
  status?: string
}

const messages = ref<Message[]>([])
const question = ref('')
const topK = ref(5)
const loading = ref(false)
const error = ref('')
const thread = ref<HTMLElement | null>(null)

async function ask() {
  const q = question.value.trim()
  if (!q || loading.value) return
  error.value = ''
  messages.value.push({ role: 'user', text: q })
  question.value = ''
  loading.value = true
  await scroll()
  try {
    const res = await api.chat(q, topK.value)
    messages.value.push({
      role: 'ai',
      text: res.answer,
      sources: res.sources,
      status: res.status,
    })
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
    await scroll()
  }
}

async function scroll() {
  await nextTick()
  thread.value?.scrollTo({ top: thread.value.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <h1 class="page-title">Assistente</h1>
  <p class="page-sub">Faça perguntas fundamentadas nos seus documentos indexados.</p>

  <div ref="thread" class="card" style="min-height: 340px; max-height: 58vh; overflow-y: auto">
    <p v-if="!messages.length" class="muted">
      Pergunte algo como “Qual é a diferença entre RAG e fine-tuning?”
    </p>

    <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
      <div class="bubble">{{ m.text }}</div>
      <template v-if="m.role === 'ai' && m.status === 'answered' && m.sources?.length">
        <div class="sources-title">Fontes utilizadas</div>
        <SourceCard v-for="(s, j) in m.sources" :key="j" :source="s" />
      </template>
      <div v-else-if="m.role === 'ai' && m.status === 'insufficient_context'" class="sources-title">
        Nenhuma fonte atingiu o limiar mínimo de confiança.
      </div>
    </div>

    <p v-if="loading" class="muted"><span class="spinner" /> Pensando…</p>
  </div>

  <div v-if="error" class="error" style="margin-top: 12px">{{ error }}</div>

  <div style="display: flex; gap: 10px; margin-top: 14px; align-items: flex-end">
    <div style="flex: 1">
      <textarea
        v-model="question"
        rows="2"
        placeholder="Digite sua pergunta e pressione Enter…"
        @keydown.enter.exact.prevent="ask"
      />
    </div>
    <div style="width: 90px">
      <label>top_k</label>
      <input v-model.number="topK" type="number" min="1" max="20" />
    </div>
    <button class="btn" :disabled="loading" @click="ask">Perguntar</button>
  </div>
</template>
