<script setup lang="ts">
import Card from 'primevue/card';
import Button from 'primevue/button';
import { ref, computed, onMounted } from 'vue';
import http from '@/api/http';
import type { Car } from '@/stores/cars';
import CarImageCarousel from '@/components/CarImageCarousel.vue';
import { useI18n } from 'vue-i18n';

const { locale } = useI18n();

type DateRange = { start: string; end: string; type: 'booking' | 'block' };
type DayBusySlot = { start: string; end: string; type: 'booking' | 'block' };
type DaySegment = { startMinutes: number; endMinutes: number; type: 'free' | 'booking' | 'block' };

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
  new Intl.DateTimeFormat(locale.value === 'nl' ? 'nl-NL' : 'en-GB', { month: 'long', year: 'numeric' })
    .format(new Date(currentYear.value, currentMonth.value, 1))
);

const calendarDays = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value, 1);
  const daysInMonth = new Date(currentYear.value, currentMonth.value + 1, 0).getDate();
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

// Returns the dominant type for a day: 'booking' takes priority over 'block'
const dayType = (day: Date): 'booking' | 'block' | null => {
  const ds = toDateStr(day);
  const matches = unavailableRanges.value.filter(r => ds >= r.start && ds <= r.end);
  if (matches.some(r => r.type === 'booking')) return 'booking';
  if (matches.some(r => r.type === 'block')) return 'block';
  return null;
};

const isUnavailable = (day: Date) => dayType(day) !== null;

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
  selectedDay.value = null;
  await fetchCalendar();
};

const prevMonth = async () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11;
    currentYear.value--;
  } else {
    currentMonth.value--;
  }
  selectedDay.value = null;
  await fetchCalendar();
};

const nextMonth = async () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0;
    currentYear.value++;
  } else {
    currentMonth.value++;
  }
  selectedDay.value = null;
  await fetchCalendar();
};

// --- Day view ---
const selectedDay = ref<Date | null>(null);
const dayBusySlots = ref<DayBusySlot[]>([]);
const dayLoading = ref(false);

const toMinutes = (isoStr: string): number => {
  const d = new Date(isoStr);
  return d.getHours() * 60 + d.getMinutes();
};

const daySegments = computed((): DaySegment[] => {
  if (!dayBusySlots.value.length) return [];
  const busy = dayBusySlots.value
    .map(s => ({ start: toMinutes(s.start), end: toMinutes(s.end) === 0 ? 1440 : toMinutes(s.end), type: s.type as 'booking' | 'block' }))
    .sort((a, b) => a.start - b.start);

  const segments: DaySegment[] = [];
  let cursor = 0;

  for (const slot of busy) {
    if (slot.start > cursor) {
      segments.push({ startMinutes: cursor, endMinutes: slot.start, type: 'free' });
    }
    segments.push({ startMinutes: slot.start, endMinutes: slot.end, type: slot.type });
    cursor = Math.max(cursor, slot.end);
  }
  if (cursor < 1440) {
    segments.push({ startMinutes: cursor, endMinutes: 1440, type: 'free' });
  }
  return segments;
});

const formatMinutes = (m: number): string => {
  const h = Math.floor(m / 60) % 24;
  const min = m % 60;
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
};

