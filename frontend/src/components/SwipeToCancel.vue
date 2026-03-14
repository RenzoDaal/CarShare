<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{ (e: 'cancel'): void }>();

const THRESHOLD = 0.35; // 35% of element width triggers action

const containerEl = ref<HTMLElement | null>(null);
const translateX = ref(0);
const isDragging = ref(false);
let startX = 0;

function onTouchStart(e: TouchEvent) {
  startX = e.touches.item(0)?.clientX ?? 0;
  isDragging.value = true;
}

function onTouchMove(e: TouchEvent) {
  if (!isDragging.value) return;
  const dx = (e.touches.item(0)?.clientX ?? startX) - startX;
  // Only allow left swipe (negative dx)
  if (dx >= 0) {
    translateX.value = 0;
    return;
  }
  translateX.value = Math.max(dx, -(containerEl.value?.offsetWidth ?? 300) * 0.6);
}

function onTouchEnd() {
  isDragging.value = false;
  const width = containerEl.value?.offsetWidth ?? 300;
  if (translateX.value < -(width * THRESHOLD)) {
    // Snap to fully revealed then emit
    translateX.value = -width;
    setTimeout(() => {
      translateX.value = 0;
      emit('cancel');
    }, 180);
  } else {
    translateX.value = 0;
  }
}

</script>

<template>
  <div ref="containerEl" class="relative overflow-hidden rounded-2xl"
    @touchstart.passive="onTouchStart"
    @touchmove.passive="onTouchMove"
    @touchend="onTouchEnd"
  >
    <!-- Danger action behind -->
    <div class="absolute inset-y-0 right-0 flex items-center justify-end pr-5 bg-red-500 dark:bg-red-600 rounded-2xl"
      :style="{ opacity: Math.min(1, -translateX / ((containerEl?.offsetWidth ?? 300) * THRESHOLD)) }"
    >
      <i class="pi pi-times text-white text-xl" />
    </div>

    <!-- Content layer -->
    <div
      :style="{
        transform: `translateX(${translateX}px)`,
        transition: isDragging ? 'none' : 'transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        pointerEvents: Math.abs(translateX) > 8 ? 'none' : undefined,
      }"
    >
      <slot />
    </div>
  </div>
</template>
