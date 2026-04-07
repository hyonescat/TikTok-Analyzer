<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
      <h2 class="text-lg font-bold text-white mb-5">Configure Analysis Run</h2>

      <div class="space-y-4">
        <label class="flex items-center justify-between">
          <span class="text-gray-300 text-sm">Favorites limit</span>
          <input v-model.number="config.favorites" type="number" min="1" max="500"
            class="w-24 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white text-right" />
        </label>

        <label class="flex items-center justify-between">
          <span class="text-gray-300 text-sm">Liked videos limit</span>
          <input v-model.number="config.liked" type="number" min="1" max="500"
            :disabled="config.favorites_only"
            class="w-24 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white text-right disabled:opacity-40" />
        </label>

        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="config.favorites_only" type="checkbox"
            class="w-4 h-4 accent-pink-500" />
          <span class="text-gray-300 text-sm">Favorites only</span>
        </label>

        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="config.dry_run" type="checkbox"
            class="w-4 h-4 accent-pink-500" />
          <span class="text-gray-300 text-sm">Dry run (collect list only)</span>
        </label>

        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="config.rebuild_output" type="checkbox"
            class="w-4 h-4 accent-pink-500" />
          <span class="text-gray-300 text-sm">Rebuild output from cache</span>
        </label>
      </div>

      <div class="flex gap-3 mt-6">
        <button @click="$emit('close')"
          class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg text-sm transition">
          Cancel
        </button>
        <button @click="$emit('run', config)"
          class="flex-1 bg-pink-600 hover:bg-pink-500 text-white py-2 rounded-lg text-sm font-medium transition">
          Start Run ▶
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
defineEmits(['close', 'run'])

const config = reactive({
  favorites: 50,
  liked: 50,
  favorites_only: false,
  dry_run: false,
  rebuild_output: false,
})
</script>
