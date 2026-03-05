<script setup lang="ts">
import Card from 'primevue/card';
import Button from 'primevue/button';
import Tag from 'primevue/tag';

import { onMounted, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import http from '@/api/http';
import type { Car } from '@/stores/cars';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const auth = useAuthStore();


type DashboardBooking = {
  id: number;
  car: Car;
  start_datetime: string;
  end_datetime: string;
  status: string;
  total_price?: number | null;
};

type DashboardResponse = {
  upcoming_bookings: DashboardBooking[];
  active_cars: Car[];
};

const loading = ref(true);
const error = ref<string | null>(null);
const data = ref<DashboardResponse>({
  upcoming_bookings: [],
  active_cars: [],
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

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

async function loadDashboard() {
  loading.value = true;
  error.value = null;
  try {
    const res = await http.get<DashboardResponse>('/dashboard');
    data.value = res.data;
  } catch (err: any) {
    console.error(err);
    error.value = err?.response?.data?.detail ?? 'Failed to load dashboard.';
  } finally {
    loading.value = false;
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
});
</script>


<template>
  <div class="flex-1 flex justify-center w-full">
    <div class="w-full max-w-6xl px-4 py-6 space-y-4">
      <h1 class="text-2xl font-semibold mb-2">Dashboard</h1>

      <div v-if="error" class="p-3 rounded bg-red-100 text-red-800 text-sm">
        {{ error }}
      </div>

      <div v-if="loading">
        <Card class="mb-4">
          <template #title>
            <span>Loading your dashboard...</span>
          </template>
          <template #content>
            <p class="text-sm text-surface-500">
              Fetching your bookings and cars.
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
                  <span>Your bookings</span>
                  <Tag v-if="hasBookings" :value="`${data?.upcoming_bookings.length} upcoming`" />
                  <Tag v-else value="No upcoming bookings" severity="info" />
                </div>
              </template>
              <template #content>
                <div v-if="!hasBookings" class="text-sm text-surface-500">
                  You don't have any upcoming bookings yet.
                  <Button label="Reserve a car" icon="pi pi-calendar" size="small" class="mt-3" @click="goToReserve" />
                </div>

                <div v-else class="space-y-4">
                  <div v-if="nextBooking" class="rounded-lg border border-surface-200 p-3">
                    <p class="text-xs uppercase tracking-wide text-surface-500 mb-1">
                      Next booking
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
                      Estimated price:
                      <span class="font-semibold">
                        € {{ nextBooking!.total_price!.toFixed(2) }}
                      </span>
                    </p>
                    <div class="mt-2">
                      <Tag :value="nextBooking!.status" />
                    </div>
                  </div>

                  <div v-if="otherBookings.length" class="space-y-2">
                    <p class="text-xs uppercase tracking-wide text-surface-500">
                      Later bookings
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
                        <Tag :value="b.status" />
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
                <span>Quick actions</span>
              </template>
              <template #content>
                <div class="flex-1 flex flex-col gap-2">
                  <Button label="Reserve a car" icon="pi pi-calendar" @click="goToReserve" />
                  <Button v-if="isOwner" label="Manage my cars" icon="pi pi-car" severity="secondary"
                    @click="goToManageCars" />
                </div>
              </template>
            </Card>
          </div>
        </div>

        <div v-if="isOwner">
          <Card>
            <template #title>
              <div class="flex items-center justify-between gap-2">
                <span>Your cars</span>
                <Button label="Manage cars" icon="pi pi-car" size="small" severity="secondary"
                  @click="goToManageCars" />
              </div>
            </template>
            <template #content>
              <div v-if="!data?.active_cars?.length" class="text-sm text-surface-500">
                You haven't added any cars yet.
                <span class="block mt-1">
                  Use <b>Manage cars</b> to add your first car.
                </span>
              </div>

              <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <Card v-for="car in data!.active_cars" :key="car.id" class="border border-surface-200 rounded-lg">
                  <template #title>
                    <div class="flex items-center justify-between gap-2">
                      <span>{{ car.name }}</span>
                      <Tag :value="car.is_active ? 'Active' : 'Disabled'"
                        :severity="car.is_active ? 'success' : 'danger'" />
                    </div>
                  </template>
                  <template #content>
                    <p class="text-sm text-surface-500 mb-1">
                      {{ car.description || 'No description' }}
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
