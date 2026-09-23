import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Documents from './views/Documents.vue'
import Assistant from './views/Assistant.vue'
import RagExplorer from './views/RagExplorer.vue'
import RagLab from './views/RagLab.vue'
import Settings from './views/Settings.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'Dashboard', component: Dashboard },
    { path: '/documents', name: 'Documents', component: Documents },
    { path: '/assistant', name: 'Assistant', component: Assistant },
    { path: '/explorer', name: 'RAG Explorer', component: RagExplorer },
    { path: '/lab', name: 'RAG Lab', component: RagLab },
    { path: '/settings', name: 'Settings', component: Settings },
  ],
})
