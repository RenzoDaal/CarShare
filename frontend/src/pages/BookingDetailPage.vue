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
import http from '@/api/http';
import { formatDateTime } from '@/utils/formatDate';

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

const isOwnerView = computed(() => auth.user?.id === booking.value?.car.owner_id);

onMounted(async () => {
  try {
    const { data } = await http.get<Booking>(`/bookings/${route.params.id}/detail`);
    booking.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to load booking.';
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
  if (status === 'pending') return 'Awaiting owner approval';
  if (status === 'accepted') return 'Confirmed';
  if (status === 'declined') return 'Declined by owner';
  if (status === 'cancelled') return 'Cancelled';
  return '';
}

function confirmCancel() {
  if (!booking.value) return;
  confirm.require({
    message: 'Are you sure you want to cancel this booking?',
    header: 'Cancel booking',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Keep booking', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Cancel booking', severity: 'danger' },
    accept: async () => {
      try {
        await http.post(`/bookings/${booking.value!.id}/cancel`);
        booking.value!.status = 'cancelled';
      } catch (err: any) {
        error.value = err?.response?.data?.detail ?? 'Failed to cancel booking.';
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
      <h1 class="text-2xl font-semibold">Booking summary</h1>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <ProgressSpinner />
    </div>

    <div v-else-if="error" class="p-3 rounded bg-red-100 text-red-800 text-sm">{{ error }}</div>

    <template v-else-if="booking">
      <!-- Status banner -->
      <div class="flex items-center gap-3 p-4 rounded-lg border"
        :class="{
          'border-green-300 bg-green-50 dark:bg-green-900/20': booking.status === 'accepted',
          'border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20': booking.status === 'pending',
          'border-red-300 bg-red-50 dark:bg-red-900/20': booking.status === 'declined' || booking.status === 'cancelled',
        }">
        <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
        <span class="text-sm">{{ statusLabel(booking.status) }}</span>
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
        <template #title>Details</template>
        <template #content>
          <dl class="space-y-3 text-sm">
            <div class="flex justify-between">
              <dt class="text-surface-500">Start</dt>
              <dd class="font-medium">{{ formatDateTime(booking.start_datetime) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-500">End</dt>
              <dd class="font-medium">{{ formatDateTime(booking.end_datetime) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-500">Duration</dt>
              <dd class="font-medium">{{ formatDuration(booking.start_datetime, booking.end_datetime) }}</dd>
            </div>
            <div v-if="booking.total_price != null" class="flex justify-between border-t pt-3">
              <dt class="text-surface-500">Estimated cost</dt>
              <dd class="font-semibold text-base">€{{ booking.total_price.toFixed(2) }}</dd>
            </div>
          </dl>
        </template>
      </Card>

      <!-- Route -->
      <Card v-if="booking.stops && booking.stops.length >= 2">
        <template #title>Route</template>
        <template #content>
          <ol class="space-y-2">
            <li v-for="(stop, i) in booking.stops" :key="i" class="flex items-start gap-2 text-sm">
              <span class="mt-0.5 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                :class="i === 0 ? 'bg-primary text-white' : i === booking.stops!.length - 1 ? 'bg-surface-700 text-white dark:bg-surface-300 dark:text-surface-900' : 'bg-surface-200 dark:bg-surface-600 text-surface-700 dark:text-white'">
                {{ i === 0 ? 'A' : i === booking.stops!.length - 1 ? 'B' : i }}
              </span>
              <span>{{ stop }}</span>
            </li>
          </ol>
        </template>
      </Card>

      <!-- Notes -->
      <Card v-if="booking.notes">
        <template #title>Notes</template>
        <template #content>
          <p class="text-sm italic text-surface-500">"{{ booking.notes }}"</p>
        </template>
      </Card>

      <!-- Borrower info (owner view only) -->
      <Card v-if="isOwnerView && booking.borrower_name">
        <template #title>Borrower</template>
        <template #content>
          <p class="text-sm font-medium">{{ booking.borrower_name }}</p>
          <p v-if="booking.borrower_email" class="text-sm text-surface-500">{{ booking.borrower_email }}</p>
        </template>
      </Card>

      <!-- Actions -->
      <div class="flex gap-2 flex-wrap">
        <!-- Borrower actions -->
        <template v-if="!isOwnerView">
          <Button
            v-if="booking.status === 'pending' || booking.status === 'accepted'"
            label="Cancel booking"
            icon="pi pi-times"
            severity="danger"
            outlined
            @click="confirmCancel"
          />
          <Button
            v-if="booking.status === 'pending' || booking.status === 'accepted'"
            label="Reschedule"
            icon="pi pi-calendar-clock"
            severity="secondary"
            outlined
            @click="router.push({ name: 'borrowerappointments' })"
          />
        </template>

        <!-- Owner actions -->
        <template v-if="isOwnerView && booking.status === 'pending'">
          <Button label="Accept" icon="pi pi-check" severity="success" @click="acceptBooking" />
          <Button label="Decline" icon="pi pi-times" severity="danger" outlined @click="declineBooking" />
        </template>
      </div>
    </template>
  </div>
</template>
