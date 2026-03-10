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
import CarImageCarousel from '@/components/CarImageCarousel.vue';

const { t } = useI18n();

const { el: bookingsEl, visible: bookingsVisible } = useReveal()
const { el: statsEl, visible: statsVisible } = useReveal()
const { el: carsEl, visible: carsVisible } = useReveal()

const timeGreeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return t('dashboard_greeting_morning');
  if (h < 18) return t('dashboard_greeting_afternoon');
  return t('dashboard_greeting_evening');
});

type CarStats = {
  car_id: number;
  car_name: string;
  total_bookings: number;
  total_km: number;
  total_earnings: number;
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

const hasBookings = computed<boolean>(() => {
  const value = data.value;
  if (!value) return false;
  return value.upcoming_bookings.length > 0;
});



const nextBooking = computed((): DashboardBooking | null => {
  const value = data.value;

  if (value.upcoming_bookings.length === 0) {
    return null;
  }

  return value.upcoming_bookings[0]!;
});



const otherBookings = computed<DashboardBooking[]>(() => {
  const value = data.value;
  if (!value || value.upcoming_bookings.length <= 1) {
    return [];
  }
  return value.upcoming_bookings.slice(1);
});

const carStats = ref<CarStats[]>([]);

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
  if (res.data?.user) {
    auth.updateUser(res.data.user);
  }
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
    // silently ignore stats failure
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
  confirm.require({
    message: t('borrower_confirm_cancel_message'),
    header: t('borrower_confirm_cancel_header'),
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: t('borrower_confirm_keep'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('borrower_confirm_cancel_button'), severity: 'danger' },
    accept: async () => {
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

function goToReserve() {
  router.push({ name: 'reserve car' });
}

function goToManageCars() {
  router.push({ name: 'manage cars' });
}

onMounted(() => {
  loadDashboard();
  loadCarStats();
  loadPendingInvites();
  loadPendingOwnerCount();
});
</script>


<template>
  <div class="flex-1 flex justify-center w-full">
    <div class="w-full max-w-6xl px-4 py-6 space-y-4">
      <div class="mb-6">
        <p class="text-sm font-medium text-surface-400 mb-0.5">{{ timeGreeting }}</p>
        <h1 class="text-3xl font-bold tracking-tight">{{ auth.user?.full_name?.split(' ')[0] }}</h1>
      </div>

      <div v-if="error" class="p-3 rounded-xl bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300 text-sm">
        {{ error }}
      </div>

      <div v-if="loading" class="space-y-4">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div class="lg:col-span-2 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden animate-pulse">
            <div class="p-5 space-y-3">
              <div class="h-4 bg-surface-200 dark:bg-surface-700 rounded-full w-1/3" />
              <div class="h-28 bg-surface-100 dark:bg-surface-800 rounded-xl" />
              <div class="h-4 bg-surface-200 dark:bg-surface-700 rounded-full w-1/2" />
            </div>
          </div>
          <div class="rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden animate-pulse">
            <div class="p-5 space-y-3">
              <div class="h-4 bg-surface-200 dark:bg-surface-700 rounded-full w-1/2" />
              <div class="h-10 bg-surface-100 dark:bg-surface-800 rounded-xl" />
              <div class="h-10 bg-surface-100 dark:bg-surface-800 rounded-xl" />
            </div>
          </div>
        </div>
      </div>

      <div v-else class="space-y-4">
        <div ref="bookingsEl"
          :class="['transition-all duration-700 space-y-4', bookingsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">

          <!-- Quick actions row -->
          <div class="flex flex-wrap gap-2">
            <Button :label="$t('dashboard_reserve_car')" icon="pi pi-calendar" @click="goToReserve" />
            <Button v-if="isBorrower" :label="$t('dashboard_my_appointments')" icon="pi pi-list" severity="secondary"
              @click="router.push({ name: 'borrowerappointments' })" />
            <Button v-if="isOwner" :label="$t('dashboard_booking_requests')" icon="pi pi-inbox" severity="secondary"
              :badge="pendingOwnerCount > 0 ? String(pendingOwnerCount) : undefined" badge-severity="warn"
              @click="router.push({ name: 'ownerappointments' })" />
            <Button v-if="isOwner" :label="$t('dashboard_manage_my_cars')" icon="pi pi-car" severity="secondary"
              @click="goToManageCars" />
          </div>

          <Card>
              <template #title>
                <div class="flex items-center justify-between gap-2">
                  <span>{{ $t('dashboard_your_bookings') }}</span>
                  <Tag v-if="hasBookings" :value="`${data?.upcoming_bookings.length} ${$t('dashboard_upcoming_count').replace('{count}', '')}`" />
                  <Tag v-else :value="$t('dashboard_no_upcoming')" severity="info" />
                </div>
              </template>
              <template #content>
                <div v-if="!hasBookings" class="flex flex-col items-center gap-3 py-8 text-center">
                  <div class="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                    <i class="pi pi-calendar text-2xl text-surface-400" />
                  </div>
                  <div>
                    <p class="font-medium text-surface-600 dark:text-surface-300">{{ $t('dashboard_no_bookings_yet') }}</p>
                    <p class="text-sm text-surface-400 mt-1">{{ $t('dashboard_reserve_car') }}</p>
                  </div>
                  <Button :label="$t('dashboard_reserve_car')" icon="pi pi-calendar" size="small" @click="goToReserve" />
                </div>

                <div v-else class="space-y-4">
                  <div v-if="nextBooking" class="rounded-xl border border-primary/20 bg-gradient-to-r from-primary/8 to-primary/3 dark:from-primary/15 dark:to-primary/5 p-4 relative overflow-hidden">
                    <div class="absolute top-0 left-0 w-1 h-full bg-primary rounded-l-xl"></div>
                    <div class="pl-1">
                      <div class="flex items-center gap-2 mb-2">
                        <i class="pi pi-calendar-clock text-primary text-sm" />
                        <p class="text-xs font-semibold uppercase tracking-wide text-primary">
                          {{ $t('dashboard_next_booking') }}
                        </p>
                      </div>
                      <p class="font-semibold text-base mb-0.5">
                        {{ nextBooking!.car.name }}
                      </p>
                      <p class="text-sm text-surface-500">
                        {{ formatDateTime(nextBooking!.start_datetime) }}
                        –
                        {{ formatDateTime(nextBooking!.end_datetime) }}
                      </p>
                      <p v-if="nextBooking!.total_price != null" class="text-sm mt-1.5 font-semibold text-primary">
                        € {{ nextBooking!.total_price!.toFixed(2) }}
                      </p>
                      <div class="mt-3 flex items-center gap-3 flex-wrap">
                        <Tag :value="nextBooking!.status" />
                        <span v-if="nextBooking!.status === 'pending'" class="text-xs text-surface-400">{{ $t('dashboard_awaiting_owner_approval') }}</span>
                        <Button v-if="nextBooking!.status === 'pending'" :label="$t('borrower_send_reminder')" icon="pi pi-bell"
                          severity="secondary" outlined size="small"
                          :loading="reminderSending.has(nextBooking!.id)"
                          :disabled="reminderSending.has(nextBooking!.id)"
                          @click="sendReminder(nextBooking!.id)" />
                        <Button :label="$t('dashboard_cancel')" icon="pi pi-times" severity="danger" outlined size="small"
                          @click="confirmCancel(nextBooking!.id)" />
                      </div>
                    </div>
                  </div>

                  <div v-if="otherBookings.length" class="space-y-2">
                    <p class="text-xs uppercase tracking-wide text-surface-500">
                      {{ $t('dashboard_later_bookings') }}
                    </p>
                    <ul class="space-y-2">
                      <li v-for="b in otherBookings" :key="b.id"
                        class="flex items-center justify-between text-sm border border-surface-100 dark:border-surface-700 rounded-lg px-3 py-2 hover:bg-surface-50 dark:hover:bg-surface-800 transition-colors cursor-default">
                        <div>
                          <p class="font-medium">
                            {{ b.car.name }}
                          </p>
                          <p class="text-xs text-surface-500">
                            {{ formatDateTime(b.start_datetime) }}
                          </p>
                        </div>
                        <div class="flex flex-col items-end gap-1">
                          <div class="flex items-center gap-2 flex-wrap justify-end">
                            <Tag :value="b.status" />
                            <Button v-if="b.status === 'pending'" icon="pi pi-bell" severity="secondary" outlined rounded size="small"
                              :loading="reminderSending.has(b.id)"
                              :disabled="reminderSending.has(b.id)"
                              @click="sendReminder(b.id)" />
                            <Button icon="pi pi-times" severity="danger" outlined rounded size="small"
                              @click="confirmCancel(b.id)" />
                          </div>
                        </div>
                      </li>
                    </ul>
                  </div>
                </div>
              </template>
            </Card>
        </div>

        <div v-if="pendingInvites.length > 0">
          <Card class="mb-4">
            <template #title>
              <div class="flex items-center gap-2">
                <span>{{ $t('dashboard_pending_invites_title') }}</span>
                <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-white text-xs font-bold">{{ pendingInvites.length }}</span>
              </div>
            </template>
            <template #content>
              <div class="flex flex-col gap-3">
                <div v-for="invite in pendingInvites" :key="invite.car_id"
                  class="border border-surface-200 dark:border-surface-700 rounded-lg p-3 flex items-center justify-between gap-3">
                  <div>
                    <p class="font-medium text-sm">{{ invite.car_name }}</p>
                    <p class="text-xs text-surface-500">{{ invite.owner_name }} {{ $t('dashboard_pending_invite_from') }} {{ invite.car_name }}</p>
                  </div>
                  <div class="flex gap-2">
                    <Button :label="$t('dashboard_accept_invite')" icon="pi pi-check" size="small" severity="success" @click="acceptInvite(invite.car_id)" />
                    <Button :label="$t('dashboard_decline_invite')" icon="pi pi-times" size="small" severity="danger" outlined @click="declineInvite(invite.car_id)" />
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <div v-if="isOwner && data.active_rentals.length > 0">
          <Card class="mb-4">
            <template #title>
              <div class="flex items-center gap-2">
                <span>{{ $t('dashboard_currently_in_use') }}</span>
                <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-500 text-white text-xs font-bold">{{ data.active_rentals.length }}</span>
              </div>
            </template>
            <template #content>
              <div class="flex flex-col gap-3">
                <div v-for="rental in data.active_rentals" :key="rental.id"
                  class="border border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10 rounded-xl p-4 flex flex-col gap-1">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="relative flex h-2 w-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                      </span>
                      <span class="font-semibold">{{ rental.car.name }}</span>
                    </div>
                    <Tag :value="$t('dashboard_active')" severity="success" />
                  </div>
                  <p class="text-sm text-surface-500">
                    {{ formatDateTime(rental.start_datetime) }} – {{ formatDateTime(rental.end_datetime) }}
                  </p>
                  <p v-if="rental.borrower_name" class="text-sm">
                    {{ $t('dashboard_borrower') }} <span class="font-medium">{{ rental.borrower_name }}</span>
                    <span v-if="rental.borrower_email" class="text-surface-400"> — {{ rental.borrower_email }}</span>
                  </p>
                  <p v-if="rental.notes" class="text-sm italic text-surface-400">"{{ rental.notes }}"</p>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <div v-if="isOwner && carStats.length > 0" ref="statsEl"
          :class="['transition-all duration-700', statsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">
          <Card class="mb-4">
            <template #title>{{ $t('dashboard_usage_stats') }}</template>
            <template #content>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <div v-for="stat in carStats" :key="stat.car_id"
                  class="rounded-xl border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-2 hover:shadow-md transition-shadow bg-gradient-to-br from-surface-0 to-surface-50 dark:from-surface-800 dark:to-surface-900">
                  <p class="font-semibold text-sm text-surface-700 dark:text-surface-200">{{ stat.car_name }}</p>
                  <p class="text-2xl font-bold text-primary">€{{ (statEarningsDisplayed[stat.car_id] ?? 0).toFixed(2) }}</p>
                  <div class="flex items-center gap-4 text-xs text-surface-500">
                    <span class="flex items-center gap-1">
                      <i class="pi pi-check-circle" />
                      {{ stat.total_bookings }} {{ stat.total_bookings !== 1 ? $t('dashboard_bookings_accepted_plural') : $t('dashboard_bookings_accepted') }}
                    </span>
                    <span class="flex items-center gap-1">
                      <i class="pi pi-map-marker" />
                      {{ stat.total_km.toFixed(0) }} {{ $t('dashboard_km_total') }}
                    </span>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <div v-if="isOwner" ref="carsEl"
          :class="['transition-all duration-700', carsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5']">
          <Card>
            <template #title>
              <div class="flex items-center justify-between gap-2">
                <span>{{ $t('dashboard_your_cars') }}</span>
                <Button :label="$t('dashboard_manage_cars')" icon="pi pi-car" size="small" severity="secondary"
                  @click="goToManageCars" />
              </div>
            </template>
            <template #content>
              <div v-if="!data?.active_cars?.length" class="flex flex-col items-center gap-3 py-8 text-center">
                <div class="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                  <i class="pi pi-car text-2xl text-surface-400" />
                </div>
                <p class="text-sm text-surface-500">{{ $t('dashboard_no_cars_yet') }}</p>
                <Button :label="$t('dashboard_manage_cars')" icon="pi pi-car" size="small" severity="secondary" @click="goToManageCars" />
              </div>

              <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <div v-for="(car, index) in data!.active_cars" :key="car.id"
                  class="relative h-80 rounded-xl overflow-hidden cursor-pointer shadow hover:-translate-y-1 hover:shadow-lg transition-all duration-300 card-animate border border-surface-200 dark:border-surface-700"
                  :style="{ animationDelay: `${index * 60}ms` }"
                  @click="goToManageCars">
                  <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
                  <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent pointer-events-none" />
                  <div class="absolute bottom-0 left-0 right-0 p-3 pointer-events-none">
                    <div class="flex items-center justify-between gap-2">
                      <p class="text-white font-semibold text-sm leading-tight truncate">{{ car.name }}</p>
                      <Tag :value="car.is_active ? $t('dashboard_active_tag') : $t('dashboard_disabled_tag')"
                        :severity="car.is_active ? 'success' : 'danger'" />
                    </div>
                    <p class="text-white/70 text-xs mt-0.5">€ {{ car.price_per_km.toFixed(2) }} / km</p>
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
</style>
