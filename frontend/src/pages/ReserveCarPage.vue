<script setup lang="ts">
import Card from 'primevue/card';
import Textarea from 'primevue/textarea';
import DatePicker from 'primevue/datepicker';
import Button from 'primevue/button';
import AutoComplete from 'primevue/autocomplete';
import CarImageCarousel from '@/components/CarImageCarousel.vue';
import Step from 'primevue/step';
import Stepper from 'primevue/stepper';
import StepList from 'primevue/steplist';
import RouteMap from '@/components/RouteMap.vue';

import { ref, computed, watch, onMounted, nextTick } from 'vue';
import type { Car } from '@/stores/cars';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

import http from '@/api/http';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const bookingError = ref<string | null>(null);
const bookingCompleted = ref(false);
const bookingSubmitting = ref(false);

// Step navigation
const activeStep = ref(1);
const stepDirection = ref<'forward' | 'back'>('forward');

const goForward = (step: number) => {
  stepDirection.value = 'forward';
  activeStep.value = step;
};

const goBack = (step: number) => {
  stepDirection.value = 'back';
  activeStep.value = step;
};

// Animate the newly visible step content via a watcher instead of <Transition>,
// which avoids mode="out-in" timing issues with synchronous done() calls.
const stepContentEl = ref<HTMLElement | null>(null);

watch(activeStep, async () => {
  await nextTick();
  const child = stepContentEl.value?.firstElementChild as HTMLElement | null;
  if (!child) return;
  const fromX = stepDirection.value === 'forward' ? 48 : -48;
  child.animate(
    [
      { opacity: '0', transform: `translateX(${fromX}px)` },
      { opacity: '1', transform: 'translateX(0)' },
    ],
    { duration: 420, easing: 'ease' },
  );
});

// Step 1: Dates & Times
const start = ref<Date | null>(null);
const end = ref<Date | null>(null);
const loadingCars = ref(false);
const datesError = ref<string | null>(null);

const canGoNextFromDates = computed(() => {
  if (!start.value || !end.value) return false;
  return end.value > start.value;
});

const handleDatesNext = async () => {
  if (!canGoNextFromDates.value) {
    datesError.value = t('reserve_error_dates');
    return;
  }
  await loadAvailableCars();
  if (!datesError.value) goForward(2);
};

// Step 2: available cars
const availableCars = ref<Car[]>([]);
const allCars = ref<Car[]>([]);
const selectedCar = ref<Car | null>(null);

const unavailableCars = computed(() => {
  const availableIds = new Set(availableCars.value.map(c => c.id));
  return allCars.value.filter(c => !availableIds.has(c.id));
});

const waitlistJoined = ref<Set<number>>(new Set());
const waitlistLoading = ref<Set<number>>(new Set());

const joinWaitlist = async (car: Car) => {
  if (!start.value || !end.value) return;
  waitlistLoading.value = new Set([...waitlistLoading.value, car.id]);
  try {
    await http.post('/waitlist', {
      car_id: car.id,
      start_datetime: start.value.toISOString(),
      end_datetime: end.value.toISOString(),
    });
    waitlistJoined.value = new Set([...waitlistJoined.value, car.id]);
  } catch {
    waitlistJoined.value = new Set([...waitlistJoined.value, car.id]);
  } finally {
    waitlistLoading.value = new Set([...waitlistLoading.value].filter(id => id !== car.id));
  }
};

const handleSelectCar = (car: Car) => {
  selectedCar.value = car;
  bookingCompleted.value = false;
  bookingError.value = null;
  goForward(3);
};

// Step 3: route & distance
const stops = ref<string[]>(['', '']);
let stopKeyCounter = 0;
const stopKeys = ref<number[]>([stopKeyCounter++, stopKeyCounter++]);
const activeStopIndex = ref(-1);
const locationSuggestions = ref<string[]>([]);
const stopAutoCompleteRefs = ref<any[]>([]);

