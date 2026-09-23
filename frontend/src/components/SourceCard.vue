<script setup lang="ts">
import { ref } from 'vue'
import type { RetrievedChunk } from '../api'

defineProps<{ source: RetrievedChunk; showBar?: boolean }>()
const open = ref(false)
</script>

<template>
  <div class="source">
    <div class="source-head" @click="open = !open">
      <span>{{ open ? '▾' : '▸' }}</span>
      <span class="source-doc">{{ source.document }}</span>
      <span class="source-meta">
        <template v-if="source.section">· {{ source.section }}</template>
        <template v-if="source.page != null">· p.{{ source.page }}</template>
      </span>
      <span class="score-pill">{{ source.score.toFixed(3) }}</span>
    </div>
    <div v-if="showBar" style="padding: 0 12px 10px">
      <div class="score-bar">
        <span :style="{ width: Math.max(0, Math.min(100, source.score * 100)) + '%' }" />
      </div>
    </div>
    <div v-if="open" class="source-body">{{ source.excerpt }}</div>
  </div>
</template>
