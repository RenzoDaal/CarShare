<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import Button from 'primevue/button';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import http from '@/api/http';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { useRouter } from 'vue-router';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';
import RescheduleDialog from '@/components/RescheduleDialog.vue';

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
const toast = useToast();
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
        toast.add({ severity: 'success', summary: t('borrower_cancel'), life: 2500 });
      } catch (err: any) {
        toast.add({ severity: 'error', summary: err?.response?.data?.detail ?? t('borrower_error_cancel'), life: 4000 });
      }
    },
  });
}

// Reschedule dialog
const rescheduleVisible = ref(false);
const rescheduleBooking = ref<BorrowerBooking | null>(null);

function openReschedule(booking: BorrowerBooking) {
  rescheduleBooking.value = booking;
  rescheduleVisible.value = true;
}

const reminderSending = ref<Set<number>>(new Set());

async function sendReminder(bookingId: number) {
  reminderSending.value = new Set(reminderSending.value).add(bookingId);
  try {
    const { data } = await http.post<{ ok: boolean; last_reminder_sent: string }>(`/bookings/${bookingId}/remind`);
    const booking = bookings.value.find(b => b.id === bookingId);
    if (booking) booking.last_reminder_sent = data.last_reminder_sent;
    toast.add({ severity: 'success', summary: t('borrower_send_reminder'), life: 2500 });
  } catch (err: any) {
    toast.add({ severity: 'error', summary: err?.response?.data?.detail ?? t('borrower_reminder_error'), life: 4000 });
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
      <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-1 hover:shadow-md transition-shadow">
        <i class="pi pi-car text-primary text-lg mb-1" />
        <span class="text-2xl font-bold">{{ stats.total_rides }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_rides') }}</span>
      </div>
      <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-1 hover:shadow-md transition-shadow">
        <i class="pi pi-map-marker text-primary text-lg mb-1" />
        <span class="text-2xl font-bold">{{ stats.total_km.toFixed(0) }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_km') }}</span>
      </div>
      <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-1 hover:shadow-md transition-shadow">
        <i class="pi pi-wallet text-primary text-lg mb-1" />
        <span class="text-2xl font-bold">€{{ stats.total_spent.toFixed(2) }}</span>
        <span class="text-xs text-surface-500">{{ $t('borrower_stats_spent') }}</span>
      </div>
      <div v-if="stats.favourite_car" class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-1 hover:shadow-md transition-shadow">
        <i class="pi pi-heart text-primary text-lg mb-1" />
        <span class="text-lg font-bold truncate">{{ stats.favourite_car }}</span>
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
            <Card v-for="booking in upcoming" :key="booking.id" class="h-full overflow-hidden"
              :style="{
                boxShadow: booking.status === 'pending'
                  ? 'inset 0 3px 0 #fbbf24'
                  : booking.status === 'accepted'
                  ? 'inset 0 3px 0 #22c55e'
                  : undefined
              }">
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
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div v-for="booking in history" :key="booking.id"
              class="rounded-xl border border-surface-200 dark:border-surface-700 p-3 flex flex-col gap-1.5 opacity-75 hover:opacity-100 transition-opacity cursor-pointer"
              @click="router.push({ name: 'booking-detail', params: { id: booking.id } })">
              <div class="flex items-center justify-between gap-2">
                <span class="font-medium text-sm truncate">{{ booking.car.name }}</span>
                <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
              </div>
              <p class="text-xs text-surface-500">{{ formatDateTime(booking.start_datetime) }}</p>
              <p v-if="booking.total_price != null" class="text-xs font-medium text-primary">€{{ booking.total_price.toFixed(2) }}</p>
            </div>
          </div>
        </template>
      </Card>
    </template>
  </div>

  <RescheduleDialog v-model:visible="rescheduleVisible" :booking="rescheduleBooking" @rescheduled="fetchBookings" />
</template>
