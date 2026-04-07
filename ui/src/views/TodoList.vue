<template>
  <div class="max-w-3xl mx-auto">
    <div v-if="loading" class="text-gray-500 text-sm text-center py-12">Loading…</div>
    <div v-else-if="!content" class="text-gray-500 text-sm text-center py-12">
      No to-do list yet. Run an analysis first.
    </div>
    <div v-else>
      <div class="flex justify-end mb-4">
        <button @click="copyToClipboard"
          class="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded transition">
          {{ copied ? '✓ Copied' : 'Copy markdown' }}
        </button>
      </div>
      <div class="prose prose-invert max-w-none" v-html="rendered" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'

const content = ref('')
const loading = ref(true)
const copied = ref(false)

const rendered = computed(() => content.value ? marked(content.value) : '')

async function loadTodo() {
  try {
    const res = await fetch('/api/results/todo')
    if (res.ok) content.value = await res.text()
  } catch {}
  loading.value = false
}

async function copyToClipboard() {
  await navigator.clipboard.writeText(content.value)
  copied.value = true
  setTimeout(() => copied.value = false, 2000)
}

onMounted(loadTodo)
</script>
