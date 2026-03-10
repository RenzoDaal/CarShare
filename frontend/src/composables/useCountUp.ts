import { ref, watch, type Ref } from 'vue'

export function useCountUp(target: Ref<number>, duration = 900) {
  const display = ref(0)

  watch(
    target,
    (to) => {
      const from = display.value
      const start = performance.now()
      const tick = (now: number) => {
        const p = Math.min((now - start) / duration, 1)
        const eased = 1 - Math.pow(1 - p, 3)
        display.value = from + (to - from) * eased
        if (p < 1) requestAnimationFrame(tick)
        else display.value = to
      }
      requestAnimationFrame(tick)
    },
    { immediate: true }
  )

  return display
}
