<template>
  <div class="bg-gray-900 border border-pink-900/40 rounded-lg overflow-hidden">
    <div class="flex items-center justify-between px-4 py-2 bg-pink-950/30">
      <span class="text-pink-400 text-xs font-medium">Analysis: {{ data.video_id }}</span>
    </div>
    <div class="grid grid-cols-2 gap-px bg-gray-700 text-sm">
      <template v-for="field in fields" :key="field.key">
        <div v-if="data[field.key]?.length" class="bg-gray-900 px-4 py-2">
          <div class="text-gray-500 text-xs mb-1">{{ field.label }}</div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="item in data[field.key]" :key="item"
              class="bg-gray-800 text-gray-200 text-xs px-2 py-0.5 rounded"
            >{{ item }}</span>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({ data: Object })

const fields = [
  { key: 'technologies', label: 'Technologies' },
  { key: 'extensions', label: 'Extensions' },
  { key: 'modules', label: 'Modules' },
  { key: 'ai_components', label: 'AI Components' },
  { key: 'ai_names', label: 'AI Names' },
]
</script>
