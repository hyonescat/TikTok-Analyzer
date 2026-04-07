<template>
  <div class="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
    <button
      @click="open = !open"
      class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-750 transition"
    >
      <div class="flex items-center gap-3 min-w-0">
        <span class="text-pink-400 text-xs font-medium uppercase shrink-0">{{ data.source }}</span>
        <span class="text-gray-200 text-sm truncate">{{ data.caption || data.video_id }}</span>
      </div>
      <div class="flex items-center gap-3 shrink-0 ml-3">
        <span class="text-gray-400 text-xs">❤️ {{ formatCount(data.like_count) }}</span>
        <span class="text-gray-500 text-xs">@{{ data.author_username }}</span>
        <span class="text-gray-500">{{ open ? '▲' : '▼' }}</span>
      </div>
    </button>
    <div v-if="open" class="px-4 pb-4 border-t border-gray-700">
      <p class="text-gray-300 text-sm leading-relaxed mt-3 whitespace-pre-wrap">{{ data.text }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ data: Object })
const open = ref(false)

function formatCount(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}
</script>
