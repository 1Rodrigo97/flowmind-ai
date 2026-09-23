<script setup lang="ts">
const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: '■' },
  { to: '/documents', label: 'Documents', icon: '▤' },
  { to: '/assistant', label: 'Assistant', icon: '◈' },
  { to: '/explorer', label: 'RAG Explorer', icon: '◎' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
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
      <div class="sidebar-foot">Personal Knowledge &amp; Automation Assistant</div>
    </aside>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>
