<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import http from '@/api/http';

type BookingStatus = 'pending' | 'accepted' | 'declined';

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
};

const bookings = ref<BorrowerBooking[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const now = new Date();
const upcoming = computed(() =>
  bookings.value.filter(
    (b) => b.status !== 'declined' && toUtcDate(b.end_datetime) >= now,
  ),
);
const history = computed(() =>
  bookings.value.filter(
    (b) => b.status === 'declined' || toUtcDate(b.end_datetime) < now,
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

onMounted(fetchBookings);
</script>

<template>
  <div class="p-4 flex flex-col gap-4">
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
            You don't have any bookings yet.
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <Card v-for="booking in upcoming" :key="booking.id" class="h-full">
              <template #title>{{ booking.car.name }}</template>
              <template #subtitle>
                <Tag :value="booking.status" :severity="statusSeverity(booking.status)" />
              </template>
              <template #content>
                <p class="text-sm text-surface-500 mb-1">
                  {{ formatDateTime(booking.start_datetime) }} –
                  {{ formatDateTime(booking.end_datetime) }}
                </p>
                <p v-if="booking.total_price != null" class="text-sm font-medium mt-1">
                  Total price: €{{ booking.total_price.toFixed(2) }}
                </p>
                <p class="text-xs text-surface-400 mt-2">
                  Your booking is only final once it is
                  <strong>accepted</strong> by the owner.
                </p>
              </template>
            </Card>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>Past & declined bookings</template>
        <template #content>
          <div v-if="history.length === 0" class="text-sm text-surface-500">
            No past or declined bookings.
          </div>
          <ul v-else class="flex flex-col gap-2 text-sm">
            <li v-for="booking in history" :key="booking.id"
              class="flex justify-between items-center border rounded-md p-2">
              <span>
                {{ booking.car.name }} –
                {{ formatDateTime(booking.start_datetime) }}
              </span>
              <Tag severity="danger" value="Declined" />
            </li>
          </ul>
        </template>
      </Card>
    </template>
  </div>
</template>
