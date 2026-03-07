<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import Button from 'primevue/button';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import Dialog from 'primevue/dialog';
import DatePicker from 'primevue/datepicker';
import AutoComplete from 'primevue/autocomplete';
import Textarea from 'primevue/textarea';
import http from '@/api/http';
import { useConfirm } from 'primevue/useconfirm';
import { useRouter } from 'vue-router';

type BookingStatus = 'pending' | 'accepted' | 'declined' | 'cancelled';

type BorrowerBooking = {
  id: number;
  car: {
    id: number;
    owner_id: number;
    name: string;
    description?: string | null;
    price_per_km: number;
    is_active: boolean;
    image_url?: string | null;
  };
  start_datetime: string;
  end_datetime: string;
  status: BookingStatus;
  total_price?: number | null;
  stops?: string[] | null;
  notes?: string | null;
};

const confirm = useConfirm();
const router = useRouter();
const bookings = ref<BorrowerBooking[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const now = new Date();
const upcoming = computed(() =>
  bookings.value.filter(
    (b) => b.status !== 'declined' && b.status !== 'cancelled' && toUtcDate(b.end_datetime) >= now,
  ),
);
const history = computed(() =>
  bookings.value.filter(
    (b) => b.status === 'declined' || b.status === 'cancelled' || toUtcDate(b.end_datetime) < now,
  ),
);

function toUtcDate(value: string): Date {
  const normalized = value.endsWith('Z') || value.includes('+') ? value : value + 'Z';
  return new Date(normalized);
}

function formatDateTime(value: string) {
  return toUtcDate(value).toLocaleString();
}

function statusSeverity(status: BookingStatus) {
  if (status === 'accepted') return 'success';
  if (status === 'pending') return 'warning';
  return 'danger';
}

async function fetchBookings() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await http.get<BorrowerBooking[]>('/bookings/borrower');
    bookings.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to load bookings';
  } finally {
    loading.value = false;
  }
}

function confirmCancel(bookingId: number) {
  confirm.require({
    message: 'Are you sure you want to cancel this booking?',
    header: 'Cancel booking',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Keep booking', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Cancel booking', severity: 'danger' },
    accept: async () => {
      try {
        await http.post(`/bookings/${bookingId}/cancel`);
        await fetchBookings();
      } catch (err: any) {
        error.value = err?.response?.data?.detail ?? 'Failed to cancel booking';
      }
    },
  });
}

// Reschedule dialog
const rescheduleVisible = ref(false);
const rescheduleBookingId = ref<number | null>(null);
const rescheduleBooking = ref<BorrowerBooking | null>(null);
const rescheduleStart = ref<Date | null>(null);
const rescheduleEnd = ref<Date | null>(null);
const rescheduleSubmitting = ref(false);
const rescheduleError = ref<string | null>(null);

// Route within reschedule dialog
const rescheduleNotes = ref<string>('');
const rescheduleStops = ref<string[]>(['', '']);
const locationSuggestions = ref<string[]>([]);
const rescheduleDistanceKm = ref<number | null>(null);
const rescheduleRouteEstimating = ref(false);
const rescheduleRouteError = ref<string | null>(null);

const rescheduleTrimmedStops = computed(() =>
  rescheduleStops.value.map(s => s.trim()).filter(Boolean)
);

const rescheduleEstimatedPrice = computed(() => {
  const pricePerKm = rescheduleBooking.value?.car.price_per_km;
  if (pricePerKm == null || rescheduleDistanceKm.value == null) return null;
  return rescheduleDistanceKm.value * pricePerKm;
});

watch(rescheduleStops, () => {
  rescheduleDistanceKm.value = null;
  rescheduleRouteError.value = null;
}, { deep: true });

function addRescheduleStop() {
  rescheduleStops.value.splice(rescheduleStops.value.length - 1, 0, '');
}

function removeRescheduleStop(index: number) {
  if (rescheduleStops.value.length <= 2) return;
  rescheduleStops.value.splice(index, 1);
}

async function searchLocations(event: { query: string }) {
  const query = (event.query || '').trim();
  if (!query || query.length < 3) { locationSuggestions.value = []; return; }
  try {
    const res = await http.get<string[]>('/locations/suggest', { params: { query } });
    locationSuggestions.value = res.data;
  } catch {
    locationSuggestions.value = [];
  }
}

