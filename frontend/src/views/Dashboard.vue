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
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <h1 class="page-title">Dashboard</h1>
  <p class="page-sub">Overview of your indexed knowledge base.</p>

  <p v-if="loading"><span class="spinner" /> Loading…</p>
  <div v-else-if="error" class="error">Could not reach the API: {{ error }}</div>

  <template v-else-if="stats">
    <div class="grid grid-4">
      <div class="card">
        <div class="stat">{{ stats.documents }}</div>
        <div class="stat-label">Documents</div>
      </div>
      <div class="card">
        <div class="stat">{{ stats.chunks }}</div>
        <div class="stat-label">Chunks</div>
      </div>
      <div class="card">
        <div class="stat">{{ Object.keys(stats.file_types).length }}</div>
        <div class="stat-label">File types</div>
      </div>
      <div class="card">
        <div class="stat">
          {{ stats.documents ? Math.round(stats.chunks / stats.documents) : 0 }}
        </div>
        <div class="stat-label">Avg chunks / doc</div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 1fr 2fr; margin-top: 16px">
      <div class="card">
        <h3 style="margin-top: 0">File types</h3>
        <table>
          <tbody>
            <tr v-for="(count, type) in stats.file_types" :key="type">
              <td><span class="badge">{{ type }}</span></td>
              <td style="text-align: right">{{ count }}</td>
            </tr>
            <tr v-if="!Object.keys(stats.file_types).length">
              <td class="muted">No documents yet.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3 style="margin-top: 0">Recent documents</h3>
        <table>
          <thead>
            <tr><th>Name</th><th>Type</th><th>Chunks</th><th>Added</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in stats.recent" :key="d.id">
              <td>{{ d.filename }}</td>
              <td><span class="badge">{{ d.file_type }}</span></td>
              <td>{{ d.chunk_count }}</td>
              <td class="muted">{{ fmtDate(d.created_at) }}</td>
            </tr>
            <tr v-if="!stats.recent.length">
              <td colspan="4" class="muted">Upload a document to get started.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>
