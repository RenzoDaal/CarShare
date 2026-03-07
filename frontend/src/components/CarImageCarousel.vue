<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import http from '@/api/http';

const props = defineProps<{
  carId: number;
  fallbackUrl?: string | null;
}>();

type CarImage = { id: number; url: string; order: number };

const images = ref<string[]>([]);
const currentIndex = ref(0);

onMounted(async () => {
  try {
    const { data } = await http.get<CarImage[]>(`/cars/${props.carId}/images`);
    images.value = data.map(i => i.url);
  } catch {
    // ignore
  }
  if (images.value.length === 0 && props.fallbackUrl) {
    images.value = [props.fallbackUrl];
  }
});

const currentImage = computed(() => images.value[currentIndex.value] ?? null);

function prev() {
  currentIndex.value = (currentIndex.value - 1 + images.value.length) % images.value.length;
}

function next() {
  currentIndex.value = (currentIndex.value + 1) % images.value.length;
}
</script>

<template>
  <div class="relative w-full h-full overflow-hidden bg-surface-900">
    <img v-if="currentImage" :src="currentImage" class="w-full h-full object-cover block" />

    <template v-if="images.length > 1">
      <button
        class="absolute left-1 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 transition-colors"
        @click.stop="prev"
      >
        <i class="pi pi-chevron-left text-xs" />
      </button>
      <button
        class="absolute right-1 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 transition-colors"
        @click.stop="next"
      >
        <i class="pi pi-chevron-right text-xs" />
      </button>

      <div class="absolute bottom-2 left-0 right-0 flex justify-center gap-1 pointer-events-none">
        <span
          v-for="(_, i) in images"
          :key="i"
          class="w-1.5 h-1.5 rounded-full transition-colors"
          :class="i === currentIndex ? 'bg-white' : 'bg-white/50'"
        />
      </div>
    </template>
  </div>
</template>
