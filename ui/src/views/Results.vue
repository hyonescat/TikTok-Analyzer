<template>
  <div class="max-w-5xl mx-auto space-y-4">
    <!-- Filters -->
    <div class="flex flex-wrap gap-3 bg-gray-900 border border-gray-700 rounded-lg p-4">
      <input
        v-model="search" placeholder="Search tools..."
        class="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm text-white flex-1 min-w-48"
      />
      <select v-model="filterCategory"
        class="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm text-white">
        <option value="">All categories</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
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
        <option v-for="author in authors" :key="author" :value="author">@{{ author }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-gray-500 text-sm text-center py-12">Loading results…</div>
    <div v-else-if="!tools.length" class="text-gray-500 text-sm text-center py-12">
      No results yet. Run an analysis first.
    </div>

    <!-- Tool rows -->
    <div v-else class="space-y-2">
      <div
        v-for="tool in filtered" :key="tool.tool"
        class="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 flex items-start justify-between gap-4"
      >
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-white font-medium">{{ tool.tool }}</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">{{ tool.category }}</span>
            <span class="text-xs text-gray-500">score: {{ tool.score }}</span>
          </div>
          <p class="text-gray-400 text-sm mt-1">{{ tool.description }}</p>
          <div class="flex flex-wrap gap-3 mt-1.5 text-xs text-gray-500">
            <span v-if="tool.install_command" class="font-mono bg-gray-800 px-2 py-0.5 rounded">
              {{ tool.install_command }}
            </span>
            <a v-if="tool.url" :href="tool.url" target="_blank"
              class="text-pink-400 hover:text-pink-300 underline">{{ tool.url }}</a>
          </div>
          <div class="text-xs text-gray-600 mt-1">
            Mentioned by: {{ uniqueAuthors(tool.sources) }}
          </div>
        </div>
        <div class="shrink-0 text-right">
          <span class="text-2xl font-bold text-pink-500">{{ tool.mention_count }}</span>
          <div class="text-gray-600 text-xs">mentions</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const tools = ref([])
const loading = ref(true)
const search = ref('')
const filterCategory = ref('')
const filterSource = ref('')
const filterAuthor = ref('')

const categories = computed(() => [...new Set(tools.value.map(t => t.category))].sort())

const authors = computed(() =>
  [...new Set(tools.value.flatMap(t => t.sources.map(s => s.author_username)))].sort()
)

const filtered = computed(() => tools.value.filter(tool => {
  if (search.value && !tool.tool.toLowerCase().includes(search.value.toLowerCase()) &&
      !tool.description.toLowerCase().includes(search.value.toLowerCase())) return false
  if (filterCategory.value && tool.category !== filterCategory.value) return false
  if (filterSource.value && !tool.sources.some(s => s.source === filterSource.value || s.source === 'both')) return false
  if (filterAuthor.value && !tool.sources.some(s => s.author_username === filterAuthor.value)) return false
  return true
}))

function uniqueAuthors(sources) {
  const authors = [...new Set(sources.map(s => '@' + s.author_username))].slice(0, 5)
  return authors.join(', ')
}

async function loadResults() {
  try {
    const res = await fetch('/api/results')
    if (res.ok) tools.value = await res.json()
  } catch {}
  loading.value = false
}

onMounted(loadResults)
</script>