async function estimateRescheduleRoute() {
  rescheduleRouteError.value = null;
  rescheduleDistanceKm.value = null;
  if (rescheduleTrimmedStops.value.length < 2) {
    rescheduleRouteError.value = 'Please enter at least a start and end location.';
    return;
  }
  rescheduleRouteEstimating.value = true;
  try {
    const res = await http.post('/routes/estimate', { stops: rescheduleTrimmedStops.value });
    rescheduleDistanceKm.value = res.data.distance_km;
  } catch (err: any) {
    rescheduleRouteError.value = err?.response?.data?.detail ?? 'Failed to estimate route.';
  } finally {
    rescheduleRouteEstimating.value = false;
  }
}

function openReschedule(booking: BorrowerBooking) {
  rescheduleBookingId.value = booking.id;
  rescheduleBooking.value = booking;
  rescheduleStart.value = toUtcDate(booking.start_datetime);
  rescheduleEnd.value = toUtcDate(booking.end_datetime);
  rescheduleStops.value = booking.stops && booking.stops.length >= 2 ? [...booking.stops] : ['', ''];
  rescheduleNotes.value = booking.notes ?? '';
  rescheduleDistanceKm.value = null;
  rescheduleRouteError.value = null;
  rescheduleError.value = null;
  rescheduleVisible.value = true;
}

async function submitReschedule() {
  if (!rescheduleBookingId.value || !rescheduleStart.value || !rescheduleEnd.value) return;
  if (rescheduleEnd.value <= rescheduleStart.value) {
    rescheduleError.value = 'End time must be after start time.';
    return;
  }
  rescheduleSubmitting.value = true;
  rescheduleError.value = null;
  try {
    await http.patch(`/bookings/${rescheduleBookingId.value}/reschedule`, {
      start_datetime: rescheduleStart.value.toISOString(),
      end_datetime: rescheduleEnd.value.toISOString(),
      distance_km: rescheduleDistanceKm.value,
      stops: rescheduleTrimmedStops.value.length >= 2 ? rescheduleTrimmedStops.value : null,
      notes: rescheduleNotes.value || null,
    });
    rescheduleVisible.value = false;
    await fetchBookings();
  } catch (err: any) {
    rescheduleError.value = err?.response?.data?.detail ?? 'Failed to reschedule booking';
  } finally {
    rescheduleSubmitting.value = false;
  }
}

onMounted(fetchBookings);
</script>

