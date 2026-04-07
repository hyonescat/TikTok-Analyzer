<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="text-xl font-bold text-white">TikTok Analyzer</span>
        <span :class="statusClass" class="text-xs px-2 py-1 rounded-full font-medium uppercase">
          {{ status }}
        </span>
      </div>
      <button
        v-if="status !== 'running'"
        @click="showModal = true"
        class="bg-pink-600 hover:bg-pink-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
      >
        Run ▶
      </button>
      <button
        v-else
        @click="cancelRun"
        class="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
      >
        Cancel ✕
      </button>
    </header>

    <!-- Tabs -->
    <nav class="bg-gray-900 border-b border-gray-800 px-6 flex gap-1">
      <router-link
        v-for="tab in tabs" :key="tab.path" :to="tab.path"
        class="px-4 py-3 text-sm text-gray-400 hover:text-white border-b-2 border-transparent transition"
        active-class="text-white border-pink-500"
      >
        {{ tab.label }}
      </router-link>
    </nav>

    <!-- Content -->
    <main class="flex-1 overflow-auto p-6">
      <router-view />
    </main>

    <RunModal v-if="showModal" @close="showModal = false" @run="startRun" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import RunModal from './components/RunModal.vue'

const tabs = [
  { path: '/progress', label: 'Progress' },
  { path: '/results', label: 'Results' },
  { path: '/todo', label: 'To-Do List' },
  { path: '/history', label: 'History' },
]

const showModal = ref(false)
const status = ref('idle')

const statusClass = computed(() => ({
  'bg-gray-700 text-gray-300': status.value === 'idle',
  'bg-yellow-900 text-yellow-300': status.value === 'running',
  'bg-green-900 text-green-300': status.value === 'done',
  'bg-red-900 text-red-300': status.value === 'error',
}))

async function pollStatus() {
  try {
    const res = await fetch('/api/status')
    const data = await res.json()
    status.value = data.status
  } catch {}
}

async function cancelRun() {
  await fetch('/api/run/cancel', { method: 'POST' })
  status.value = 'idle'
}

async function startRun(config) {
  showModal.value = false
  await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  status.value = 'running'
}

onMounted(() => {
  pollStatus()
  setInterval(pollStatus, 3000)
})
</script>