const setStopRef = (el: unknown, index: number) => {
  if (el) stopAutoCompleteRefs.value[index] = el;
};

const getStopInput = (index: number): HTMLInputElement | null =>
  stopAutoCompleteRefs.value[index]?.$el?.querySelector('input') ?? null;

const onStopPointerDown = (index: number) => {
  stopAutoCompleteRefs.value.forEach((_, i) => {
    const input = getStopInput(i);
    if (input) {
      input.readOnly = i !== index;
      input.autocomplete = i === index ? 'street-address' : 'new-password';
    }
  });
};

const onStopFocus = (index: number) => { activeStopIndex.value = index; };

const onStopBlur = (index: number) => {
  setTimeout(() => {
    if (activeStopIndex.value !== index) return;
    activeStopIndex.value = -1;
    locationSuggestions.value = [];
    stopAutoCompleteRefs.value.forEach((_, i) => {
      const input = getStopInput(i);
      if (input) { input.readOnly = false; input.autocomplete = 'new-password'; }
    });
  }, 200);
};

const userLocation = ref<{ lat: number; lon: number } | null>(null);

onMounted(() => {
  navigator.geolocation?.getCurrentPosition(
    (pos) => { userLocation.value = { lat: pos.coords.latitude, lon: pos.coords.longitude }; },
    () => { },
  );
});

const distanceKm = ref<number | null>(null);
const routeEstimating = ref(false);
const routeError = ref<string | null>(null);
const routeCoordinates = ref<[number, number][]>([]);

const trimmedStops = computed(() => stops.value.map(s => s.trim()).filter(Boolean));

const estimatedPrice = computed(() => {
  if (!selectedCar.value || distanceKm.value == null) return null;
  return distanceKm.value * selectedCar.value.price_per_km;
});

const canGoNextFromRoute = computed(() =>
  trimmedStops.value.length >= 2 && distanceKm.value != null && !routeEstimating.value
);

watch(stops, () => {
  distanceKm.value = null;
  routeError.value = null;
  routeCoordinates.value = [];
}, { deep: true });

const addStop = () => {
  const insertAt = stops.value.length - 1;
  stops.value.splice(insertAt, 0, '');
  stopKeys.value.splice(insertAt, 0, stopKeyCounter++);
};

const removeStop = (index: number) => {
  if (stops.value.length <= 2) return;
  stops.value.splice(index, 1);
  stopKeys.value.splice(index, 1);
};

const searchLocations = async (event: { query: string }) => {
  const query = (event.query || '').trim();
  if (!query || query.length < 3) { locationSuggestions.value = []; return; }

  try {
    const photonParams = new URLSearchParams({ q: query, limit: '5' });
    if (userLocation.value) {
      photonParams.set('lat', String(userLocation.value.lat));
      photonParams.set('lon', String(userLocation.value.lon));
    }
    const photonRes = await fetch(`https://photon.komoot.io/api/?${photonParams}`);
    console.log('[Photon] status:', photonRes.status);
    if (photonRes.ok) {
      const data = await photonRes.json();
      console.log('[Photon] features:', data.features?.length, data.features?.[0]);
      const seen = new Set<string>();
      const labels: string[] = (data.features ?? []).map((f: any) => {
        const p = f.properties ?? {};
        const street = p.street ? `${p.street}${p.housenumber ? ' ' + p.housenumber : ''}` : null;
        return [p.name, street, p.city].filter(Boolean).join(', ');
      }).filter((label: string) => {
        if (!label || seen.has(label)) return false;
        seen.add(label);
        return true;
      });
      console.log('[Photon] labels:', labels);
      if (labels.length) { locationSuggestions.value = labels; return; }
    }
  } catch (e) { console.error('[Photon] fetch error:', e); }

  try {
    const res = await http.get<string[]>('/locations/suggest', {
      params: {
        query,
        ...(userLocation.value && { focus_lat: userLocation.value.lat, focus_lon: userLocation.value.lon }),
      }
    });
    locationSuggestions.value = res.data;
  } catch (err) {
    console.error(err);
    locationSuggestions.value = [];
  }
};

