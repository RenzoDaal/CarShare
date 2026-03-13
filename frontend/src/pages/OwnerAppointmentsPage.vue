<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import http from '@/api/http';
import { useRouter } from 'vue-router';
import { formatDateTime } from '@/utils/formatDate';
import { useI18n } from 'vue-i18n';
import { useToast } from 'primevue/usetoast';
import { haptic } from '@/utils/haptic';

const { t } = useI18n();
const toast = useToast();

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

type TabKey = 'pending' | 'accepted' | 'declined' | 'cancelled';
const activeTab = ref<TabKey>('pending');

const pendingBookings = computed(() => bookings.value.filter(b => b.status === 'pending'));
const acceptedBookings = computed(() => bookings.value.filter(b => b.status === 'accepted'));
const declinedBookings = computed(() => bookings.value.filter(b => b.status === 'declined'));
const cancelledBookings = computed(() => bookings.value.filter(b => b.status === 'cancelled'));

const activeBookings = computed(() => {
  if (activeTab.value === 'pending') return pendingBookings.value;
  if (activeTab.value === 'accepted') return acceptedBookings.value;
  if (activeTab.value === 'declined') return declinedBookings.value;
  return cancelledBookings.value;
});

const tabs = computed(() => [
  { key: 'pending' as TabKey, label: t('owner_pending_title'), count: pendingBookings.value.length, severity: 'warn', icon: 'pi pi-clock' },
  { key: 'accepted' as TabKey, label: t('owner_accepted_title'), count: acceptedBookings.value.length, severity: 'success', icon: 'pi pi-check-circle' },
  { key: 'declined' as TabKey, label: t('owner_declined_title'), count: declinedBookings.value.length, severity: 'danger', icon: 'pi pi-times-circle' },
  { key: 'cancelled' as TabKey, label: t('owner_cancelled_title'), count: cancelledBookings.value.length, severity: 'secondary', icon: 'pi pi-ban' },
]);

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
  haptic([30, 20, 60]);
  const booking = bookings.value.find(b => b.id === id);
  if (!booking) return;
  const prev = booking.status;
  booking.status = 'accepted';
  try {
    await http.post(`/bookings/${id}/accept`);
    toast.add({ severity: 'success', summary: t('owner_accepted_toast'), life: 2500 });
  } catch (err: any) {
    booking.status = prev;
    toast.add({ severity: 'error', summary: t('owner_error_accept'), detail: err?.response?.data?.detail, life: 4000 });
  }
}

async function declineBooking(id: number) {
  haptic(50);
  const booking = bookings.value.find(b => b.id === id);
  if (!booking) return;
  const prev = booking.status;
  booking.status = 'declined';
  try {
    await http.post(`/bookings/${id}/decline`);
    toast.add({ severity: 'info', summary: t('owner_declined_toast'), life: 2500 });
  } catch (err: any) {
    booking.status = prev;
    toast.add({ severity: 'error', summary: t('owner_error_decline'), detail: err?.response?.data?.detail, life: 4000 });
  }
}

onMounted(fetchBookings);
</script>