<template>
  <div class="p-4 flex flex-col gap-4 max-w-5xl mx-auto w-full">
    <h1 class="text-2xl font-semibold mb-2">My appointments</h1>

    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <div v-if="loading" class="flex justify-center items-center py-10">
      <ProgressSpinner />
    </div>

    <template v-else>
      <Card class="mb-4">
        <template #title>Upcoming and current</template>
        <template #content>
          <div v-if="upcoming.length === 0" class="text-sm text-surface-500">
            You don't have any upcoming bookings.
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <Card v-for="booking in upcoming" :key="booking.id" class="h-full">
              <template #title>{{ booking.car.name }}</template>
              <template #subtitle>
                <div class="flex items-center gap-2 flex-wrap">
                  <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
                  <span v-if="booking.status === 'pending'" class="text-xs text-surface-400">Awaiting owner approval</span>
                </div>
              </template>
              <template #content>
                <p class="text-sm text-surface-500 mb-1">
                  {{ formatDateTime(booking.start_datetime) }} –
                  {{ formatDateTime(booking.end_datetime) }}
                </p>
                <p v-if="booking.total_price != null" class="text-sm font-medium mt-1">
                  Total price: €{{ booking.total_price.toFixed(2) }}
                </p>
                <p v-if="booking.notes" class="text-sm mt-2 p-2 rounded bg-surface-100 dark:bg-surface-800 italic text-surface-500">
                  "{{ booking.notes }}"
                </p>
                <div class="mt-3 flex gap-2 flex-wrap">
                  <Button label="Summary" icon="pi pi-file" severity="secondary" outlined size="small"
                    @click="router.push({ name: 'booking-detail', params: { id: booking.id } })" />
                  <Button label="Reschedule" icon="pi pi-calendar-clock" severity="secondary" outlined size="small"
                    @click="openReschedule(booking)" />
                  <Button label="Cancel" icon="pi pi-times" severity="danger" outlined size="small"
                    @click="confirmCancel(booking.id)" />
                </div>
              </template>
            </Card>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>Past & cancelled bookings</template>
        <template #content>
          <div v-if="history.length === 0" class="text-sm text-surface-500">
            No past or cancelled bookings.
          </div>
          <ul v-else class="flex flex-col gap-2 text-sm">
            <li v-for="booking in history" :key="booking.id"
              class="flex justify-between items-center border rounded-md p-2">
              <span>
                {{ booking.car.name }} –
                {{ formatDateTime(booking.start_datetime) }}
              </span>
              <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
            </li>
          </ul>
        </template>
      </Card>
    </template>
  </div>

  <!-- Reschedule dialog -->
  <Dialog v-model:visible="rescheduleVisible" header="Reschedule booking" modal :style="{ width: '42rem' }">
    <div class="flex flex-col gap-5 mt-2">

      <!-- Dates -->
      <div class="grid gap-4 md:grid-cols-2">
        <div class="space-y-2">
          <span class="block text-sm font-medium">New start</span>
          <DatePicker v-model="rescheduleStart" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5" fluid />
        </div>
        <div class="space-y-2">
          <span class="block text-sm font-medium">New end</span>
          <DatePicker v-model="rescheduleEnd" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5" fluid />
        </div>
      </div>

      <!-- Route -->
      <div class="space-y-3">
        <span class="block text-sm font-medium">Route</span>
        <div v-for="(_stop, index) in rescheduleStops" :key="index" class="flex items-center gap-2">
          <div class="flex-1 min-w-0">
            <span class="block text-xs text-surface-400 mb-1">
              {{ index === 0 ? 'Start location' : index === rescheduleStops.length - 1 ? 'End location' : `Stop ${index}` }}
            </span>
            <AutoComplete v-model="rescheduleStops[index]" :suggestions="locationSuggestions" :minLength="3"
              :delay="300" placeholder="Type an address" class="w-full" inputClass="w-full"
              @complete="searchLocations" />
          </div>
          <Button icon="pi pi-trash" severity="danger" text rounded
            :disabled="rescheduleStops.length <= 2" @click="removeRescheduleStop(index)" />
        </div>
        <Button label="Add stop" icon="pi pi-plus" text size="small" @click="addRescheduleStop" />

        <div class="flex items-center gap-4 flex-wrap">
          <Button label="Calculate distance" icon="pi pi-map" size="small"
            :loading="rescheduleRouteEstimating"
            :disabled="rescheduleRouteEstimating || rescheduleTrimmedStops.length < 2"
            @click="estimateRescheduleRoute" />
          <div v-if="rescheduleDistanceKm != null" class="text-sm space-y-0.5">
            <div><span class="font-medium">Distance:</span> {{ rescheduleDistanceKm.toFixed(1) }} km</div>
            <div v-if="rescheduleEstimatedPrice != null"><span class="font-medium">Estimated cost:</span> €{{ rescheduleEstimatedPrice.toFixed(2) }}</div>
          </div>
        </div>
        <p v-if="rescheduleRouteError" class="text-sm text-red-500">{{ rescheduleRouteError }}</p>
        <p class="text-xs text-surface-400">Leave route empty to keep the existing distance and price.</p>
      </div>

      <!-- Notes -->
      <div class="space-y-2">
        <span class="block text-sm font-medium">Notes for the owner</span>
        <Textarea v-model="rescheduleNotes" rows="3" placeholder="Optional message to the owner" class="w-full" fluid />
      </div>

      <p class="text-xs text-surface-400">Rescheduling will reset the booking status to pending — the owner will need to re-approve.</p>
      <p v-if="rescheduleError" class="text-sm text-red-500">{{ rescheduleError }}</p>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" outlined @click="rescheduleVisible = false" />
        <Button label="Confirm reschedule" icon="pi pi-check" :loading="rescheduleSubmitting"
          :disabled="!rescheduleStart || !rescheduleEnd || rescheduleSubmitting"
          @click="submitReschedule" />
      </div>
    </div>
  </Dialog>
</template>