const estimateRoute = async () => {
  routeError.value = null;
  distanceKm.value = null;
  routeCoordinates.value = [];

  const payloadStops = trimmedStops.value;
  if (payloadStops.length < 2) { routeError.value = t('reserve_error_route'); return; }

  routeEstimating.value = true;
  try {
    const res = await http.post('/routes/estimate', { stops: payloadStops });
    distanceKm.value = res.data.distance_km;
    const backendCoords = (res.data.coordinates || []) as [number, number][];
    routeCoordinates.value = backendCoords.map(([lon, lat]) => [lat, lon]);
  } catch (err: any) {
    console.error(err);
    routeError.value = err?.response?.data?.detail ?? t('reserve_error_route_estimate');
  } finally {
    routeEstimating.value = false;
  }
};

// Step 4: confirmation
const fullName = ref(auth.user?.full_name ?? '');
const email = ref(auth.user?.email ?? '');
const bookingNotes = ref('');

const resetFlow = () => {
  start.value = null;
  end.value = null;
  datesError.value = null;
  availableCars.value = [];
  selectedCar.value = null;
  bookingCompleted.value = false;
  bookingError.value = null;
  fullName.value = auth.user?.full_name ?? '';
  email.value = auth.user?.email ?? '';
  stops.value = ['', ''];
  distanceKm.value = null;
  routeError.value = null;
  routeCoordinates.value = [];
  bookingNotes.value = '';
};

const loadAvailableCars = async () => {
  if (!start.value || !end.value) return;
  loadingCars.value = true;
  datesError.value = null;
  waitlistJoined.value = new Set();

  try {
    const [availableRes, allRes] = await Promise.all([
      http.get<Car[]>('/cars/available', {
        params: { start_datetime: start.value.toISOString(), end_datetime: end.value.toISOString() }
      }),
      http.get<Car[]>('/cars'),
    ]);
    availableCars.value = availableRes.data;
    allCars.value = allRes.data;
  } catch (err: any) {
    datesError.value = err?.response?.data?.detail ?? t('reserve_error_load_cars');
    availableCars.value = [];
    allCars.value = [];
  } finally {
    loadingCars.value = false;
  }
};

const hasAvailableCars = computed(() => availableCars.value.length > 0);

const canSubmitBooking = computed(() =>
  !!selectedCar.value && !!start.value && !!end.value && distanceKm.value != null && !bookingSubmitting.value
);

const submitBooking = async () => {
  if (!auth.user) { bookingError.value = t('reserve_error_not_logged_in'); return; }
  if (!selectedCar.value || !start.value || !end.value || distanceKm.value == null) return;

  bookingSubmitting.value = true;
  bookingError.value = null;
  bookingCompleted.value = false;

  let bookingId: number | null = null;

  try {
    const res = await http.post<{ id: number }>('/bookings', null, {
      params: {
        car_id: selectedCar.value.id,
        start_datetime: start.value.toISOString(),
        end_datetime: end.value.toISOString(),
        distance_km: distanceKm.value,
        stops: JSON.stringify(trimmedStops.value),
        notes: bookingNotes.value.trim() || undefined,
        route_coordinates: routeCoordinates.value.length >= 2
          ? JSON.stringify(routeCoordinates.value)
          : undefined,
      }
    });
    bookingId = res.data.id;
  } catch (err: any) {
    bookingError.value = err?.response?.data?.detail ?? t('reserve_error_booking');
  } finally {
    bookingSubmitting.value = false;
  }

  if (bookingId != null) {
    await router.push({ name: 'booking-detail', params: { id: String(bookingId) }, query: { new: '1' } });
  }
};
</script>

