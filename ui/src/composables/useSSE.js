import { ref, onUnmounted } from 'vue'

export function useSSE() {
  const events = ref([])
  const connected = ref(false)
  let source = null

  function connect(onTranscript, onAnalysis, onDone) {
    if (source) source.close()
    events.value = []
    source = new EventSource('/api/progress')
    connected.value = true

    source.addEventListener('log', (e) => {
      const data = JSON.parse(e.data)
      events.value.push({ type: 'log', text: data })
    })

    source.addEventListener('transcript', (e) => {
      const data = JSON.parse(e.data)
      events.value.push({ type: 'transcript', data })
      onTranscript?.(data)
    })

    source.addEventListener('analysis', (e) => {
      const data = JSON.parse(e.data)
      events.value.push({ type: 'analysis', data })
      onAnalysis?.(data)
    })

    source.addEventListener('done', (e) => {
      const data = JSON.parse(e.data)
      events.value.push({ type: 'done', data })
      connected.value = false
      source.close()
      onDone?.(data)
    })

    source.addEventListener('error', (e) => {
      connected.value = false
      source?.close()
    })
  }

  function disconnect() {
    source?.close()
    connected.value = false
  }

  onUnmounted(disconnect)

  return { events, connected, connect, disconnect }
}
