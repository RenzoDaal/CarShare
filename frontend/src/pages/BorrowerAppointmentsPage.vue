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
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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
  created_at?: string | null;
  last_reminder_sent?: string | null;
};

type BorrowerStats = {
  total_rides: number;
  total_km: number;
  total_spent: number;
  favourite_car: string | null;
};

const confirm = useConfirm();
const router = useRouter();
const bookings = ref<BorrowerBooking[]>([]);
const stats = ref<BorrowerStats | null>(null);

async function fetchStats() {
  try {
    const { data } = await http.get<BorrowerStats>('/bookings/borrower/stats');
    stats.value = data;
  } catch {
    // silently ignore
  }
}

type WaitlistEntry = {
  id: number;
  car_id: number;
  car_name: string;
  start_datetime: string;
  end_datetime: string;
};

const waitlist = ref<WaitlistEntry[]>([]);

async function fetchWaitlist() {
  try {
    const { data } = await http.get<WaitlistEntry[]>('/waitlist/mine');
    waitlist.value = data;
  } catch {
    waitlist.value = [];
  }
}

async function leaveWaitlist(id: number) {
  await http.delete(`/waitlist/${id}`);
  waitlist.value = waitlist.value.filter(e => e.id !== id);
}
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
    error.value = err?.response?.data?.detail ?? t('borrower_error_load');
  } finally {
    loading.value = false;
  }
}