<template>
  <div class="flex-1 flex justify-center w-full px-4 py-6">
    <Card class="w-full max-w-4xl">
      <template #title>
        <span>{{ $t('reserve_title') }}</span>
      </template>

      <template #content>
        <Stepper :value="activeStep" linear class="w-full">
          <StepList>
            <Step :value="1">{{ $t('reserve_step_dates') }}</Step>
            <Step :value="2">{{ $t('reserve_step_select_car') }}</Step>
            <Step :value="3">{{ $t('reserve_step_select_route') }}</Step>
            <Step :value="4">{{ $t('reserve_step_confirm') }}</Step>
          </StepList>
        </Stepper>

        <!-- Step content: v-if switches content, watcher animates the incoming div -->
        <div class="mt-6 overflow-x-hidden" ref="stepContentEl">

            <!-- Step 1: Dates & Times -->
            <div v-if="activeStep === 1" class="flex flex-col gap-6">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2">
                  <span class="block text-sm font-medium">{{ $t('reserve_start_label') }}</span>
                  <DatePicker v-model="start" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5"
                    fluid inline />
                </div>
                <div class="space-y-2">
                  <span class="block text-sm font-medium">{{ $t('reserve_end_label') }}</span>
                  <DatePicker v-model="end" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5"
                    fluid inline />
                </div>
              </div>

              <div v-if="datesError" class="text-sm text-red-500">{{ datesError }}</div>

              <div class="flex justify-end gap-2">
                <Button :label="$t('reserve_next')" icon="pi pi-arrow-right" iconPos="right"
                  :disabled="!canGoNextFromDates || loadingCars" :loading="loadingCars"
                  @click="handleDatesNext" />
              </div>
            </div>

            <!-- Step 2: Select Car -->
            <div v-else-if="activeStep === 2" class="lg:grid lg:grid-cols-[1fr_240px] lg:gap-6 lg:items-start flex flex-col gap-6">
              <!-- Main content -->
              <div class="flex flex-col gap-6 min-w-0">
              <div v-if="!hasAvailableCars && !loadingCars" class="text-sm text-surface-500">
                {{ $t('reserve_no_cars_available') }}<br />
                {{ $t('reserve_go_back_different_dates') }}
              </div>

              <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <Card v-for="(car, index) in availableCars" :key="car.id"
                  class="overflow-hidden cursor-pointer hover:-translate-y-1.5 hover:shadow-xl transition-all duration-300 card-animate"
                  :style="{ animationDelay: `${index * 70}ms` }" @click="handleSelectCar(car)">
                  <template #header>
                    <div class="h-80 w-full relative">
                      <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
                      <div class="absolute inset-0 bg-gradient-to-t from-black/65 via-black/15 to-transparent pointer-events-none" />
                      <div class="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
                        <p class="text-white font-semibold text-base leading-tight">{{ car.name }}</p>
                        <p class="text-white/75 text-sm mt-0.5">{{ car.price_per_km }} € / km</p>
                      </div>
                    </div>
                  </template>
                  <template #content>
                    <p class="text-sm text-surface-500 mb-3 line-clamp-2">
                      {{ car.description || $t('reserve_no_description') }}
                    </p>
                    <Button :label="$t('reserve_select_button')" size="small" class="w-full"
                      @click.stop="handleSelectCar(car)" />
                  </template>
                </Card>
              </div>

              <div v-if="unavailableCars.length > 0" class="space-y-3">
                <p class="text-sm font-medium text-surface-500">{{ $t('reserve_unavailable_for_dates') }}</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <Card v-for="car in unavailableCars" :key="car.id" class="overflow-hidden opacity-60 grayscale">
                    <template #header>
                      <div class="h-44 w-full relative">
                        <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
                        <div class="absolute inset-0 bg-gradient-to-t from-black/65 via-black/15 to-transparent pointer-events-none" />
                        <div class="absolute bottom-0 left-0 right-0 p-3 pointer-events-none">
                          <p class="text-white font-semibold text-sm leading-tight">{{ car.name }}</p>
                          <p class="text-white/75 text-xs mt-0.5">{{ car.price_per_km }} € / km</p>
                        </div>
                      </div>
                    </template>
                    <template #content>
                      <p class="text-sm text-surface-500 mb-3">{{ car.description || $t('reserve_no_description') }}</p>
                      <Button v-if="!waitlistJoined.has(car.id)" :label="$t('reserve_notify_when_available')"
                        icon="pi pi-bell" size="small" severity="secondary" outlined
                        :loading="waitlistLoading.has(car.id)" @click="joinWaitlist(car)" />
                      <div v-else class="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                        <i class="pi pi-check-circle" />
                        <span>{{ $t('reserve_on_waitlist') }}</span>
                      </div>
                    </template>
                  </Card>
                </div>
              </div>

              <div class="flex justify-between">
                <Button :label="$t('reserve_previous')" icon="pi pi-arrow-left" severity="secondary" outlined
                  @click="goBack(1)" />
              </div>
              </div>

              <!-- Sticky summary sidebar (desktop only) -->
              <div class="hidden lg:block">
                <div class="sticky top-6 rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5 space-y-4 shadow-sm">
                  <p class="text-xs font-semibold uppercase tracking-wider text-surface-400">{{ $t('reserve_summary') }}</p>
                  <div class="space-y-2 text-sm">
                    <div class="flex items-start gap-2">
                      <i class="pi pi-calendar text-primary mt-0.5 shrink-0" />
                      <div>
                        <p class="font-medium">{{ start ? formatDateTime(start) : '—' }}</p>
                        <p class="text-surface-400 text-xs mt-0.5">{{ $t('reserve_label_start') }}</p>
                      </div>
                    </div>
                    <div class="flex items-start gap-2">
                      <i class="pi pi-calendar text-primary mt-0.5 shrink-0" />
                      <div>
                        <p class="font-medium">{{ end ? formatDateTime(end) : '—' }}</p>
                        <p class="text-surface-400 text-xs mt-0.5">{{ $t('reserve_label_end') }}</p>
                      </div>
                    </div>
                  </div>
                  <div class="pt-3 border-t border-surface-100 dark:border-zinc-700 flex items-center gap-2">
                    <i class="pi pi-car text-primary text-sm" />
                    <span class="text-sm">
                      <span class="font-bold text-primary">{{ availableCars.length }}</span>
                      {{ $t('reserve_cars_available') }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 3: Route -->
            <div v-else-if="activeStep === 3" class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
              <div class="flex flex-col gap-6 w-full">
                <div class="space-y-2">
                  <h2 class="font-semibold text-base">{{ $t('reserve_route_title') }}</h2>
                  <p class="text-sm text-surface-500">{{ $t('reserve_route_description') }}</p>
                </div>

                <TransitionGroup name="stop" tag="div" class="relative flex flex-col">
                  <div v-for="(_stop, index) in stops" :key="stopKeys[index]" class="flex gap-3">
                    <div class="flex flex-col items-center w-8 shrink-0">
                      <div class="h-5 shrink-0" />
                      <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold z-10"
                        :class="index === 0
                          ? 'bg-primary text-white'
                          : index === stops.length - 1
                          ? 'bg-slate-600 text-white'
                          : 'bg-surface-0 dark:bg-surface-800 text-surface-600 dark:text-surface-300 border-2 border-surface-300 dark:border-surface-500'">
                        {{ String.fromCharCode(65 + index) }}
                      </div>
                      <div v-if="index < stops.length - 1" class="connector-line" />
                    </div>

                    <div class="flex-1 min-w-0 pb-3 flex items-start gap-2">
                      <div class="flex-1 min-w-0">
                        <span class="block text-xs font-medium mb-1 text-surface-500">
                          {{ index === 0 ? $t('reserve_start_location') : index === stops.length - 1 ? $t('reserve_end_location') : $t('reserve_stop_label').replace('{index}', String(index)) }}
                        </span>
                        <AutoComplete :ref="(el) => setStopRef(el, index)"
                          v-model="stops[index]"
                          :suggestions="locationSuggestions" :minLength="3" :delay="300"
                          :placeholder="$t('reserve_address_placeholder')" class="w-full" inputClass="w-full"
                          @mousedown="onStopPointerDown(index)" @touchstart.passive="onStopPointerDown(index)"
                          @focus="onStopFocus(index)" @blur="onStopBlur(index)" @complete="searchLocations" />
                      </div>
                      <Button v-if="index > 0 && index < stops.length - 1"
                        icon="pi pi-minus" severity="danger" outlined rounded size="small"
                        class="shrink-0 mt-6"
                        @click="removeStop(index)" />
                    </div>
                  </div>
                </TransitionGroup>

                <Button :label="$t('reserve_add_stop')" icon="pi pi-plus" text @click="addStop" />

                <div class="space-y-2">
                  <div class="flex items-center gap-4">
                    <Button :label="$t('reserve_calculate_distance')" icon="pi pi-map" :loading="routeEstimating"
                      :disabled="routeEstimating || trimmedStops.length < 2" @click="estimateRoute" />
                    <div v-if="distanceKm != null" class="text-sm space-y-1">
                      <div>
                        <span class="font-medium">{{ $t('reserve_total_distance') }}</span>
                        <span class="ml-1">{{ distanceKm.toFixed(1) }} km</span>
                      </div>
                      <div v-if="estimatedPrice != null">
                        <span class="font-medium">{{ $t('reserve_estimated_cost') }}</span>
                        <span class="ml-1">€{{ estimatedPrice.toFixed(2) }}</span>
                      </div>
                    </div>
                  </div>
                  <p v-if="routeError" class="text-sm text-red-500">{{ routeError }}</p>
                </div>

                <div class="flex justify-between">
                  <Button :label="$t('reserve_previous')" icon="pi pi-arrow-left" severity="secondary" outlined
                    @click="goBack(2)" />
                  <Button :label="$t('reserve_next')" icon="pi pi-arrow-right" iconPos="right"
                    :disabled="!canGoNextFromRoute" @click="goForward(4)" />
                </div>
              </div>

              <div class="flex flex-col h-full">
                <h3 class="text-sm font-medium mb-2">{{ $t('reserve_route_preview') }}</h3>
                <div class="flex-1 min-h-[300px]">
                  <RouteMap :coordinates="routeCoordinates" />
                </div>
              </div>
            </div>

            <!-- Step 4: Confirm -->
            <div v-else-if="activeStep === 4" class="flex flex-col gap-6">
              <div class="space-y-3">
                <h2 class="font-semibold text-base">{{ $t('reserve_summary_title') }}</h2>
                <div class="rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden text-sm divide-y divide-surface-100 dark:divide-surface-700">
                  <div v-if="selectedCar" class="flex justify-between items-center px-4 py-3 bg-surface-50 dark:bg-surface-800/50">
                    <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-car" />{{ $t('reserve_car_label') }}</span>
                    <span class="font-medium">{{ selectedCar.name }}</span>
                  </div>
                  <div v-if="selectedCar" class="flex justify-between items-center px-4 py-3">
                    <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-tag" />{{ $t('reserve_price_per_km') }}</span>
                    <span class="font-medium">{{ selectedCar.price_per_km }} € / km</span>
                  </div>
                  <div v-if="start" class="flex justify-between items-center px-4 py-3 bg-surface-50 dark:bg-surface-800/50">
                    <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-calendar" />{{ $t('reserve_start_summary') }}</span>
                    <span class="font-medium">{{ formatDateTime(start!) }}</span>
                  </div>
                  <div v-if="end" class="flex justify-between items-center px-4 py-3">
                    <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-calendar-clock" />{{ $t('reserve_end_summary') }}</span>
                    <span class="font-medium">{{ formatDateTime(end!) }}</span>
                  </div>
                  <div v-if="trimmedStops.length >= 2" class="flex justify-between items-start px-4 py-3 bg-surface-50 dark:bg-surface-800/50">
                    <span class="flex items-center gap-2 text-surface-500 shrink-0"><i class="pi pi-map-marker" />{{ $t('reserve_route_summary') }}</span>
                    <ul class="text-right space-y-0.5">
                      <li v-for="(stop, index) in trimmedStops" :key="index" class="font-medium text-xs">{{ stop }}</li>
                    </ul>
                  </div>
                  <div v-if="distanceKm != null" class="flex justify-between items-center px-4 py-3">
                    <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-map" />{{ $t('reserve_total_distance') }}</span>
                    <span class="font-medium">{{ distanceKm.toFixed(1) }} km</span>
                  </div>
                  <div v-if="estimatedPrice != null" class="flex justify-between items-center px-4 py-3.5 bg-primary/5 dark:bg-primary/10">
                    <span class="flex items-center gap-2 font-semibold text-primary"><i class="pi pi-euro" />{{ $t('reserve_estimated_cost') }}</span>
                    <span class="text-xl font-bold text-primary">€{{ estimatedPrice.toFixed(2) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="!bookingCompleted" class="space-y-4">
                <div class="space-y-2">
                  <h2 class="font-semibold text-base">{{ $t('reserve_notes_title') }}
                    <span class="font-normal text-surface-400 text-sm">{{ $t('reserve_notes_optional') }}</span>
                  </h2>
                  <Textarea v-model="bookingNotes" rows="3" class="w-full"
                    :placeholder="$t('reserve_notes_placeholder')" autoResize />
                </div>

                <h2 class="font-semibold text-base">{{ $t('reserve_your_details') }}</h2>
                <div class="text-sm space-y-1">
                  <div>
                    <span class="font-medium">{{ $t('reserve_name_label') }}</span>
                    <span class="ml-2">{{ fullName }}</span>
                  </div>
                  <div>
                    <span class="font-medium">{{ $t('reserve_email_label') }}</span>
                    <span class="ml-2">{{ email }}</span>
                  </div>
                </div>

                <div v-if="bookingError" class="text-sm text-red-500">{{ bookingError }}</div>

                <div class="flex justify-between">
                  <Button :label="$t('reserve_previous')" icon="pi pi-arrow-left" severity="secondary" outlined
                    @click="goBack(3)" />
                  <Button :label="$t('reserve_confirm_button')" icon="pi pi-check" :disabled="!canSubmitBooking"
                    :loading="bookingSubmitting" @click="submitBooking" />
                </div>
              </div>

              <div v-else class="space-y-4">
                <div class="text-sm text-emerald-600">
                  {{ $t('reserve_booking_success') }}<br />
                  {{ $t('reserve_booking_pending') }}
                </div>
                <div class="flex gap-2">
                  <Button :label="$t('reserve_make_another')" @click="() => { resetFlow(); activeStep = 1; }" />
                  <Button :label="$t('reserve_go_to_homepage')" severity="secondary" outlined
                    @click="router.push({ name: 'home' })" />
                </div>
              </div>
            </div>

        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.card-animate {
  animation: cardFadeIn 0.35s ease forwards;
  opacity: 0;
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Dashed connector between stop circles */
.connector-line {
  flex: 1;
  width: 2px;
  min-height: 14px;
  margin-top: 4px;
  background-image: repeating-linear-gradient(
    to bottom,
    var(--p-surface-400, #94a3b8) 0, var(--p-surface-400, #94a3b8) 5px,
    transparent 5px, transparent 10px
  );
}

/* Stop add/remove transitions */
.stop-enter-active { transition: all 0.25s ease; }
.stop-leave-active { transition: all 0.2s ease; position: absolute; width: 100%; }
.stop-enter-from { opacity: 0; transform: translateX(-8px); }
.stop-leave-to   { opacity: 0; transform: translateX(-8px); }
.stop-move { transition: transform 0.25s ease; }
</style>
