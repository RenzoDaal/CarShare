<script setup lang="ts">
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';

import { onMounted, ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import http from '@/api/http';
import type { Car } from '@/stores/cars';
import { useAuthStore } from '@/stores/auth';
import { useConfirm } from 'primevue/useconfirm';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';
import { useReveal } from '@/composables/useReveal';
import { haptic } from '@/utils/haptic';
import CarImageCarousel from '@/components/CarImageCarousel.vue';

const { t, locale } = useI18n();

const { el: bookingsEl, visible: bookingsVisible } = useReveal()
const { el: statsEl, visible: statsVisible } = useReveal()
const { el: carsEl, visible: carsVisible } = useReveal()
const { el: borrowerStatsEl, visible: borrowerStatsVisible } = useReveal()

const timeGreeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return t('dashboard_greeting_morning');
  if (h < 18) return t('dashboard_greeting_afternoon');
  return t('dashboard_greeting_evening');
});

const todayLabel = computed(() => {
  return new Date().toLocaleDateString(locale.value === 'nl' ? 'nl-NL' : 'en-GB', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
});

// Time-of-day ambient gradient — full class strings so Tailwind scans them statically
const GREETING_GRADIENTS = {
  morning:   'bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/10',
  afternoon: 'bg-gradient-to-br from-sky-50 to-blue-50 dark:from-sky-950/20 dark:to-blue-950/10',
  evening:   'bg-gradient-to-br from-indigo-50 to-violet-50 dark:from-indigo-950/20 dark:to-violet-950/10',
} as const;

const greetingGradientClass = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return GREETING_GRADIENTS.morning;
  if (h < 18) return GREETING_GRADIENTS.afternoon;
  return GREETING_GRADIENTS.evening;
});

type CarStats = {
  car_id: number;
  car_name: string;
  total_bookings: number;
  total_km: number;
  total_earnings: number;
};

type BorrowerStats = {
  total_rides: number;
  total_km: number;
  total_spent: number;
  favourite_car: string | null;
};

const router = useRouter();
const auth = useAuthStore();
const confirm = useConfirm();

type DashboardBooking = {
  id: number;
  car: Car;
  start_datetime: string;
  end_datetime: string;
  status: string;
  total_price?: number | null;
  borrower_name?: string | null;
  borrower_email?: string | null;
  notes?: string | null;
  created_at?: string | null;
  last_reminder_sent?: string | null;
};

type DashboardResponse = {
  upcoming_bookings: DashboardBooking[];
  active_cars: Car[];
  active_rentals: DashboardBooking[];
};

const loading = ref(true);
const error = ref<string | null>(null);
const data = ref<DashboardResponse>({
  upcoming_bookings: [],
  active_cars: [],
  active_rentals: [],
});

const isOwner = computed(() => auth.user?.role_owner ?? false);
const isBorrower = computed(() => auth.user?.role_borrower ?? false);

const pendingOwnerCount = ref(0);
async function loadPendingOwnerCount() {
  if (!auth.user?.role_owner) return;
  try {
    const { data } = await http.get<{ status: string }[]>('/bookings/owner');
    pendingOwnerCount.value = data.filter(b => b.status === 'pending').length;
  } catch {
    // silently ignore
  }
}

const activeBorrowerRental = computed<DashboardBooking | null>(() => {
  const now = new Date();
  return data.value.upcoming_bookings.find(b =>
    b.status === 'accepted' &&
    new Date(b.start_datetime + (b.start_datetime.endsWith('Z') ? '' : 'Z')) <= now &&
    new Date(b.end_datetime + (b.end_datetime.endsWith('Z') ? '' : 'Z')) >= now,
  ) ?? null;
});

const hasBookings = computed<boolean>(() => {
  return data.value.upcoming_bookings.length > 0;
});

const nextBooking = computed((): DashboardBooking | null => {
  return data.value.upcoming_bookings[0] ?? null;
});

const otherBookings = computed<DashboardBooking[]>(() => {
  return data.value.upcoming_bookings.slice(1);
});

