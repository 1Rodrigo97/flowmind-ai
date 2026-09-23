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
  <h1 class="page-title">Configurações</h1>
  <p class="page-sub">Configuração de execução (somente leitura na V1).</p>

  <div class="card" style="max-width: 560px">
    <table>
      <tbody>
        <tr>
          <td class="muted">URL base da API</td>
          <td>{{ api.base }}</td>
        </tr>
        <tr>
          <td class="muted">Status do backend</td>
          <td>
            <span v-if="health === 'checking'" class="badge">verificando…</span>
            <span v-else-if="health === 'ok'" class="badge ok">online</span>
            <span v-else class="badge" style="color: #f0716f">offline</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="muted" style="margin-bottom: 0; margin-top: 16px">
      O provedor de LLM, o modelo de embeddings, o top-k de recuperação e o limiar
      de similaridade são configurados no backend via variáveis de ambiente (veja
      <code>.env.example</code>).
    </p>
  </div>
</template>
