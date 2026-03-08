<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import http from '@/api/http';
import { useRouter } from 'vue-router';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

type BookingStatus = 'pending' | 'accepted' | 'declined' | 'cancelled';

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
  borrower_name?: string | null;
  borrower_email?: string | null;
  notes?: string | null;
};

const router = useRouter();
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
const cancelledBookings = computed(() =>
  bookings.value.filter((b) => b.status === 'cancelled'),
);

async function fetchBookings() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await http.get<OwnerBooking[]>('/bookings/owner');
    bookings.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? t('owner_error_load');
  } finally {
    loading.value = false;
  }
}

async function acceptBooking(id: number) {
  try {
    await http.post(`/bookings/${id}/accept`);
    await fetchBookings();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? t('owner_error_accept');
  }
}

async function declineBooking(id: number) {
  try {
    await http.post(`/bookings/${id}/decline`);
    await fetchBookings();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? t('owner_error_decline');
  }
}

onMounted(fetchBookings);
</script>

<template>
  <div class="p-4 flex flex-col gap-4 max-w-5xl mx-auto w-full">
    <h1 class="text-2xl font-semibold mb-2">{{ $t('owner_appointments_title') }}</h1>

    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <div v-if="loading" class="flex justify-center items-center py-10">
      <ProgressSpinner />
    </div>

    <template v-else>
      <!-- Pending -->
      <Card class="mb-4">
        <template #title>{{ $t('owner_pending_title') }}</template>
        <template #content>
          <div v-if="pendingBookings.length === 0" class="text-sm text-surface-500">
            {{ $t('owner_no_pending') }}
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
                  {{ $t('owner_total_price') }} €{{ booking.total_price.toFixed(2) }}
                </div>
                <div v-if="booking.borrower_name" class="text-sm mt-1 text-surface-500">
                  {{ $t('owner_borrower_label') }} <span class="font-medium text-surface-700 dark:text-surface-200">{{ booking.borrower_name }}</span>
                  <span v-if="booking.borrower_email"> — {{ booking.borrower_email }}</span>
                </div>
                <div v-if="booking.notes" class="text-sm mt-2 p-2 rounded bg-surface-100 dark:bg-surface-800 italic text-surface-600 dark:text-surface-300">
                  "{{ booking.notes }}"
                </div>
              </div>
              <div class="flex gap-2 mt-2 md:mt-0 flex-wrap">
                <Button :label="$t('owner_summary')" icon="pi pi-file" severity="secondary" outlined
                  @click="router.push({ name: 'booking-detail', params: { id: booking.id } })" />
                <Button :label="$t('owner_accept')" icon="pi pi-check" severity="success" @click="acceptBooking(booking.id)" />
                <Button :label="$t('owner_decline')" icon="pi pi-times" severity="danger" outlined
                  @click="declineBooking(booking.id)" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Accepted -->
      <Card class="mb-4">
        <template #title>{{ $t('owner_accepted_title') }}</template>
        <template #content>
          <div v-if="acceptedBookings.length === 0" class="text-sm text-surface-500">
            {{ $t('owner_no_accepted') }}
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <Card v-for="booking in acceptedBookings" :key="booking.id" class="h-full">
              <template #title>{{ booking.car.name }}</template>
              <template #subtitle>
                <Tag severity="success" :value="$t('owner_accepted_tag')" />
              </template>
              <template #content>
                <p class="text-sm text-surface-500 mb-1">
                  {{ formatDateTime(booking.start_datetime) }} –
                  {{ formatDateTime(booking.end_datetime) }}
                </p>
                <p v-if="booking.total_price != null" class="text-sm font-medium mt-1">
                  {{ $t('owner_total_price') }} €{{ booking.total_price.toFixed(2) }}
                </p>
                <p v-if="booking.borrower_name" class="text-sm mt-1 text-surface-500">
                  {{ $t('owner_borrower_label') }} <span class="font-medium text-surface-700 dark:text-surface-200">{{ booking.borrower_name }}</span>
                  <span v-if="booking.borrower_email"> — {{ booking.borrower_email }}</span>
                </p>
              </template>
            </Card>
          </div>
        </template>
      </Card>

      <!-- Declined -->
      <Card class="mb-4">
        <template #title>{{ $t('owner_declined_title') }}</template>
        <template #content>
          <div v-if="declinedBookings.length === 0" class="text-sm text-surface-500">
            {{ $t('owner_no_declined') }}
          </div>
          <ul v-else class="flex flex-col gap-2 text-sm">
            <li v-for="booking in declinedBookings" :key="booking.id"
              class="flex justify-between items-center border rounded-md p-2">
              <div>
                <span class="font-medium">{{ booking.car.name }}</span> –
                {{ formatDateTime(booking.start_datetime) }}
                <span v-if="booking.borrower_name" class="ml-2 text-surface-400">({{ booking.borrower_name }})</span>
              </div>
              <Tag severity="danger" :value="$t('owner_declined_tag')" />
            </li>
          </ul>
        </template>
      </Card>

      <!-- Cancelled -->
      <Card>
        <template #title>{{ $t('owner_cancelled_title') }}</template>
        <template #content>
          <div v-if="cancelledBookings.length === 0" class="text-sm text-surface-500">
            {{ $t('owner_no_cancelled') }}
          </div>
          <ul v-else class="flex flex-col gap-2 text-sm">
            <li v-for="booking in cancelledBookings" :key="booking.id"
              class="flex justify-between items-center border rounded-md p-2">
              <div>
                <span class="font-medium">{{ booking.car.name }}</span> –
                {{ formatDateTime(booking.start_datetime) }}
                <span v-if="booking.borrower_name" class="ml-2 text-surface-400">({{ booking.borrower_name }})</span>
              </div>
              <Tag severity="secondary" :value="$t('owner_cancelled_tag')" />
            </li>
          </ul>
        </template>
      </Card>
    </template>
  </div>
</template>