// "Starts in X" countdown for the next booking
const timeUntilNextBooking = computed((): string | null => {
  if (!nextBooking.value) return null;
  const now = new Date();
  const startStr = nextBooking.value.start_datetime;
  const start = new Date(startStr + (startStr.endsWith('Z') ? '' : 'Z'));
  const diff = start.getTime() - now.getTime();
  if (diff <= 0) return null; // already started or in the past
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
});

const carStats = ref<CarStats[]>([]);
const borrowerStats = ref<BorrowerStats | null>(null);

const statEarningsDisplayed = ref<Record<number, number>>({})
watch([statsVisible, carStats], () => {
  if (!statsVisible.value) return
  carStats.value.forEach(stat => {
    const target = stat.total_earnings
    const start = performance.now()
    const tick = (now: number) => {
      const p = Math.min((now - start) / 900, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      statEarningsDisplayed.value[stat.car_id] = target * eased
      if (p < 1) requestAnimationFrame(tick)
      else statEarningsDisplayed.value[stat.car_id] = target
    }
    requestAnimationFrame(tick)
  })
}, { immediate: false })

type CoOwnerInvite = {
  car_id: number;
  car_name: string;
  owner_name: string;
  status: string;
};

const pendingInvites = ref<CoOwnerInvite[]>([]);

async function loadPendingInvites() {
  try {
    const res = await http.get<CoOwnerInvite[]>('/cars/co-owner-invites');
    pendingInvites.value = res.data;
  } catch {
    // silently ignore
  }
}

async function acceptInvite(carId: number) {
  const res = await http.post(`/cars/${carId}/co-owners/accept`);
  if (res.data?.user) auth.updateUser(res.data.user);
  await loadPendingInvites();
  await loadDashboard();
  await loadCarStats();
}

async function declineInvite(carId: number) {
  await http.post(`/cars/${carId}/co-owners/decline`);
  await loadPendingInvites();
}

async function loadCarStats() {
  if (!auth.user?.role_owner) return;
  try {
    const res = await http.get<CarStats[]>('/cars/stats');
    carStats.value = res.data;
  } catch {
    // silently ignore
  }
}

async function loadBorrowerStats() {
  if (!auth.user?.role_borrower) return;
  try {
    const res = await http.get<BorrowerStats>('/bookings/borrower/stats');
    borrowerStats.value = res.data;
  } catch {
    // silently ignore
  }
}

async function loadDashboard() {
  loading.value = true;
  error.value = null;
  try {
    const res = await http.get<DashboardResponse>('/dashboard');
    data.value = res.data;
  } catch (err: any) {
    console.error(err);
    error.value = err?.response?.data?.detail ?? t('dashboard_error_load');
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
        await loadDashboard();
      } catch (err: any) {
        error.value = err?.response?.data?.detail ?? t('dashboard_error_cancel');
      }
    },
  });
}

const reminderSending = ref<Set<number>>(new Set());

async function sendReminder(bookingId: number) {
  reminderSending.value = new Set(reminderSending.value).add(bookingId);
  try {
    const { data: res } = await http.post<{ ok: boolean; last_reminder_sent: string }>(`/bookings/${bookingId}/remind`);
    const booking = data.value.upcoming_bookings.find(b => b.id === bookingId);
    if (booking) booking.last_reminder_sent = res.last_reminder_sent;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? t('borrower_reminder_error');
  } finally {
    const next = new Set(reminderSending.value);
    next.delete(bookingId);
    reminderSending.value = next;
  }
}

function statusSeverity(status: string) {
  if (status === 'accepted') return 'success';
  if (status === 'pending') return 'warn';
  return 'danger';
}

onMounted(() => {
  loadDashboard();
  loadCarStats();
  loadBorrowerStats();
  loadPendingInvites();
  loadPendingOwnerCount();
});
</script>