const dayTitle = computed(() => {
  if (!selectedDay.value) return '';
  return new Intl.DateTimeFormat(locale.value === 'nl' ? 'nl-NL' : 'en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(selectedDay.value);
});

const selectDay = async (day: Date) => {
  if (selectedDay.value && toDateStr(selectedDay.value) === toDateStr(day)) {
    selectedDay.value = null;
    return;
  }
  selectedDay.value = day;
  if (!selectedCar.value) return;
  dayLoading.value = true;
  try {
    const res = await http.get<DayBusySlot[]>(`/cars/${selectedCar.value.id}/day`, {
      params: { date: toDateStr(day) },
    });
    dayBusySlots.value = res.data;
  } catch {
    dayBusySlots.value = [];
  } finally {
    dayLoading.value = false;
  }
};
</script>

<template>
  <div class="flex flex-col w-full px-4 py-6">

    <!-- Car grid -->
    <template v-if="!selectedCar">
      <div class="w-full max-w-6xl mx-auto">
        <h1 class="text-xl font-semibold mb-4">{{ $t('availability_title') }}</h1>
        <p class="text-sm text-surface-500 mb-6">{{ $t('availability_select_car') }}</p>
        <p v-if="carsLoading" class="text-sm text-surface-500">{{ $t('availability_loading_cars') }}</p>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="(car, index) in cars" :key="car.id"
            class="relative h-80 rounded-xl overflow-hidden cursor-pointer shadow hover:-translate-y-1.5 hover:shadow-xl transition-all duration-300 card-animate border border-surface-200 dark:border-surface-700"
            :style="{ animationDelay: `${index * 70}ms` }"
            @click="selectCar(car)">
            <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
            <div class="absolute inset-0 bg-gradient-to-t from-black/65 via-black/15 to-transparent pointer-events-none" />
            <div class="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
              <p class="text-white font-semibold leading-tight">{{ car.name }}</p>
              <p class="text-white/75 text-sm mt-0.5">{{ car.price_per_km }} € / km</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Calendar / Day detail view -->
    <template v-else>
      <div class="w-full max-w-2xl mx-auto">

        <!-- Header: always visible, back button changes target depending on view -->
        <div class="flex items-center gap-3 mb-6">
          <Button icon="pi pi-arrow-left" severity="secondary" outlined rounded size="small"
            @click="selectedDay ? selectedDay = null : (selectedCar = null)" />
          <div>
            <h1 class="text-xl font-semibold">{{ selectedDay ? dayTitle : selectedCar.name }}</h1>
            <p class="text-sm text-surface-500">{{ selectedDay ? selectedCar.name : `${selectedCar.price_per_km} € / km` }}</p>
          </div>
        </div>

        <!-- Calendar ↔ Day detail: mutually exclusive with transition -->
        <Transition name="drill" mode="out-in">

          <!-- Calendar view -->
          <Card v-if="!selectedDay" key="calendar">
            <template #content>
              <!-- Month navigation -->
              <div class="flex items-center justify-between mb-4">
                <Button icon="pi pi-chevron-left" severity="secondary" text rounded @click="prevMonth" />
                <span class="font-semibold text-base">{{ monthName }}</span>
                <Button icon="pi pi-chevron-right" severity="secondary" text rounded @click="nextMonth" />
              </div>

              <!-- Day-of-week headers -->
              <div class="grid grid-cols-7 mb-1">
                <div v-for="day in [$t('availability_day_sun'), $t('availability_day_mon'), $t('availability_day_tue'), $t('availability_day_wed'), $t('availability_day_thu'), $t('availability_day_fri'), $t('availability_day_sat')]" :key="day"
                  class="text-center text-xs font-medium text-surface-400 py-1">
                  {{ day }}
                </div>
              </div>

              <!-- Calendar grid -->
              <div v-if="calendarLoading" class="text-center py-8 text-sm text-surface-500">{{ $t('availability_loading_calendar') }}</div>
              <div v-else class="grid grid-cols-7 gap-1">
                <div v-for="(day, i) in calendarDays" :key="i"
                  class="aspect-square flex items-center justify-center rounded-lg text-sm transition-all"
                  :class="{
                    'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 cursor-pointer hover:bg-red-200 dark:hover:bg-red-800/50': day && dayType(day) === 'booking',
                    'bg-orange-100 dark:bg-orange-900/40 text-orange-600 dark:text-orange-400 cursor-pointer hover:bg-orange-200 dark:hover:bg-orange-800/50': day && dayType(day) === 'block',
                    'ring-2 ring-primary font-semibold': day && isToday(day) && !isUnavailable(day),
                    'text-surface-800 dark:text-surface-100 cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-700': day && !isUnavailable(day),
                    'text-surface-300': !day,
                  }"
                  @click="day && selectDay(day)">
                  <span :class="{ 'line-through opacity-60': day && isUnavailable(day) }">{{ day ? day.getDate() : '' }}</span>
                </div>
              </div>

              <!-- Legend -->
              <div class="flex items-center gap-4 mt-4 flex-wrap text-xs text-surface-500">
                <div class="flex items-center gap-1.5">
                  <div class="w-4 h-4 rounded bg-red-100 dark:bg-red-900/40"></div>
                  <span>{{ $t('availability_day_booked') }}</span>
                </div>
                <div class="flex items-center gap-1.5">
                  <div class="w-4 h-4 rounded bg-orange-100 dark:bg-orange-900/40"></div>
                  <span>{{ $t('availability_day_blocked') }}</span>
                </div>
                <div class="flex items-center gap-1.5">
                  <div class="w-4 h-4 rounded border-2 border-primary"></div>
                  <span>{{ $t('availability_today') }}</span>
                </div>
              </div>
              <p class="text-xs text-surface-400 italic mt-2">{{ $t('availability_click_day_hint') }}</p>
            </template>
          </Card>

          <!-- Day detail view -->
          <Card v-else key="day-detail">
            <template #content>
              <div v-if="dayLoading" class="text-sm text-surface-500 py-8 text-center">
                {{ $t('availability_loading_calendar') }}
              </div>

              <div v-else-if="!dayBusySlots.length" class="text-sm text-green-600 dark:text-green-400 py-4">
                {{ $t('availability_day_fully_free') }}
              </div>

              <div v-else class="flex flex-col rounded-lg overflow-hidden border border-surface-200 dark:border-surface-700" style="height: min(420px, 55vh)">
                <div
                  v-for="(seg, i) in daySegments" :key="i"
                  class="flex items-center px-3 gap-3 text-xs overflow-hidden transition-colors"
                  :style="{ flexGrow: seg.endMinutes - seg.startMinutes, minHeight: '20px' }"
                  :class="{
                    'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400': seg.type === 'free',
                    'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300': seg.type === 'booking',
                    'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300': seg.type === 'block',
                  }">
                  <span class="font-semibold shrink-0">{{ formatMinutes(seg.startMinutes) }} – {{ formatMinutes(seg.endMinutes) }}</span>
                  <span class="truncate">
                    {{ seg.type === 'free' ? $t('availability_day_free') : seg.type === 'booking' ? $t('availability_day_booked') : $t('availability_day_blocked') }}
                  </span>
                </div>
              </div>

              <!-- Day legend -->
              <div v-if="dayBusySlots.length" class="flex items-center gap-4 mt-3 text-xs text-surface-500">
                <div class="flex items-center gap-1">
                  <div class="w-3 h-3 rounded bg-green-100 dark:bg-green-900/40"></div>
                  <span>{{ $t('availability_day_free') }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <div class="w-3 h-3 rounded bg-red-100 dark:bg-red-900/40"></div>
                  <span>{{ $t('availability_day_booked') }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <div class="w-3 h-3 rounded bg-orange-100 dark:bg-orange-900/40"></div>
                  <span>{{ $t('availability_day_blocked') }}</span>
                </div>
              </div>
            </template>
          </Card>

        </Transition>

      </div>
    </template>

  </div>
</template>

<style scoped>
.card-animate {
  animation: cardFadeIn 0.35s ease forwards;
  opacity: 0;
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.drill-enter-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.drill-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.drill-enter-from {
  opacity: 0;
  transform: translateX(16px);
}
.drill-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
