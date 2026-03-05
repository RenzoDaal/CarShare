<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import http from '@/api/http';

type BookingStatus = 'pending' | 'accepted' | 'declined';

type OwnerBooking = {
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

const bookings = ref<OwnerBooking[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const pendingBookings = computed(() =>
  bookings.value.filter((b) => b.status === 'pending'),
);
const acceptedBookings = computed(() =>
  bookings.value.filter((b) => b.status === 'accepted'),
);
const declinedBookings = computed(() =>
  bookings.value.filter((b) => b.status === 'declined'),
);

function formatDateTime(value: string) {
  const normalized = value.endsWith('Z') || value.includes('+') ? value : value + 'Z';
  return new Date(normalized).toLocaleString();
}

async function fetchBookings() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await http.get<OwnerBooking[]>('/bookings/owner');
    bookings.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to load bookings';
  } finally {
    loading.value = false;
  }
}

async function acceptBooking(id: number) {
  try {
    await http.post(`/bookings/${id}/accept`);
    await fetchBookings();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to accept booking';
  }
}

async function declineBooking(id: number) {
  try {
    await http.post(`/bookings/${id}/decline`);
    await fetchBookings();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to decline booking';
  }
}

onMounted(fetchBookings);
</script>

<template>
  <div class="p-4 flex flex-col gap-4">
    <h1 class="text-2xl font-semibold mb-2">Appointments for your cars</h1>

    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <div v-if="loading" class="flex justify-center items-center py-10">
      <ProgressSpinner />
    </div>

    <template v-else>
      <!-- Pending -->
      <Card class="mb-4">
        <template #title>Pending approvals</template>
        <template #content>
          <div v-if="pendingBookings.length === 0" class="text-sm text-surface-500">
            There are no pending bookings right now.
          </div>
          <div v-else class="flex flex-col gap-3">
            <div v-for="booking in pendingBookings" :key="booking.id"
              class="border rounded-md p-3 flex flex-col gap-2 md:flex-row md:justify-between md:items-center">
              <div>
                <div class="font-semibold">
                  {{ booking.car.name }}
                </div>
                <div class="text-sm text-surface-500">
                  {{ formatDateTime(booking.start_datetime) }} –
                  {{ formatDateTime(booking.end_datetime) }}
                </div>
                <div v-if="booking.total_price != null" class="text-sm mt-1">
                  Total price: €{{ booking.total_price.toFixed(2) }}
                </div>
              </div>
              <div class="flex gap-2 mt-2 md:mt-0">
                <Button label="Accept" icon="pi pi-check" severity="success" @click="acceptBooking(booking.id)" />
                <Button label="Decline" icon="pi pi-times" severity="danger" outlined
                  @click="declineBooking(booking.id)" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Accepted -->
      <Card class="mb-4">
        <template #title>Upcoming accepted bookings</template>
        <template #content>
          <div v-if="acceptedBookings.length === 0" class="text-sm text-surface-500">
            No accepted bookings yet.
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <Card v-for="booking in acceptedBookings" :key="booking.id" class="h-full">
              <template #title>{{ booking.car.name }}</template>
              <template #subtitle>
                <Tag severity="success" value="Accepted" />
              </template>
              <template #content>
                <p class="text-sm text-surface-500 mb-1">
                  {{ formatDateTime(booking.start_datetime) }} –
                  {{ formatDateTime(booking.end_datetime) }}
                </p>
                <p v-if="booking.total_price != null" class="text-sm font-medium mt-1">
                  Total price: €{{ booking.total_price.toFixed(2) }}
                </p>
              </template>
            </Card>
          </div>
        </template>
      </Card>

      <!-- Declined -->
      <Card>
        <template #title>Declined bookings</template>
        <template #content>
          <div v-if="declinedBookings.length === 0" class="text-sm text-surface-500">
            No declined bookings.
          </div>
          <ul v-else class="flex flex-col gap-2 text-sm">
            <li v-for="booking in declinedBookings" :key="booking.id"
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
