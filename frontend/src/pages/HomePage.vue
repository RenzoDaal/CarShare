<script setup lang="ts">
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';

import { onMounted, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import http from '@/api/http';
import type { Car } from '@/stores/cars';
import { useAuthStore } from '@/stores/auth';
import { useConfirm } from 'primevue/useconfirm';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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
});
</script>


<template>
  <div class="flex-1 flex justify-center w-full">
    <div class="w-full max-w-6xl px-4 py-6 space-y-4">
      <h1 class="text-2xl font-semibold mb-2">{{ $t('dashboard_title') }}</h1>

      <div v-if="error" class="p-3 rounded bg-red-100 text-red-800 text-sm">
        {{ error }}
      </div>

      <div v-if="loading">
        <Card class="mb-4">
          <template #title>
            <span>{{ $t('dashboard_loading_title') }}</span>
          </template>
          <template #content>
            <p class="text-sm text-surface-500">
              {{ $t('dashboard_loading_description') }}
            </p>
          </template>
        </Card>
      </div>

      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
          <div class="lg:col-span-2 h-full">
            <Card class="h-full">
              <template #title>
                <div class="flex items-center justify-between gap-2">
                  <span>{{ $t('dashboard_your_bookings') }}</span>
                  <Tag v-if="hasBookings" :value="`${data?.upcoming_bookings.length} ${$t('dashboard_upcoming_count').replace('{count}', '')}`" />
                  <Tag v-else :value="$t('dashboard_no_upcoming')" severity="info" />
                </div>
              </template>
              <template #content>
                <div v-if="!hasBookings" class="text-sm text-surface-500">
                  {{ $t('dashboard_no_bookings_yet') }}
                  <Button :label="$t('dashboard_reserve_car')" icon="pi pi-calendar" size="small" class="mt-3" @click="goToReserve" />
                </div>

                <div v-else class="space-y-4">
                  <div v-if="nextBooking" class="rounded-lg border border-surface-200 p-3">
                    <p class="text-xs uppercase tracking-wide text-surface-500 mb-1">
                      {{ $t('dashboard_next_booking') }}
                    </p>
                    <p class="font-medium">
                      {{ nextBooking!.car.name }}
                    </p>
                    <p class="text-sm text-surface-500">
                      {{ formatDateTime(nextBooking!.start_datetime) }}
                      -
                      {{ formatDateTime(nextBooking!.end_datetime) }}
                    </p>
                    <p v-if="nextBooking!.total_price != null" class="text-sm mt-1">
                      {{ $t('dashboard_estimated_price') }}
                      <span class="font-semibold">
                        € {{ nextBooking!.total_price!.toFixed(2) }}
                      </span>
                    </p>
                    <div class="mt-2 flex items-center gap-3 flex-wrap">
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

                  <div v-if="otherBookings.length" class="space-y-2">
                    <p class="text-xs uppercase tracking-wide text-surface-500">
                      {{ $t('dashboard_later_bookings') }}
                    </p>
                    <ul class="space-y-2">
                      <li v-for="b in otherBookings" :key="b.id"
                        class="flex items-center justify-between text-sm border border-surface-100 rounded px-2 py-1">
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

          <div class="lg:col-span-1 flex">
            <Card class="flex-1 h-full flex flex-col">
              <template #title>
                <span>{{ $t('dashboard_quick_actions') }}</span>
              </template>
              <template #content>
                <div class="flex-1 flex flex-col gap-2">
                  <Button :label="$t('dashboard_reserve_car')" icon="pi pi-calendar" @click="goToReserve" />
                  <Button v-if="isOwner" :label="$t('dashboard_manage_my_cars')" icon="pi pi-car" severity="secondary"
                    @click="goToManageCars" />
                </div>
              </template>
            </Card>
          </div>
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
                  class="border border-green-200 dark:border-green-800 rounded-lg p-3 flex flex-col gap-1">
                  <div class="flex items-center justify-between">
                    <span class="font-semibold">{{ rental.car.name }}</span>
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

        <div v-if="isOwner && carStats.length > 0">
          <Card class="mb-4">
            <template #title>{{ $t('dashboard_usage_stats') }}</template>
            <template #content>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <div v-for="stat in carStats" :key="stat.car_id"
                  class="border rounded-lg p-3 flex flex-col gap-1">
                  <p class="font-semibold text-sm">{{ stat.car_name }}</p>
                  <p class="text-xs text-surface-500">{{ stat.total_bookings }} {{ stat.total_bookings !== 1 ? $t('dashboard_bookings_accepted_plural') : $t('dashboard_bookings_accepted') }}</p>
                  <p class="text-xs text-surface-500">{{ stat.total_km.toFixed(0) }} {{ $t('dashboard_km_total') }}</p>
                  <p class="text-sm font-medium mt-1">€{{ stat.total_earnings.toFixed(2) }} {{ $t('dashboard_earned') }}</p>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <div v-if="isOwner">
          <Card>
            <template #title>
              <div class="flex items-center justify-between gap-2">
                <span>{{ $t('dashboard_your_cars') }}</span>
                <Button :label="$t('dashboard_manage_cars')" icon="pi pi-car" size="small" severity="secondary"
                  @click="goToManageCars" />
              </div>
            </template>
            <template #content>
              <div v-if="!data?.active_cars?.length" class="text-sm text-surface-500">
                {{ $t('dashboard_no_cars_yet') }}
                <span class="block mt-1">
                  {{ $t('dashboard_no_cars_hint').replace('{bold}', '') }}<b>{{ $t('dashboard_manage_cars_bold') }}</b>{{ $t('dashboard_no_cars_hint').split('{bold}')[1] ?? '' }}
                </span>
              </div>

              <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <Card v-for="car in data!.active_cars" :key="car.id" class="border border-surface-200 rounded-lg">
                  <template #title>
                    <div class="flex items-center justify-between gap-2">
                      <span>{{ car.name }}</span>
                      <Tag :value="car.is_active ? $t('dashboard_active_tag') : $t('dashboard_disabled_tag')"
                        :severity="car.is_active ? 'success' : 'danger'" />
                    </div>
                  </template>
                  <template #content>
                    <p class="text-sm text-surface-500 mb-1">
                      {{ car.description || $t('dashboard_no_description') }}
                    </p>
                    <p class="text-sm">
                      € {{ car.price_per_km.toFixed(2) }} / km
                    </p>
                  </template>
                </Card>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>