function confirmCancel(bookingId: number) {
  confirm.require({
    message: t('borrower_confirm_cancel_message'),
    header: t('borrower_confirm_cancel_header'),
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: t('borrower_confirm_keep'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('borrower_confirm_cancel_button'), severity: 'danger' },
    accept: async () => {
      try {
        await http.post(`/bookings/${bookingId}/cancel`);
        await fetchBookings();
      } catch (err: any) {
        error.value = err?.response?.data?.detail ?? t('borrower_error_cancel');
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
    rescheduleRouteError.value = t('borrower_reschedule_error_route');
    return;
  }
  rescheduleRouteEstimating.value = true;
  try {
    const res = await http.post('/routes/estimate', { stops: rescheduleTrimmedStops.value });
    rescheduleDistanceKm.value = res.data.distance_km;
  } catch (err: any) {
    rescheduleRouteError.value = err?.response?.data?.detail ?? t('borrower_reschedule_error_estimate');
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
    rescheduleError.value = t('borrower_reschedule_error_end_after_start');
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
    rescheduleError.value = err?.response?.data?.detail ?? t('borrower_reschedule_error_submit');
  } finally {
    rescheduleSubmitting.value = false;
  }
}

const reminderSending = ref<Set<number>>(new Set());

async function sendReminder(bookingId: number) {
  reminderSending.value = new Set(reminderSending.value).add(bookingId);
  try {
    const { data } = await http.post<{ ok: boolean; last_reminder_sent: string }>(`/bookings/${bookingId}/remind`);
    const booking = bookings.value.find(b => b.id === bookingId);
    if (booking) booking.last_reminder_sent = data.last_reminder_sent;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? t('borrower_reminder_error');
  } finally {
    const next = new Set(reminderSending.value);
    next.delete(bookingId);
    reminderSending.value = next;
  }
}

onMounted(() => {
  fetchBookings();
  fetchWaitlist();
  fetchStats();
});
</script>

<template>
  <div class="p-4 flex flex-col gap-4 max-w-5xl mx-auto w-full">
    <h1 class="text-2xl font-semibold mb-2">{{ $t('borrower_appointments_title') }}</h1>

    <div v-if="stats && stats.total_rides > 0"
      class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div class="rounded-lg border border-surface-200 dark:border-surface-700 p-3 flex flex-col gap-0.5">
        <span class="text-2xl font-semibold">{{ stats.total_rides }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_rides') }}</span>
      </div>
      <div class="rounded-lg border border-surface-200 dark:border-surface-700 p-3 flex flex-col gap-0.5">
        <span class="text-2xl font-semibold">{{ stats.total_km.toFixed(0) }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_km') }}</span>
      </div>
      <div class="rounded-lg border border-surface-200 dark:border-surface-700 p-3 flex flex-col gap-0.5">
        <span class="text-2xl font-semibold">€{{ stats.total_spent.toFixed(2) }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_spent') }}</span>
      </div>
      <div v-if="stats.favourite_car" class="rounded-lg border border-surface-200 dark:border-surface-700 p-3 flex flex-col gap-0.5">
        <span class="text-lg font-semibold truncate">{{ stats.favourite_car }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_favourite') }}</span>
      </div>
    </div>

    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <div v-if="loading" class="flex justify-center items-center py-10">
      <ProgressSpinner />
    </div>

    <template v-else>
      <Card class="mb-4">
        <template #title>{{ $t('borrower_upcoming_title') }}</template>
        <template #content>
          <div v-if="upcoming.length === 0" class="text-sm text-surface-500">
            {{ $t('borrower_no_upcoming') }}
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <Card v-for="booking in upcoming" :key="booking.id" class="h-full">
              <template #title>{{ booking.car.name }}</template>
              <template #subtitle>
                <div class="flex items-center gap-2 flex-wrap">
                  <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
                  <span v-if="booking.status === 'pending'" class="text-xs text-surface-400">{{ $t('borrower_awaiting_owner_approval') }}</span>
                </div>
              </template>
              <template #content>
                <p class="text-sm text-surface-500 mb-1">
                  {{ formatDateTime(booking.start_datetime) }} –
                  {{ formatDateTime(booking.end_datetime) }}
                </p>
                <p v-if="booking.total_price != null" class="text-sm font-medium mt-1">
                  {{ $t('borrower_total_price') }} €{{ booking.total_price.toFixed(2) }}
                </p>
                <p v-if="booking.notes" class="text-sm mt-2 p-2 rounded bg-surface-100 dark:bg-surface-800 italic text-surface-500">
                  "{{ booking.notes }}"
                </p>
                <div class="mt-3 flex gap-2 flex-wrap">
                  <Button :label="$t('borrower_summary')" icon="pi pi-file" severity="secondary" outlined size="small"
                    @click="router.push({ name: 'booking-detail', params: { id: booking.id } })" />
                  <Button :label="$t('borrower_reschedule')" icon="pi pi-calendar-clock" severity="secondary" outlined size="small"
                    @click="openReschedule(booking)" />
                  <Button v-if="booking.status === 'pending'" :label="$t('borrower_send_reminder')" icon="pi pi-bell"
                    severity="secondary" outlined size="small"
                    :loading="reminderSending.has(booking.id)"
                    :disabled="reminderSending.has(booking.id)"
                    @click="sendReminder(booking.id)" />
                  <Button :label="$t('borrower_cancel')" icon="pi pi-times" severity="danger" outlined size="small"
                    @click="confirmCancel(booking.id)" />
                </div>
              </template>
            </Card>
          </div>
        </template>
      </Card>

      <Card v-if="waitlist.length > 0">
        <template #title>
          <div class="flex items-center gap-2">
            <span>{{ $t('borrower_waitlist_title') }}</span>
            <span class="text-xs text-surface-400 font-normal">{{ $t('borrower_waitlist_subtitle') }}</span>
          </div>
        </template>
        <template #content>
          <ul class="flex flex-col gap-2 text-sm">
            <li v-for="entry in waitlist" :key="entry.id"
              class="flex items-center justify-between border rounded-md px-3 py-2">
              <div>
                <p class="font-medium">{{ entry.car_name }}</p>
                <p class="text-xs text-surface-500">
                  {{ formatDateTime(entry.start_datetime) }} – {{ formatDateTime(entry.end_datetime) }}
                </p>
              </div>
              <Button icon="pi pi-times" severity="danger" text rounded size="small"
                :title="$t('borrower_leave_waitlist_title')" @click="leaveWaitlist(entry.id)" />
            </li>
          </ul>
        </template>
      </Card>

      <Card>
        <template #title>{{ $t('borrower_past_cancelled_title') }}</template>
        <template #content>
          <div v-if="history.length === 0" class="text-sm text-surface-500">
            {{ $t('borrower_no_past') }}
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
  <Dialog v-model:visible="rescheduleVisible" :header="$t('borrower_reschedule_dialog_title')" modal :style="{ width: '42rem' }">
    <div class="flex flex-col gap-5 mt-2">

      <!-- Dates -->
      <div class="grid gap-4 md:grid-cols-2">
        <div class="space-y-2">
          <span class="block text-sm font-medium">{{ $t('borrower_reschedule_new_start') }}</span>
          <DatePicker v-model="rescheduleStart" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5" fluid />
        </div>
        <div class="space-y-2">
          <span class="block text-sm font-medium">{{ $t('borrower_reschedule_new_end') }}</span>
          <DatePicker v-model="rescheduleEnd" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5" fluid />
        </div>
      </div>

      <!-- Route -->
      <div class="space-y-3">
        <span class="block text-sm font-medium">{{ $t('borrower_reschedule_route') }}</span>
        <div v-for="(_stop, index) in rescheduleStops" :key="index" class="flex items-center gap-2">
          <div class="flex-1 min-w-0">
            <span class="block text-xs text-surface-400 mb-1">
              {{ index === 0 ? $t('borrower_start_location') : index === rescheduleStops.length - 1 ? $t('borrower_end_location') : $t('borrower_stop_label').replace('{index}', String(index)) }}
            </span>
            <AutoComplete v-model="rescheduleStops[index]" :suggestions="locationSuggestions" :minLength="3"
              :delay="300" :placeholder="$t('borrower_address_placeholder')" class="w-full" inputClass="w-full"
              @complete="searchLocations" />
          </div>
          <Button icon="pi pi-trash" severity="danger" text rounded
            :disabled="rescheduleStops.length <= 2" @click="removeRescheduleStop(index)" />
        </div>
        <Button :label="$t('borrower_reschedule_add_stop')" icon="pi pi-plus" text size="small" @click="addRescheduleStop" />

        <div class="flex items-center gap-4 flex-wrap">
          <Button :label="$t('borrower_reschedule_calculate_distance')" icon="pi pi-map" size="small"
            :loading="rescheduleRouteEstimating"
            :disabled="rescheduleRouteEstimating || rescheduleTrimmedStops.length < 2"
            @click="estimateRescheduleRoute" />
          <div v-if="rescheduleDistanceKm != null" class="text-sm space-y-0.5">
            <div><span class="font-medium">{{ $t('borrower_reschedule_distance') }}</span> {{ rescheduleDistanceKm.toFixed(1) }} km</div>
            <div v-if="rescheduleEstimatedPrice != null"><span class="font-medium">{{ $t('borrower_reschedule_estimated_cost') }}</span> €{{ rescheduleEstimatedPrice.toFixed(2) }}</div>
          </div>
        </div>
        <p v-if="rescheduleRouteError" class="text-sm text-red-500">{{ rescheduleRouteError }}</p>
        <p class="text-xs text-surface-400">{{ $t('borrower_reschedule_keep_route') }}</p>
      </div>

      <!-- Notes -->
      <div class="space-y-2">
        <span class="block text-sm font-medium">{{ $t('borrower_reschedule_notes_label') }}</span>
        <Textarea v-model="rescheduleNotes" rows="3" :placeholder="$t('borrower_reschedule_notes_placeholder')" class="w-full" fluid />
      </div>

      <p class="text-xs text-surface-400">{{ $t('borrower_reschedule_pending_warning') }}</p>
      <p v-if="rescheduleError" class="text-sm text-red-500">{{ rescheduleError }}</p>
      <div class="flex justify-end gap-2">
        <Button :label="$t('borrower_reschedule_cancel')" severity="secondary" outlined @click="rescheduleVisible = false" />
        <Button :label="$t('borrower_reschedule_confirm')" icon="pi pi-check" :loading="rescheduleSubmitting"
          :disabled="!rescheduleStart || !rescheduleEnd || rescheduleSubmitting"
          @click="submitReschedule" />
      </div>
    </div>
  </Dialog>
</template>
