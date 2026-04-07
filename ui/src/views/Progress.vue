<template>
  <div class="space-y-2 max-w-4xl mx-auto">
    <div v-if="events.length === 0" class="text-gray-500 text-sm text-center py-12">
      No active run. Click "Run ▶" to start an analysis.
    </div>

    <template v-for="(event, i) in events" :key="i">
      <div v-if="event.type === 'log'" class="text-gray-400 text-xs font-mono py-0.5 px-2">
        › {{ event.text }}
      </div>
      <TranscriptCard v-else-if="event.type === 'transcript'" :data="event.data" />
      <VideoAnalysisCard v-else-if="event.type === 'analysis'" :data="event.data" />
      <div v-else-if="event.type === 'done'"
        class="bg-green-950 border border-green-800 rounded-lg px-4 py-3 text-green-300 text-sm">
        ✓ Done — {{ event.data.videos }} videos processed, {{ event.data.tools }} tools found
        ({{ event.data.duration_seconds }}s)
      </div>
    </template>

    <div ref="bottom" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useSSE } from '../composables/useSSE.js'
import TranscriptCard from '../components/TranscriptCard.vue'
import VideoAnalysisCard from '../components/VideoAnalysisCard.vue'

const { events, connect } = useSSE()
const bottom = ref(null)

onMounted(() => {
  connect()
})

watch(events, () => {
  setTimeout(() => bottom.value?.scrollIntoView({ behavior: 'smooth' }), 50)
}, { deep: true })
</script>
