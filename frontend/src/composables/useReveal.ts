import { ref, onMounted, onUnmounted } from 'vue'

export function useReveal(threshold = 0.08) {
  const el = ref<HTMLElement | null>(null)
  const visible = ref(false)
  let obs: IntersectionObserver | null = null

  onMounted(() => {
    obs = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry?.isIntersecting) {
          visible.value = true
          obs?.disconnect()
        }
      },
      { threshold }
    )
    if (el.value) obs.observe(el.value)
  })

  onUnmounted(() => obs?.disconnect())

  return { el, visible }
}
