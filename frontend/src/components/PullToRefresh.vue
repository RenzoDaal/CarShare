<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{ refresh: [] }>();

const pulling = ref(false);
const refreshing = ref(false);
const pullY = ref(0);
const THRESHOLD = 64;

let startY = 0;
let scrollEl: Element | null = null;

function getScrollParent(el: Element | null): Element | null {
  if (!el) return null;
  const style = window.getComputedStyle(el);
  if (['auto', 'scroll'].includes(style.overflowY)) return el;
  return getScrollParent(el.parentElement);
}

function onTouchStart(e: TouchEvent) {
  if (refreshing.value) return;
  startY = e.touches[0]!.clientY;
  scrollEl = getScrollParent((e.target as Element)?.parentElement);
}

function onTouchMove(e: TouchEvent) {
  if (refreshing.value) return;
  const dy = e.touches[0]!.clientY - startY;
  const scrollTop = scrollEl ? (scrollEl as HTMLElement).scrollTop : window.scrollY;
  if (dy > 0 && scrollTop <= 0) {
    pulling.value = true;
    pullY.value = Math.min(dy * 0.45, THRESHOLD + 20);
    e.preventDefault();
  } else {
    pulling.value = false;
    pullY.value = 0;
  }
}

function onTouchEnd() {
  if (!pulling.value) return;
  if (pullY.value >= THRESHOLD) {
    refreshing.value = true;
    emit('refresh');
  }
  pulling.value = false;
  pullY.value = 0;
}

function done() {
  refreshing.value = false;
}

defineExpose({ done });
</script>

<template>
  <div
    class="relative"
    @touchstart.passive="onTouchStart"
    @touchmove="onTouchMove"
    @touchend.passive="onTouchEnd"
  >
    <!-- Pull indicator -->
    <div
      class="absolute left-1/2 -translate-x-1/2 flex items-center justify-center pointer-events-none z-10 transition-opacity duration-150"
      :style="{ top: `${pullY - 38}px`, opacity: pulling || refreshing ? 1 : 0 }"
    >
      <div class="w-8 h-8 rounded-full bg-white dark:bg-zinc-800 shadow-md flex items-center justify-center">
        <i
          v-if="!refreshing"
          class="pi pi-arrow-down text-primary text-sm transition-transform duration-150"
          :style="{ transform: `rotate(${pullY >= THRESHOLD ? 180 : 0}deg)` }"
        />
        <i v-else class="pi pi-spin pi-spinner text-primary text-sm" />
      </div>
    </div>

    <div
      :style="{
        transform: refreshing
          ? 'translateY(40px)'
          : pulling
            ? `translateY(${pullY * 0.3}px)`
            : 'none',
        transition: pulling ? 'none' : 'transform 0.2s ease',
      }"
    >
      <slot />
    </div>
  </div>
</template>
