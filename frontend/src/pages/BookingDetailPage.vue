<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import ProgressSpinner from 'primevue/progressspinner';
import { useConfirm } from 'primevue/useconfirm';
import { useAuthStore } from '@/stores/auth';
import CarImageCarousel from '@/components/CarImageCarousel.vue';
import RescheduleDialog from '@/components/RescheduleDialog.vue';
import http from '@/api/http';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

type Booking = {
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
  status: string;
  total_price?: number | null;
  borrower_name?: string | null;
  borrower_email?: string | null;
  stops?: string[] | null;
  notes?: string | null;
};

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const confirm = useConfirm();

const booking = ref<Booking | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const rescheduleVisible = ref(false);

const isOwnerView = computed(() => auth.user?.id === booking.value?.car.owner_id);

onMounted(async () => {
  try {
    const { data } = await http.get<Booking>(`/bookings/${route.params.id}/detail`);
    booking.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? t('booking_detail_error_load');
  } finally {
    loading.value = false;
  }
});

function toUtcDate(iso: string): Date {
  const normalized = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z';
  return new Date(normalized);
}

function formatDuration(start: string, end: string): string {
  const diffMs = toUtcDate(end).getTime() - toUtcDate(start).getTime();
  const totalHours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  if (days > 0 && hours > 0) return `${days}d ${hours}h`;
  if (days > 0) return `${days} day${days !== 1 ? 's' : ''}`;
  return `${totalHours} hour${totalHours !== 1 ? 's' : ''}`;
}

function statusSeverity(status: string) {
  if (status === 'accepted') return 'success';
  if (status === 'pending') return 'warn';
  if (status === 'declined') return 'danger';
  return 'secondary';
}

function statusLabel(status: string): string {
  if (status === 'pending') return t('booking_detail_status_awaiting');
  if (status === 'accepted') return t('booking_detail_status_confirmed');
  if (status === 'declined') return t('booking_detail_status_declined');
  if (status === 'cancelled') return t('booking_detail_status_cancelled');
  return '';
}

function confirmCancel() {
  if (!booking.value) return;
  confirm.require({
    message: t('booking_detail_confirm_cancel_message'),
    header: t('booking_detail_confirm_cancel_header'),
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: t('booking_detail_keep_booking'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('booking_detail_confirm_cancel_button'), severity: 'danger' },
    accept: async () => {
      try {
        await http.post(`/bookings/${booking.value!.id}/cancel`);
        booking.value!.status = 'cancelled';
      } catch (err: any) {
        error.value = err?.response?.data?.detail ?? t('booking_detail_error_cancel');
      }
    },
  });
}

async function acceptBooking() {
  if (!booking.value) return;
  await http.post(`/bookings/${booking.value.id}/accept`);
  booking.value.status = 'accepted';
}

async function declineBooking() {
  if (!booking.value) return;
  await http.post(`/bookings/${booking.value.id}/decline`);
  booking.value.status = 'declined';
}
</script>

