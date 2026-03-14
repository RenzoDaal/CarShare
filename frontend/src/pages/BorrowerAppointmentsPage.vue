<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useCountUp } from '@/composables/useCountUp';
import PullToRefresh from '@/components/PullToRefresh.vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import Button from 'primevue/button';
import Message from 'primevue/message';
import http from '@/api/http';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { useRouter } from 'vue-router';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';
import { haptic } from '@/utils/haptic';
import RescheduleDialog from '@/components/RescheduleDialog.vue';
import SwipeToCancel from '@/components/SwipeToCancel.vue';

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
    b => b.status !== 'declined' && b.status !== 'cancelled' && toUtcDate(b.end_datetime) >= now,
  ),
);
const history = computed(() =>
  bookings.value.filter(
    b => b.status === 'declined' || b.status === 'cancelled' || toUtcDate(b.end_datetime) < now,
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
  haptic(50);
  confirm.require({
    message: t('borrower_confirm_cancel_message'),
    header: t('borrower_confirm_cancel_header'),
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: t('borrower_confirm_keep'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('borrower_confirm_cancel_button'), severity: 'danger' },
    accept: async () => {
      haptic([50, 30, 80]);
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

const ptr = ref<InstanceType<typeof PullToRefresh>>();

const statRides = computed(() => stats.value?.total_rides ?? 0);
const statKm = computed(() => stats.value?.total_km ?? 0);
const statSpent = computed(() => stats.value?.total_spent ?? 0);

const ridesDisplay = useCountUp(statRides);
const kmDisplay = useCountUp(statKm);
const spentDisplay = useCountUp(statSpent);

async function refresh() {
  await Promise.all([fetchBookings(), fetchWaitlist(), fetchStats()]);
  ptr.value?.done();
}

onMounted(() => {
  fetchBookings();
  fetchWaitlist();
  fetchStats();
});
</script>

<template>
  <PullToRefresh ref="ptr" @refresh="refresh">
  <div class="p-4 flex flex-col gap-5 max-w-5xl mx-auto w-full">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('borrower_appointments_title') }}</h1>
    </div>

    <!-- Stats row -->
    <div v-if="stats && stats.total_rides > 0" class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
        <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
          <i class="pi pi-car text-primary text-base" />
        </div>
        <span class="text-2xl font-bold tracking-tight">{{ ridesDisplay.toFixed(0) }}</span>
        <span class="text-xs text-surface-400">{{ $t('borrower_stats_rides') }}</span>
      </div>
      <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
        <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
          <i class="pi pi-map-marker text-primary text-base" />
        </div>
        <span class="text-2xl font-bold tracking-tight">{{ kmDisplay.toFixed(0) }}</span>
        <span class="text-xs text-surface-400">{{ $t('borrower_stats_km') }}</span>
      </div>
      <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
        <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
          <i class="pi pi-wallet text-primary text-base" />
        </div>
        <span class="text-2xl font-bold tracking-tight">€{{ spentDisplay.toFixed(2) }}</span>
        <span class="text-xs text-surface-400">{{ $t('borrower_stats_spent') }}</span>
      </div>
      <div v-if="stats.favourite_car"
        class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
        <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
          <i class="pi pi-heart text-primary text-base" />
        </div>
        <span class="text-base font-bold truncate leading-tight">{{ stats.favourite_car }}</span>
        <span class="text-xs text-surface-400">{{ $t('borrower_stats_favourite') }}</span>
      </div>
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <div v-for="i in 3" :key="i"
        class="rounded-2xl border border-surface-200 dark:border-zinc-700 p-5 animate-pulse space-y-3">
        <div class="h-4 bg-surface-200 dark:bg-zinc-700 rounded-full w-1/2" />
        <div class="h-3 bg-surface-100 dark:bg-zinc-800 rounded-full w-3/4" />
        <div class="h-3 bg-surface-100 dark:bg-zinc-800 rounded-full w-1/2" />
        <div class="flex gap-2 mt-4">
          <div class="h-8 w-24 bg-surface-200 dark:bg-zinc-700 rounded-xl" />
          <div class="h-8 w-20 bg-surface-200 dark:bg-zinc-700 rounded-xl" />
        </div>
      </div>
    </div>

    <template v-else>
      <!-- ── Upcoming bookings ── -->
      <Card>
        <template #title>
          <div class="flex items-center gap-2">
            <span>{{ $t('borrower_upcoming_title') }}</span>
            <span v-if="upcoming.length > 0"
              class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-white text-xs font-bold">
              {{ upcoming.length }}
            </span>
          </div>
        </template>
        <template #content>
          <div v-if="upcoming.length === 0"
            class="flex flex-col items-center gap-3 py-10 text-center">
            <div class="w-14 h-14 rounded-2xl bg-surface-100 dark:bg-zinc-800 flex items-center justify-center">
              <i class="pi pi-calendar text-xl text-surface-400" />
            </div>
            <p class="text-sm text-surface-500">{{ $t('borrower_no_upcoming') }}</p>
            <Button :label="$t('dashboard_reserve_car')" icon="pi pi-calendar-plus" size="small"
              @click="router.push({ name: 'reserve car' })" />
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <SwipeToCancel v-for="booking in upcoming" :key="booking.id" @cancel="confirmCancel(booking.id)">
            <div
              class="bg-white dark:bg-zinc-900 rounded-2xl border overflow-hidden flex flex-col transition-all duration-200 hover:shadow-md"
              :style="{
                borderColor: booking.status === 'pending' ? '#fbbf24' : booking.status === 'accepted' ? '#22c55e' : undefined,
                borderWidth: '1.5px',
              }"
            >
              <!-- Top color bar -->
              <div class="h-1 w-full"
                :class="booking.status === 'pending' ? 'bg-amber-400' : booking.status === 'accepted' ? 'bg-green-500' : 'bg-slate-300'" />

              <div class="p-4 flex flex-col gap-2 flex-1">
                <div class="flex items-start justify-between gap-2">
                  <h3 class="font-bold text-base leading-tight">{{ booking.car.name }}</h3>
                  <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
                </div>

                <p class="text-sm text-surface-500">
                  {{ formatDateTime(booking.start_datetime) }} – {{ formatDateTime(booking.end_datetime) }}
                </p>

                <p v-if="booking.total_price != null" class="text-sm font-semibold text-primary">
                  {{ $t('borrower_total_price') }} €{{ booking.total_price.toFixed(2) }}
                </p>

                <p v-if="booking.status === 'pending'" class="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                  <i class="pi pi-clock text-xs" />
                  {{ $t('borrower_awaiting_owner_approval') }}
                </p>

                <div v-if="booking.notes"
                  class="text-xs p-2.5 rounded-xl bg-surface-50 dark:bg-zinc-800 italic text-surface-400 border border-surface-100 dark:border-zinc-700">
                  "{{ booking.notes }}"
                </div>

                <div class="mt-auto pt-3 flex gap-2 flex-wrap">
                  <Button :label="$t('borrower_summary')" icon="pi pi-file" severity="secondary" outlined size="small"
                    @click="router.push({ name: 'booking-detail', params: { id: booking.id } })" />
                  <Button :label="$t('borrower_reschedule')" icon="pi pi-calendar-clock" severity="secondary" outlined
                    size="small" @click="openReschedule(booking)" />
                  <Button v-if="booking.status === 'pending'" :label="$t('borrower_send_reminder')" icon="pi pi-bell"
                    severity="secondary" outlined size="small"
                    :loading="reminderSending.has(booking.id)"
                    :disabled="reminderSending.has(booking.id)"
                    @click="sendReminder(booking.id)" />
                  <Button :label="$t('borrower_cancel')" icon="pi pi-times" severity="danger" outlined size="small"
                    @click="confirmCancel(booking.id)" />
                </div>
              </div>
            </div>
            </SwipeToCancel>
          </div>
        </template>
      </Card>

      <!-- ── Waitlist ── -->
      <Card v-if="waitlist.length > 0">
        <template #title>
          <div class="flex items-center gap-2">
            <span>{{ $t('borrower_waitlist_title') }}</span>
            <span class="text-xs text-surface-400 font-normal">{{ $t('borrower_waitlist_subtitle') }}</span>
          </div>
        </template>
        <template #content>
          <ul class="flex flex-col gap-2">
            <li v-for="entry in waitlist" :key="entry.id"
              class="flex items-center justify-between rounded-xl border border-surface-200 dark:border-zinc-700 px-4 py-3 text-sm">
              <div>
                <p class="font-semibold">{{ entry.car_name }}</p>
                <p class="text-xs text-surface-400 mt-0.5">
                  {{ formatDateTime(entry.start_datetime) }} – {{ formatDateTime(entry.end_datetime) }}
                </p>
              </div>
              <Button icon="pi pi-times" severity="danger" text rounded size="small"
                :title="$t('borrower_leave_waitlist_title')" @click="leaveWaitlist(entry.id)" />
            </li>
          </ul>
        </template>
      </Card>

      <!-- ── Past & cancelled ── -->
      <Card>
        <template #title>{{ $t('borrower_past_cancelled_title') }}</template>
        <template #content>
          <div v-if="history.length === 0" class="text-sm text-surface-500 py-4 text-center">
            {{ $t('borrower_no_past') }}
          </div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div v-for="booking in history" :key="booking.id"
              class="rounded-2xl border border-surface-200 dark:border-zinc-700 p-4 flex flex-col gap-1.5 opacity-70 hover:opacity-100 transition-all duration-200 cursor-pointer hover:shadow-sm"
              @click="router.push({ name: 'booking-detail', params: { id: booking.id } })">
              <div class="flex items-center justify-between gap-2">
                <span class="font-semibold text-sm truncate">{{ booking.car.name }}</span>
                <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
              </div>
              <p class="text-xs text-surface-400">{{ formatDateTime(booking.start_datetime) }}</p>
              <p v-if="booking.total_price != null" class="text-xs font-semibold text-primary">
                €{{ booking.total_price.toFixed(2) }}
              </p>
            </div>
          </div>
        </template>
      </Card>
    </template>
  </div>

  <RescheduleDialog v-model:visible="rescheduleVisible" :booking="rescheduleBooking" @rescheduled="fetchBookings" />
  </PullToRefresh>
</template>
