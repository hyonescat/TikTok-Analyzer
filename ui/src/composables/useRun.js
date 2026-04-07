import { ref } from 'vue'

export function useRun() {
  const status = ref('idle')

  async function startRun(config) {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    if (!res.ok) throw new Error(await res.text())
    status.value = 'running'
  }

  async function cancelRun() {
    await fetch('/api/run/cancel', { method: 'POST' })
    status.value = 'idle'
  }

  return { status, startRun, cancelRun }
}