<template>
  <div class="p-4 max-w-2xl mx-auto w-full flex flex-col gap-6">
    <div class="flex items-center gap-3">
      <Button icon="pi pi-arrow-left" severity="secondary" text rounded @click="router.back()" />
      <h1 class="text-2xl font-semibold">{{ $t('booking_detail_title') }}</h1>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <ProgressSpinner />
    </div>

    <div v-else-if="error" class="p-3 rounded bg-red-100 text-red-800 text-sm">{{ error }}</div>

    <template v-else-if="booking">
      <!-- Status banner -->
      <div class="flex items-center gap-3 p-4 rounded-xl border-l-4"
        :class="{
          'border-l-green-500 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800': booking.status === 'accepted',
          'border-l-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800': booking.status === 'pending',
          'border-l-red-500 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800': booking.status === 'declined' || booking.status === 'cancelled',
        }">
        <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
        <span class="text-sm font-medium">{{ statusLabel(booking.status) }}</span>
      </div>

      <!-- Car -->
      <Card class="overflow-hidden">
        <template #header>
          <div class="h-56 w-full">
            <CarImageCarousel :car-id="booking.car.id" :fallback-url="booking.car.image_url" />
          </div>
        </template>
        <template #title>{{ booking.car.name }}</template>
        <template #content>
          <p v-if="booking.car.description" class="text-sm text-surface-500 mb-1">
            {{ booking.car.description }}
          </p>
          <p class="text-sm">{{ booking.car.price_per_km }} € / km</p>
        </template>
      </Card>

      <!-- Booking details -->
      <Card>
        <template #title>{{ $t('booking_detail_details') }}</template>
        <template #content>
          <div class="rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden text-sm divide-y divide-surface-100 dark:divide-surface-700">
            <div class="flex justify-between items-center px-4 py-3 bg-surface-50 dark:bg-surface-800/50">
              <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-calendar" />{{ $t('booking_detail_start') }}</span>
              <span class="font-medium">{{ formatDateTime(booking.start_datetime) }}</span>
            </div>
            <div class="flex justify-between items-center px-4 py-3">
              <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-calendar-clock" />{{ $t('booking_detail_end') }}</span>
              <span class="font-medium">{{ formatDateTime(booking.end_datetime) }}</span>
            </div>
            <div class="flex justify-between items-center px-4 py-3 bg-surface-50 dark:bg-surface-800/50">
              <span class="flex items-center gap-2 text-surface-500"><i class="pi pi-clock" />{{ $t('booking_detail_duration') }}</span>
              <span class="font-medium">{{ formatDuration(booking.start_datetime, booking.end_datetime) }}</span>
            </div>
            <div v-if="booking.total_price != null" class="flex justify-between items-center px-4 py-3.5 bg-primary/5 dark:bg-primary/10">
              <span class="flex items-center gap-2 font-semibold text-primary"><i class="pi pi-euro" />{{ $t('booking_detail_estimated_cost') }}</span>
              <span class="text-xl font-bold text-primary">€{{ booking.total_price.toFixed(2) }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Route -->
      <Card v-if="booking.stops && booking.stops.length >= 2">
        <template #title>{{ $t('booking_detail_route') }}</template>
        <template #content>
          <ol class="relative space-y-0">
            <li v-for="(stop, i) in booking.stops" :key="i" class="flex items-start gap-3 pb-4 last:pb-0 relative">
              <!-- vertical connector line (not on last item) -->
              <div v-if="i < booking.stops!.length - 1"
                class="absolute left-[9px] top-5 bottom-0 w-px bg-surface-200 dark:bg-surface-700" />
              <!-- circle indicator -->
              <span class="mt-0.5 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 z-10"
                :class="i === 0
                  ? 'bg-primary text-white'
                  : i === booking.stops!.length - 1
                  ? 'bg-surface-700 dark:bg-surface-300 text-white dark:text-surface-900'
                  : 'bg-surface-200 dark:bg-surface-600 text-surface-600 dark:text-white'">
                {{ i === 0 ? 'A' : i === booking.stops!.length - 1 ? 'B' : i }}
              </span>
              <div class="flex flex-col min-w-0 pt-0.5">
                <span class="text-xs text-surface-400 font-medium uppercase tracking-wide mb-0.5">
                  {{ i === 0 ? $t('reserve_start_location') : i === booking.stops!.length - 1 ? $t('reserve_end_location') : $t('reserve_stop_label').replace('{index}', String(i)) }}
                </span>
                <span class="text-sm">{{ stop }}</span>
              </div>
            </li>
          </ol>
        </template>
      </Card>

      <!-- Notes -->
      <Card v-if="booking.notes">
        <template #title>{{ $t('booking_detail_notes') }}</template>
        <template #content>
          <p class="text-sm italic text-surface-500">"{{ booking.notes }}"</p>
        </template>
      </Card>

      <!-- Borrower info (owner view only) -->
      <Card v-if="isOwnerView && booking.borrower_name">
        <template #title>{{ $t('booking_detail_borrower') }}</template>
        <template #content>
          <p class="text-sm font-medium">{{ booking.borrower_name }}</p>
          <p v-if="booking.borrower_email" class="text-sm text-surface-500">{{ booking.borrower_email }}</p>
        </template>
      </Card>

      <!-- Actions -->
      <div class="sticky bottom-0 -mx-4 px-4 py-3 mt-2 bg-surface-0/95 dark:bg-surface-900/95 backdrop-blur-sm border-t border-surface-100 dark:border-surface-800 sm:static sm:bg-transparent sm:border-0 sm:backdrop-filter-none sm:px-0 sm:py-0 sm:mx-0">
        <div class="flex gap-2 flex-wrap">
          <!-- Borrower actions -->
          <template v-if="!isOwnerView">
            <Button
              v-if="booking.status === 'pending' || booking.status === 'accepted'"
              :label="$t('booking_detail_cancel_booking')"
              icon="pi pi-times"
              severity="danger"
              outlined
              @click="confirmCancel"
            />
            <Button
              v-if="booking.status === 'pending' || booking.status === 'accepted'"
              :label="$t('booking_detail_reschedule')"
              icon="pi pi-calendar-clock"
              severity="secondary"
              outlined
              @click="rescheduleVisible = true"
            />
          </template>

          <!-- Owner actions -->
          <template v-if="isOwnerView && booking.status === 'pending'">
            <Button :label="$t('booking_detail_accept')" icon="pi pi-check" severity="success" @click="acceptBooking" />
            <Button :label="$t('booking_detail_decline')" icon="pi pi-times" severity="danger" outlined @click="declineBooking" />
          </template>
        </div>
      </div>
    </template>
  </div>

  <RescheduleDialog v-model:visible="rescheduleVisible" :booking="booking" @rescheduled="booking!.status = 'pending'" />
</template>
