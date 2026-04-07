<template>
  <div class="max-w-5xl mx-auto space-y-4">
    <!-- Filters -->
    <div class="flex flex-wrap gap-3 bg-gray-900 border border-gray-700 rounded-lg p-4">
      <input v-model="search" placeholder="Search by caption or author..."
        class="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm text-white flex-1 min-w-48" />
      <select v-model="filterSource"
        class="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm text-white">
        <option value="">All sources</option>
        <option value="favorites">Favorites</option>
        <option value="liked">Liked</option>
        <option value="both">Both</option>
      </select>
      <select v-model="filterAuthor"
        class="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm text-white">
        <option value="">All authors</option>
        <option v-for="a in authors" :key="a" :value="a">@{{ a }}</option>
      </select>
    </div>

    <div class="text-xs text-gray-500 px-1">{{ filtered.length }} videos analyzed</div>

    <div v-for="rec in filtered" :key="rec.video_id"
      class="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      <div class="flex items-start justify-between px-4 py-3 gap-4">
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs px-2 py-0.5 rounded-full text-xs font-medium"
              :class="{
                'bg-pink-950 text-pink-400': rec.source === 'favorites',
                'bg-blue-950 text-blue-400': rec.source === 'liked',
                'bg-purple-950 text-purple-400': rec.source === 'both',
              }">{{ rec.source }}</span>
            <span class="text-gray-200 text-sm truncate">{{ rec.caption || rec.video_id }}</span>
          </div>
          <div class="flex gap-4 mt-1.5 text-xs text-gray-500">
            <span>@{{ rec.author_username }}</span>
            <span>❤️ {{ formatCount(rec.like_count) }}</span>
            <span>{{ rec.tool_count }} tools found</span>
            <span>{{ rec.analyzed_date?.slice(0, 10) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button @click="toggleExpand(rec.video_id)"
            class="text-xs text-gray-500 hover:text-white transition px-2 py-1 bg-gray-800 rounded">
            {{ expanded === rec.video_id ? 'Hide' : 'Details' }}
          </button>
          <button @click="reprocess(rec.video_id)"
            class="text-xs text-gray-500 hover:text-pink-400 transition px-2 py-1 bg-gray-800 rounded">
            Reprocess
          </button>
        </div>
      </div>

      <div v-if="expanded === rec.video_id && analyses[rec.video_id]"
        class="border-t border-gray-700 px-4 py-3">
        <VideoAnalysisCard :data="analyses[rec.video_id]" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VideoAnalysisCard from '../components/VideoAnalysisCard.vue'

const records = ref([])
const analyses = ref({})
const search = ref('')
const filterSource = ref('')
const filterAuthor = ref('')
const expanded = ref(null)

const authors = computed(() => [...new Set(records.value.map(r => r.author_username))].sort())

const filtered = computed(() => records.value.filter(r => {
  if (filterSource.value && r.source !== filterSource.value) return false
  if (filterAuthor.value && r.author_username !== filterAuthor.value) return false
  if (search.value) {
    const q = search.value.toLowerCase()
    if (!r.caption?.toLowerCase().includes(q) && !r.author_username?.toLowerCase().includes(q)) return false
  }
  return true
}))

function formatCount(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

async function toggleExpand(videoId) {
  if (expanded.value === videoId) {
    expanded.value = null
    return
  }
  expanded.value = videoId
  if (!analyses.value[videoId]) {
    try {
      const res = await fetch(`/api/analysis/${videoId}`)
      if (res.ok) analyses.value[videoId] = await res.json()
    } catch {}
  }
}

async function reprocess(videoId) {
  await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reprocess: videoId }),
  })
}

async function loadHistory() {
  try {
    const res = await fetch('/api/history')
    if (res.ok) records.value = await res.json()
  } catch {}
}

onMounted(loadHistory)
</script>