<template>
  <div class="p-4 flex flex-col gap-5 max-w-5xl mx-auto w-full">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('owner_appointments_title') }}</h1>
      <p class="text-sm text-surface-400 mt-0.5">{{ $t('owner_appointments_title') }}</p>
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <!-- Tab bar -->
    <div class="grid grid-cols-2 gap-1 p-1 bg-surface-100 dark:bg-zinc-800 rounded-2xl">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200"
        :class="activeTab === tab.key
          ? 'bg-white dark:bg-zinc-900 text-slate-900 dark:text-slate-100 shadow-sm'
          : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
        @click="activeTab = tab.key"
      >
        <span>{{ tab.label }}</span>
        <span v-if="tab.count > 0"
          class="flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold shrink-0"
          :class="activeTab === tab.key
            ? (tab.key === 'pending' ? 'bg-amber-500 text-white' : tab.key === 'accepted' ? 'bg-green-500 text-white' : 'bg-slate-400 text-white')
            : 'bg-surface-300 dark:bg-zinc-600 text-slate-600 dark:text-slate-300'"
        >
          {{ tab.count }}
        </span>
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i"
        class="rounded-2xl border border-surface-200 dark:border-zinc-700 p-5 animate-pulse space-y-3">
        <div class="h-4 bg-surface-200 dark:bg-zinc-700 rounded-full w-1/3" />
        <div class="h-3 bg-surface-100 dark:bg-zinc-800 rounded-full w-1/2" />
        <div class="flex gap-2 mt-4">
          <div class="h-8 w-20 bg-surface-200 dark:bg-zinc-700 rounded-xl" />
          <div class="h-8 w-20 bg-surface-200 dark:bg-zinc-700 rounded-xl" />
        </div>
      </div>
    </div>

    <!-- Content area -->
    <template v-else>
      <!-- Empty state -->
      <div v-if="activeBookings.length === 0"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div class="w-16 h-16 rounded-2xl bg-surface-100 dark:bg-zinc-800 flex items-center justify-center">
          <i class="pi pi-calendar text-2xl text-surface-400" />
        </div>
        <div>
          <p class="font-medium text-slate-600 dark:text-slate-300">
            {{ activeTab === 'pending' ? $t('owner_no_pending')
              : activeTab === 'accepted' ? $t('owner_no_accepted')
              : activeTab === 'declined' ? $t('owner_no_declined')
              : $t('owner_no_cancelled') }}
          </p>
        </div>
      </div>

      <!-- Pending bookings (special layout with prominent actions) -->
      <div v-if="activeTab === 'pending' && activeBookings.length > 0" class="flex flex-col gap-3">
        <div v-for="booking in activeBookings" :key="booking.id"
          class="bg-white dark:bg-zinc-900 border border-amber-200 dark:border-amber-900/50 rounded-2xl p-5 shadow-sm">
          <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <Tag severity="warn" :value="$t('owner_pending_title')" />
              </div>
              <h3 class="font-bold text-base">{{ booking.car.name }}</h3>
              <p class="text-sm text-surface-500 mt-0.5">
                {{ formatDateTime(booking.start_datetime) }} – {{ formatDateTime(booking.end_datetime) }}
              </p>
              <p v-if="booking.total_price != null" class="text-sm font-semibold text-primary mt-1.5">
                {{ $t('owner_total_price') }} €{{ booking.total_price.toFixed(2) }}
              </p>
              <p v-if="booking.borrower_name" class="text-sm mt-2 text-surface-500">
                {{ $t('owner_borrower_label') }}
                <span class="font-semibold text-slate-700 dark:text-slate-200">{{ booking.borrower_name }}</span>
                <span v-if="booking.borrower_email"> — {{ booking.borrower_email }}</span>
              </p>
              <div v-if="booking.notes"
                class="text-sm mt-3 p-3 rounded-xl bg-surface-50 dark:bg-zinc-800 italic text-surface-500 border border-surface-100 dark:border-zinc-700">
                "{{ booking.notes }}"
              </div>
            </div>
            <div class="flex gap-2 flex-wrap md:flex-col md:items-stretch shrink-0">
              <Button :label="$t('owner_summary')" icon="pi pi-file" severity="secondary" outlined size="small"
                @click="router.push({ name: 'booking-detail', params: { id: booking.id } })" />
              <Button :label="$t('owner_accept')" icon="pi pi-check" severity="success" size="small"
                @click="acceptBooking(booking.id)" />
              <Button :label="$t('owner_decline')" icon="pi pi-times" severity="danger" outlined size="small"
                @click="declineBooking(booking.id)" />
            </div>
          </div>
        </div>
      </div>

      <!-- Accepted / Declined / Cancelled grid -->
      <div v-else-if="activeBookings.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div v-for="booking in activeBookings" :key="booking.id"
          class="bg-white dark:bg-zinc-900 border rounded-2xl p-4 flex flex-col gap-2 hover:shadow-md transition-all duration-200 cursor-pointer"
          :class="activeTab === 'accepted'
            ? 'border-green-200 dark:border-green-900/40'
            : 'border-surface-200 dark:border-zinc-700'"
          @click="router.push({ name: 'booking-detail', params: { id: booking.id } })"
        >
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-bold text-sm truncate">{{ booking.car.name }}</h3>
            <Tag
              :severity="activeTab === 'accepted' ? 'success' : activeTab === 'declined' ? 'danger' : 'secondary'"
              :value="activeTab === 'accepted' ? $t('owner_accepted_tag') : activeTab === 'declined' ? $t('owner_declined_tag') : $t('owner_cancelled_tag')"
            />
          </div>
          <p class="text-xs text-surface-400">
            {{ formatDateTime(booking.start_datetime) }} – {{ formatDateTime(booking.end_datetime) }}
          </p>
          <p v-if="booking.total_price != null" class="text-sm font-semibold text-primary">
            €{{ booking.total_price.toFixed(2) }}
          </p>
          <p v-if="booking.borrower_name" class="text-xs text-surface-500 truncate">
            {{ $t('owner_borrower_label') }}
            <span class="font-medium text-slate-600 dark:text-slate-300">{{ booking.borrower_name }}</span>
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
