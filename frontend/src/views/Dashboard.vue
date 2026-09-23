<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type StatsResponse } from '../api'

const stats = ref<StatsResponse | null>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    stats.value = await api.stats()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR')
}
</script>

<template>
  <h1 class="page-title">Painel</h1>
  <p class="page-sub">Visão geral da sua base de conhecimento indexada.</p>

  <p v-if="loading"><span class="spinner" /> Carregando…</p>
  <div v-else-if="error" class="error">Não foi possível acessar a API: {{ error }}</div>

  <template v-else-if="stats">
    <div class="grid grid-4">
      <div class="card">
        <div class="stat">{{ stats.documents }}</div>
        <div class="stat-label">Documentos</div>
      </div>
      <div class="card">
        <div class="stat">{{ stats.chunks }}</div>
        <div class="stat-label">Trechos</div>
      </div>
      <div class="card">
        <div class="stat">{{ Object.keys(stats.file_types).length }}</div>
        <div class="stat-label">Tipos de arquivo</div>
      </div>
      <div class="card">
        <div class="stat">
          {{ stats.documents ? Math.round(stats.chunks / stats.documents) : 0 }}
        </div>
        <div class="stat-label">Média de trechos / doc</div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 1fr 2fr; margin-top: 16px">
      <div class="card">
        <h3 style="margin-top: 0">Tipos de arquivo</h3>
        <table>
          <tbody>
            <tr v-for="(count, type) in stats.file_types" :key="type">
              <td><span class="badge">{{ type }}</span></td>
              <td style="text-align: right">{{ count }}</td>
            </tr>
            <tr v-if="!Object.keys(stats.file_types).length">
              <td class="muted">Nenhum documento ainda.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3 style="margin-top: 0">Documentos recentes</h3>
        <table>
          <thead>
            <tr><th>Nome</th><th>Tipo</th><th>Trechos</th><th>Adicionado</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in stats.recent" :key="d.id">
              <td>{{ d.filename }}</td>
              <td><span class="badge">{{ d.file_type }}</span></td>
              <td>{{ d.chunk_count }}</td>
              <td class="muted">{{ fmtDate(d.created_at) }}</td>
            </tr>
            <tr v-if="!stats.recent.length">
              <td colspan="4" class="muted">Envie um documento para começar.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>