<template>
  <div class="flex-1 flex justify-center w-full">
    <div class="w-full max-w-6xl px-4 py-6 space-y-5">

      <!-- Greeting header with time-of-day ambient band -->
      <div class="mb-4 -mx-4 px-4 py-5 rounded-2xl transition-colors duration-1000" :class="greetingGradientClass">
        <p class="text-sm font-medium text-surface-400 mb-0.5 capitalize">{{ timeGreeting }}, {{ todayLabel }}</p>
        <h1 class="text-3xl font-bold tracking-tight">{{ auth.user?.full_name?.split(' ')[0] }}</h1>
      </div>

      <!-- Error state -->
      <div v-if="error" class="p-3 rounded-xl bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300 text-sm">
        {{ error }}
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-5">
        <!-- Action cards skeleton -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div v-for="i in 4" :key="i" class="h-24 rounded-2xl bg-surface-200 dark:bg-zinc-800 animate-pulse" />
        </div>
        <!-- Main booking skeleton shaped like the next-booking hero card -->
        <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 overflow-hidden animate-pulse">
          <div class="p-5 space-y-3">
            <div class="flex items-center gap-2">
              <div class="h-3 w-3 rounded-full bg-primary/30" />
              <div class="h-3 bg-surface-200 dark:bg-zinc-700 rounded-full w-24" />
            </div>
            <div class="h-28 bg-surface-100 dark:bg-zinc-800 rounded-xl" />
            <div class="h-4 bg-surface-200 dark:bg-zinc-700 rounded-full w-1/2" />
            <div class="flex gap-2">
              <div class="h-8 w-20 bg-surface-200 dark:bg-zinc-700 rounded-xl" />
              <div class="h-8 w-20 bg-surface-200 dark:bg-zinc-700 rounded-xl" />
            </div>
          </div>
        </div>
      </div>

      <div v-else class="space-y-5">
        <!-- ── Quick action cards + Your bookings ── -->
        <div ref="bookingsEl"
          :class="['transition-all duration-700', bookingsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            <button
              class="group flex flex-col items-center justify-center gap-2.5 p-4 rounded-2xl bg-primary text-white hover:bg-primary/90 active:scale-95 transition-all duration-200 shadow-sm hover:shadow-md"
              @click="router.push({ name: 'reserve car' })"
            >
              <div class="w-11 h-11 rounded-xl bg-white/20 flex items-center justify-center group-hover:bg-white/30 transition-colors">
                <i class="pi pi-calendar text-xl" />
              </div>
              <span class="text-xs font-semibold text-center leading-tight">{{ $t('dashboard_reserve_car') }}</span>
            </button>

            <button v-if="isBorrower"
              class="group flex flex-col items-center justify-center gap-2.5 p-4 rounded-2xl bg-white dark:bg-zinc-800 border border-surface-200 dark:border-zinc-700 text-slate-700 dark:text-slate-200 hover:bg-surface-50 dark:hover:bg-zinc-700 shadow-sm active:scale-95 transition-all duration-200"
              @click="router.push({ name: 'borrowerappointments' })"
            >
              <div class="w-11 h-11 rounded-xl bg-surface-100 dark:bg-zinc-700 flex items-center justify-center group-hover:bg-surface-200 dark:group-hover:bg-zinc-600 transition-colors">
                <i class="pi pi-list text-xl text-surface-600" />
              </div>
              <span class="text-xs font-semibold text-center leading-tight">{{ $t('dashboard_my_appointments') }}</span>
            </button>

            <button v-if="isOwner"
              class="group flex flex-col items-center justify-center gap-2.5 p-4 rounded-2xl bg-white dark:bg-zinc-800 border border-surface-200 dark:border-zinc-700 text-slate-700 dark:text-slate-200 hover:bg-surface-50 dark:hover:bg-zinc-700 shadow-sm active:scale-95 transition-all duration-200 relative"
              @click="router.push({ name: 'ownerappointments' })"
            >
              <div class="relative">
                <div class="w-11 h-11 rounded-xl bg-surface-100 dark:bg-zinc-700 flex items-center justify-center group-hover:bg-surface-200 dark:group-hover:bg-zinc-600 transition-colors">
                  <i class="pi pi-inbox text-xl text-surface-600" />
                </div>
                <span v-if="pendingOwnerCount > 0"
                  class="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-white text-[10px] font-bold">
                  {{ pendingOwnerCount }}
                </span>
              </div>
              <span class="text-xs font-semibold text-center leading-tight">{{ $t('dashboard_booking_requests') }}</span>
            </button>

            <button v-if="isOwner"
              class="group flex flex-col items-center justify-center gap-2.5 p-4 rounded-2xl bg-white dark:bg-zinc-800 border border-surface-200 dark:border-zinc-700 text-slate-700 dark:text-slate-200 hover:bg-surface-50 dark:hover:bg-zinc-700 shadow-sm active:scale-95 transition-all duration-200"
              @click="router.push({ name: 'manage cars' })"
            >
              <div class="w-11 h-11 rounded-xl bg-surface-100 dark:bg-zinc-700 flex items-center justify-center group-hover:bg-surface-200 dark:group-hover:bg-zinc-600 transition-colors">
                <i class="pi pi-car text-xl text-surface-600" />
              </div>
              <span class="text-xs font-semibold text-center leading-tight">{{ $t('dashboard_manage_my_cars') }}</span>
            </button>
          </div>

          <!-- ── Your bookings ── -->
          <Card>
            <template #title>
              <div class="flex items-center justify-between gap-2">
                <span>{{ $t('dashboard_your_bookings') }}</span>
                <Tag v-if="hasBookings" :value="`${data?.upcoming_bookings.length} ${$t('dashboard_upcoming_count').replace('{count}', '')}`" />
                <Tag v-else :value="$t('dashboard_no_upcoming')" severity="info" />
              </div>
            </template>
            <template #content>
              <!-- Empty state -->
              <div v-if="!hasBookings" class="flex flex-col items-center gap-3 py-10 text-center">
                <div class="w-16 h-16 rounded-2xl bg-surface-100 dark:bg-zinc-800 flex items-center justify-center">
                  <i class="pi pi-calendar text-2xl text-surface-400" />
                </div>
                <div>
                  <p class="font-medium text-slate-600 dark:text-slate-300">{{ $t('dashboard_no_bookings_yet') }}</p>
                  <p class="text-sm text-surface-400 mt-1">{{ $t('dashboard_reserve_car') }}</p>
                </div>
                <Button :label="$t('dashboard_reserve_car')" icon="pi pi-calendar" size="small"
                  @click="router.push({ name: 'reserve car' })" />
              </div>

              <div v-else class="space-y-4">
                <!-- Next booking hero card -->
                <div v-if="nextBooking"
                  class="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/8 to-primary/3 dark:from-primary/15 dark:to-primary/5 p-5 relative overflow-hidden">
                  <div class="absolute top-0 left-0 w-1 h-full bg-primary rounded-l-2xl" />
                  <div class="pl-2">
                    <div class="flex items-center gap-2 mb-3">
                      <i class="pi pi-calendar-clock text-primary text-sm" />
                      <p class="text-xs font-semibold uppercase tracking-wider text-primary">
                        {{ $t('dashboard_next_booking') }}
                      </p>
                    </div>
                    <p class="font-bold text-lg mb-1 tracking-tight">{{ nextBooking.car.name }}</p>
                    <p class="text-sm text-surface-500 mb-1">
                      {{ formatDateTime(nextBooking.start_datetime) }} – {{ formatDateTime(nextBooking.end_datetime) }}
                    </p>
                    <p v-if="nextBooking.total_price != null" class="text-base font-bold text-primary mt-2">
                      € {{ nextBooking.total_price.toFixed(2) }}
                    </p>
                    <!-- Time until next booking countdown -->
                    <div v-if="timeUntilNextBooking" class="mt-1.5 flex items-center gap-1.5 text-xs text-surface-500">
                      <i class="pi pi-clock text-xs" />
                      <span>{{ $t('dashboard_starts_in') }} <span class="font-semibold text-primary">{{ timeUntilNextBooking }}</span></span>
                    </div>
                    <div class="mt-4 flex items-center gap-2 flex-wrap">
                      <Tag :value="nextBooking.status" :severity="statusSeverity(nextBooking.status)" />
                      <span v-if="nextBooking.status === 'pending'"
                        class="text-xs text-surface-400">{{ $t('dashboard_awaiting_owner_approval') }}</span>
                      <Button v-if="nextBooking.status === 'pending'" :label="$t('borrower_send_reminder')"
                        icon="pi pi-bell" severity="secondary" outlined size="small"
                        :loading="reminderSending.has(nextBooking.id)"
                        :disabled="reminderSending.has(nextBooking.id)"
                        @click="sendReminder(nextBooking.id)" />
                      <Button :label="$t('dashboard_cancel')" icon="pi pi-times" severity="danger" outlined size="small"
                        @click="confirmCancel(nextBooking.id)" />
                    </div>
                  </div>
                </div>

                <!-- Other bookings list with stagger + click-through -->
                <div v-if="otherBookings.length" class="space-y-2">
                  <p class="text-xs uppercase tracking-wider font-semibold text-surface-400">
                    {{ $t('dashboard_later_bookings') }}
                  </p>
                  <ul class="space-y-1.5">
                    <li v-for="(b, index) in otherBookings" :key="b.id"
                      class="list-item-stagger flex items-center justify-between text-sm border border-surface-100 dark:border-zinc-700 rounded-xl px-4 py-3 hover:bg-surface-50 dark:hover:bg-zinc-800 hover:border-surface-200 dark:hover:border-zinc-600 transition-all cursor-pointer"
                      :style="{ animationDelay: `${index * 60}ms` }"
                      @click="router.push({ name: 'booking-detail', params: { id: b.id } })">
                      <div>
                        <p class="font-semibold">{{ b.car.name }}</p>
                        <p class="text-xs text-surface-400 mt-0.5">{{ formatDateTime(b.start_datetime) }}</p>
                      </div>
                      <div class="flex items-center gap-2 flex-wrap justify-end" @click.stop>
                        <Tag :value="b.status" :severity="statusSeverity(b.status)" />
                        <Button v-if="b.status === 'pending'" icon="pi pi-bell" severity="secondary" outlined rounded
                          size="small" :loading="reminderSending.has(b.id)" :disabled="reminderSending.has(b.id)"
                          @click="sendReminder(b.id)" />
                        <Button icon="pi pi-times" severity="danger" outlined rounded size="small"
                          @click="confirmCancel(b.id)" />
                      </div>
                    </li>
                  </ul>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <!-- ── Borrower stats on dashboard ── -->
        <div v-if="isBorrower && borrowerStats && borrowerStats.total_rides > 0"
          ref="borrowerStatsEl"
          :class="['transition-all duration-700', borrowerStatsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
              <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
                <i class="pi pi-car text-primary text-base" />
              </div>
              <span class="text-2xl font-bold tracking-tight">{{ borrowerStats.total_rides }}</span>
              <span class="text-xs text-surface-400">{{ $t('borrower_stats_rides') }}</span>
            </div>
            <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
              <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
                <i class="pi pi-map-marker text-primary text-base" />
              </div>
              <span class="text-2xl font-bold tracking-tight">{{ borrowerStats.total_km.toFixed(0) }}</span>
              <span class="text-xs text-surface-400">{{ $t('borrower_stats_km') }}</span>
            </div>
            <div class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
              <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
                <i class="pi pi-wallet text-primary text-base" />
              </div>
              <span class="text-2xl font-bold tracking-tight">€{{ borrowerStats.total_spent.toFixed(2) }}</span>
              <span class="text-xs text-surface-400">{{ $t('borrower_stats_spent') }}</span>
            </div>
            <div v-if="borrowerStats.favourite_car"
              class="rounded-2xl border border-surface-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 flex flex-col gap-1.5 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
              <div class="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mb-0.5">
                <i class="pi pi-heart text-primary text-base" />
              </div>
              <span class="text-base font-bold truncate leading-tight">{{ borrowerStats.favourite_car }}</span>
              <span class="text-xs text-surface-400">{{ $t('borrower_stats_favourite') }}</span>
            </div>
          </div>
        </div>

        <!-- ── Co-owner invites ── -->
        <div v-if="pendingInvites.length > 0">
          <Card>
            <template #title>
              <div class="flex items-center gap-2">
                <span>{{ $t('dashboard_pending_invites_title') }}</span>
                <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-white text-xs font-bold">
                  {{ pendingInvites.length }}
                </span>
              </div>
            </template>
            <template #content>
              <div class="flex flex-col gap-3">
                <div v-for="invite in pendingInvites" :key="invite.car_id"
                  class="border border-surface-200 dark:border-zinc-700 rounded-xl p-4 flex items-center justify-between gap-3">
                  <div>
                    <p class="font-semibold text-sm">{{ invite.car_name }}</p>
                    <p class="text-xs text-surface-500 mt-0.5">
                      {{ invite.owner_name }} {{ $t('dashboard_pending_invite_from') }} {{ invite.car_name }}
                    </p>
                  </div>
                  <div class="flex gap-2 shrink-0">
                    <Button :label="$t('dashboard_accept_invite')" icon="pi pi-check" size="small" severity="success"
                      @click="acceptInvite(invite.car_id)" />
                    <Button :label="$t('dashboard_decline_invite')" icon="pi pi-times" size="small" severity="danger"
                      outlined @click="declineInvite(invite.car_id)" />
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <!-- ── Borrower: currently using a car ── -->
        <div v-if="isBorrower && activeBorrowerRental">
          <Card>
            <template #title>
              <div class="flex items-center gap-2">
                <span>{{ $t('dashboard_currently_using') }}</span>
                <span class="relative flex h-2.5 w-2.5">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
                </span>
              </div>
            </template>
            <template #content>
              <!-- Pulsing glow border to convey live state -->
              <div class="rental-card-live border border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10 rounded-2xl p-4 flex flex-col gap-1.5 cursor-pointer"
                @click="router.push({ name: 'booking-detail', params: { id: activeBorrowerRental!.id } })">
                <div class="flex items-center justify-between">
                  <span class="font-bold">{{ activeBorrowerRental!.car.name }}</span>
                  <Tag :value="$t('dashboard_active')" severity="success" />
                </div>
                <p class="text-sm text-surface-500">
                  {{ formatDateTime(activeBorrowerRental!.start_datetime) }} – {{ formatDateTime(activeBorrowerRental!.end_datetime) }}
                </p>
                <p v-if="activeBorrowerRental!.total_price != null" class="text-sm font-semibold text-primary">
                  €{{ activeBorrowerRental!.total_price.toFixed(2) }}
                </p>
              </div>
            </template>
          </Card>
        </div>

        <!-- ── Active rentals (owner view) ── -->
        <div v-if="isOwner && data.active_rentals.length > 0">
          <Card>
            <template #title>
              <div class="flex items-center gap-2">
                <span>{{ $t('dashboard_currently_in_use') }}</span>
                <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-500 text-white text-xs font-bold">
                  {{ data.active_rentals.length }}
                </span>
              </div>
            </template>
            <template #content>
              <div class="flex flex-col gap-3">
                <div v-for="rental in data.active_rentals" :key="rental.id"
                  class="border border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10 rounded-2xl p-4 flex flex-col gap-1.5">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2.5">
                      <span class="relative flex h-2.5 w-2.5">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
                      </span>
                      <span class="font-bold">{{ rental.car.name }}</span>
                    </div>
                    <Tag :value="$t('dashboard_active')" severity="success" />
                  </div>
                  <p class="text-sm text-surface-500">
                    {{ formatDateTime(rental.start_datetime) }} – {{ formatDateTime(rental.end_datetime) }}
                  </p>
                  <p v-if="rental.borrower_name" class="text-sm">
                    {{ $t('dashboard_borrower') }}
                    <span class="font-semibold">{{ rental.borrower_name }}</span>
                    <span v-if="rental.borrower_email" class="text-surface-400"> — {{ rental.borrower_email }}</span>
                  </p>
                  <p v-if="rental.notes" class="text-sm italic text-surface-400">"{{ rental.notes }}"</p>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <!-- ── Usage stats (owner) ── -->
        <div v-if="isOwner && carStats.length > 0" ref="statsEl"
          :class="['transition-all duration-700', statsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">
          <Card>
            <template #title>{{ $t('dashboard_usage_stats') }}</template>
            <template #content>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <div v-for="(stat, index) in carStats" :key="stat.car_id"
                  class="card-animate rounded-2xl border border-surface-200 dark:border-zinc-700 p-5 flex flex-col gap-2 hover:shadow-md transition-all duration-200 bg-gradient-to-br from-surface-0 to-surface-50 dark:from-zinc-800 dark:to-zinc-900 hover:-translate-y-0.5"
                  :style="{ animationDelay: `${index * 80}ms` }">
                  <p class="font-semibold text-sm text-slate-600 dark:text-slate-300 truncate">{{ stat.car_name }}</p>
                  <p class="text-3xl font-bold text-primary tracking-tight">
                    €{{ (statEarningsDisplayed[stat.car_id] ?? 0).toFixed(2) }}
                  </p>
                  <div class="flex items-center gap-4 text-xs text-surface-500 mt-0.5">
                    <span class="flex items-center gap-1.5">
                      <i class="pi pi-check-circle text-green-500" />
                      {{ stat.total_bookings }}
                      {{ stat.total_bookings !== 1 ? $t('dashboard_bookings_accepted_plural') : $t('dashboard_bookings_accepted') }}
                    </span>
                    <span class="flex items-center gap-1.5">
                      <i class="pi pi-map-marker text-primary" />
                      {{ stat.total_km.toFixed(0) }} {{ $t('dashboard_km_total') }}
                    </span>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <!-- ── Your cars (owner) ── -->
        <div v-if="isOwner" ref="carsEl"
          :class="['transition-all duration-700', carsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">
          <Card>
            <template #title>
              <div class="flex items-center justify-between gap-2">
                <span>{{ $t('dashboard_your_cars') }}</span>
                <Button :label="$t('dashboard_manage_cars')" icon="pi pi-car" size="small" severity="secondary"
                  @click="router.push({ name: 'manage cars' })" />
              </div>
            </template>
            <template #content>
              <div v-if="!data?.active_cars?.length" class="flex flex-col items-center gap-3 py-10 text-center">
                <div class="w-16 h-16 rounded-2xl bg-surface-100 dark:bg-zinc-800 flex items-center justify-center">
                  <i class="pi pi-car text-2xl text-surface-400" />
                </div>
                <p class="text-sm text-surface-500">{{ $t('dashboard_no_cars_yet') }}</p>
                <Button :label="$t('dashboard_manage_cars')" icon="pi pi-car" size="small" severity="secondary"
                  @click="router.push({ name: 'manage cars' })" />
              </div>

              <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div v-for="(car, index) in data.active_cars" :key="car.id"
                  class="relative h-64 rounded-2xl overflow-hidden cursor-pointer shadow-sm hover:-translate-y-1.5 hover:shadow-xl transition-all duration-300 card-animate"
                  :style="{ animationDelay: `${index * 60}ms` }"
                  @click="router.push({ name: 'manage cars' })">
                  <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
                  <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent pointer-events-none" />
                  <div class="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
                    <div class="flex items-center justify-between gap-2">
                      <p class="text-white font-bold text-sm leading-tight truncate">{{ car.name }}</p>
                      <Tag :value="car.is_active ? $t('dashboard_active_tag') : $t('dashboard_disabled_tag')"
                        :severity="car.is_active ? 'success' : 'danger'" />
                    </div>
                    <p class="text-white/65 text-xs mt-0.5">€ {{ car.price_per_km.toFixed(2) }} / km</p>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card-animate {
  animation: cardFadeIn 0.35s ease forwards;
  opacity: 0;
}
@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Stagger fade-in for booking list items */
.list-item-stagger {
  animation: cardFadeIn 0.3s ease forwards;
  opacity: 0;
}

/* Pulsing green glow for the active rental card */
.rental-card-live {
  animation: rentalGlow 2.5s ease-in-out infinite;
}
@keyframes rentalGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
  50% { box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.12); }
}
</style>
