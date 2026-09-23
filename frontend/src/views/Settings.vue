<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

const health = ref<'checking' | 'ok' | 'down'>('checking')

onMounted(async () => {
  try {
    await api.stats()
    health.value = 'ok'
  } catch {
    health.value = 'down'
  }
})
</script>

<template>
  <h1 class="page-title">Settings</h1>
  <p class="page-sub">Runtime configuration (read-only in V1).</p>

  <div class="card" style="max-width: 560px">
    <table>
      <tbody>
        <tr>
          <td class="muted">API base URL</td>
          <td>{{ api.base }}</td>
        </tr>
        <tr>
          <td class="muted">Backend status</td>
          <td>
            <span v-if="health === 'checking'" class="badge">checking…</span>
            <span v-else-if="health === 'ok'" class="badge ok">online</span>
            <span v-else class="badge" style="color: #f0716f">offline</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="muted" style="margin-bottom: 0; margin-top: 16px">
      LLM provider, embedding model, retrieval top-k and the similarity threshold
      are configured on the backend via environment variables (see
      <code>.env.example</code>).
    </p>
  </div>
</template>
