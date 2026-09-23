<script setup lang="ts">
const nav = [
  { to: '/dashboard', label: 'Painel', icon: '■' },
  { to: '/documents', label: 'Documentos', icon: '▤' },
  { to: '/assistant', label: 'Assistente', icon: '◈' },
  { to: '/explorer', label: 'Explorador RAG', icon: '◎' },
  { to: '/settings', label: 'Configurações', icon: '⚙' },
]
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">F</span>
        <span>FlowMind AI</span>
      </div>
      <RouterLink v-for="n in nav" :key="n.to" :to="n.to" class="nav-item">
        <span>{{ n.icon }}</span>
        <span>{{ n.label }}</span>
      </RouterLink>
      <div class="nav-spacer" />
      <div class="sidebar-foot">Assistente Pessoal de Conhecimento &amp; Automação</div>
    </aside>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>
