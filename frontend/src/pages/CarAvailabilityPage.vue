<script setup lang="ts">
import Card from 'primevue/card';
import Button from 'primevue/button';
import { ref, computed, onMounted } from 'vue';
import http from '@/api/http';
import type { Car } from '@/stores/cars';
import CarImageCarousel from '@/components/CarImageCarousel.vue';

type DateRange = { start: string; end: string };

// --- Car grid ---
const cars = ref<Car[]>([]);
const carsLoading = ref(false);

onMounted(async () => {
  carsLoading.value = true;
  try {
    const res = await http.get<Car[]>('/cars');
    cars.value = res.data;
  } finally {
    carsLoading.value = false;
  }
});

// --- Calendar view ---
const selectedCar = ref<Car | null>(null);
const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth()); // 0-based
const unavailableRanges = ref<DateRange[]>([]);
const calendarLoading = ref(false);

const monthName = computed(() =>
  new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric' })
    .format(new Date(currentYear.value, currentMonth.value, 1))
);

const calendarDays = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value, 1);
  const daysInMonth = new Date(currentYear.value, currentMonth.value + 1, 0).getDate();
  // Sunday = 0, fill leading blanks
  const leadingBlanks = firstDay.getDay();
  const days: (Date | null)[] = Array(leadingBlanks).fill(null);
  for (let d = 1; d <= daysInMonth; d++) {
    days.push(new Date(currentYear.value, currentMonth.value, d));
  }
  return days;
});

const toDateStr = (d: Date) => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

const isUnavailable = (day: Date) => {
  const ds = toDateStr(day);
  return unavailableRanges.value.some(r => ds >= r.start && ds <= r.end);
};

const isToday = (day: Date) => toDateStr(day) === toDateStr(new Date());

const fetchCalendar = async () => {
  if (!selectedCar.value) return;
  calendarLoading.value = true;
  try {
    const res = await http.get<DateRange[]>(`/cars/${selectedCar.value.id}/calendar`, {
      params: { year: currentYear.value, month: currentMonth.value + 1 },
    });
    unavailableRanges.value = res.data;
  } catch {
    unavailableRanges.value = [];
  } finally {
    calendarLoading.value = false;
  }
};

const selectCar = async (car: Car) => {
  selectedCar.value = car;
  currentYear.value = new Date().getFullYear();
  currentMonth.value = new Date().getMonth();
  await fetchCalendar();
};

const prevMonth = async () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11;
    currentYear.value--;
  } else {
    currentMonth.value--;
  }
  await fetchCalendar();
};

const nextMonth = async () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0;
    currentYear.value++;
  } else {
    currentMonth.value++;
  }
  await fetchCalendar();
};
</script>

<template>
  <div class="flex flex-col w-full">

    <!-- Car grid -->
    <template v-if="!selectedCar">
      <div class="w-full max-w-[98%] mx-auto mt-6 px-2">
        <h1 class="text-xl font-semibold mb-4">Car Availability</h1>
        <p class="text-sm text-surface-500 mb-6">Select a car to see its availability calendar.</p>
        <p v-if="carsLoading" class="text-sm text-surface-500">Loading cars…</p>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card v-for="car in cars" :key="car.id"
            class="overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all"
            @click="selectCar(car)">
            <template #header>
              <div class="h-48 w-full">
                <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
              </div>
            </template>
            <template #title>{{ car.name }}</template>
            <template #content>
              <span class="text-sm text-surface-500">{{ car.price_per_km }} € / km</span>
            </template>
          </Card>
        </div>
      </div>
    </template>

    <!-- Calendar view -->
    <template v-else>
      <div class="w-full max-w-2xl mx-auto mt-6 px-2">
        <div class="flex items-center gap-3 mb-6">
          <Button icon="pi pi-arrow-left" severity="secondary" outlined rounded size="small"
            @click="selectedCar = null" />
          <div>
            <h1 class="text-xl font-semibold">{{ selectedCar.name }}</h1>
            <p class="text-sm text-surface-500">{{ selectedCar.price_per_km }} € / km</p>
          </div>
        </div>

        <Card>
          <template #content>
            <!-- Month navigation -->
            <div class="flex items-center justify-between mb-4">
              <Button icon="pi pi-chevron-left" severity="secondary" text rounded @click="prevMonth" />
              <span class="font-semibold text-base">{{ monthName }}</span>
              <Button icon="pi pi-chevron-right" severity="secondary" text rounded @click="nextMonth" />
            </div>

            <!-- Day-of-week headers -->
            <div class="grid grid-cols-7 mb-1">
              <div v-for="day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="day"
                class="text-center text-xs font-medium text-surface-400 py-1">
                {{ day }}
              </div>
            </div>

            <!-- Calendar grid -->
            <div v-if="calendarLoading" class="text-center py-8 text-sm text-surface-500">Loading…</div>
            <div v-else class="grid grid-cols-7 gap-1">
              <div v-for="(day, i) in calendarDays" :key="i" class="aspect-square flex items-center justify-center rounded-lg text-sm"
                :class="{
                  'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 font-medium': day && isUnavailable(day),
                  'ring-2 ring-primary font-semibold': day && isToday(day) && !isUnavailable(day),
                  'text-surface-800 dark:text-surface-100': day && !isUnavailable(day),
                  'text-surface-300': !day,
                }">
                {{ day ? day.getDate() : '' }}
              </div>
            </div>

            <!-- Legend -->
            <div class="flex items-center gap-4 mt-4 text-xs text-surface-500">
              <div class="flex items-center gap-1">
                <div class="w-4 h-4 rounded bg-red-100 dark:bg-red-900/40"></div>
                <span>Unavailable</span>
              </div>
              <div class="flex items-center gap-1">
                <div class="w-4 h-4 rounded border-2 border-primary"></div>
                <span>Today</span>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </template>

  </div>
</template>
