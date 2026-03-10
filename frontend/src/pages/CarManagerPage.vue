<script setup lang="ts">
import Card from 'primevue/card';
import Toolbar from 'primevue/toolbar';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import InputNumber from 'primevue/inputnumber';
import DatePicker from 'primevue/datepicker';
import Tag from 'primevue/tag';
import SelectButton from 'primevue/selectbutton';

import { useCarStore, type NewCarPayload, type UpdateCarPayload, type Car } from '@/stores/cars';
import { formatDateOnly } from '@/utils/formatDate';
import CarImageCarousel from '@/components/CarImageCarousel.vue';
import { computed, onMounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useConfirm } from 'primevue/useconfirm';
import http from '@/api/http';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const priceModeOptions = computed(() => [
  { label: t('car_manager_price_mode_manual'), value: 'manual' },
  { label: t('car_manager_price_mode_calculated'), value: 'calculated' },
]);

const fuelTypeOptions = computed(() => [
  { label: t('car_manager_fuel_electric'), value: 'electric' },
  { label: t('car_manager_fuel_combustion'), value: 'combustion' },
]);

const calcPricePerKm = (
  fuelType: string | null | undefined,
  batteryKwh: number | null | undefined,
  rangeKm: number | null | undefined,
  chargeCost: number | null | undefined,
  consumption: number | null | undefined,
  fuelPrice: number | null | undefined,
): number | null => {
  if (fuelType === 'electric' && batteryKwh && rangeKm && chargeCost) {
    return (batteryKwh / rangeKm) * chargeCost;
  }
  if (fuelType === 'combustion' && consumption && fuelPrice) {
    return (consumption / 100) * fuelPrice;
  }
  return null;
};

type UnavailabilityBlock = {
  id: number;
  car_id: number;
  start_date: string;
  end_date: string;
};

const carStore = useCarStore();
const confirm = useConfirm();
const { cars } = storeToRefs(carStore);

onMounted(() => {
  carStore.fetchMyCars();
})

const createCarDialogVisible = ref(false);
const editCarDialogVisible = ref(false);
const editingCarId = ref<number | null>(null);
const newCarImage = ref<File | null>(null);

const onNewCarImageSelected = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    newCarImage.value = target.files[0];
  }
};

type CarImage = { id: number; url: string; order: number };
const editCarImages = ref<CarImage[]>([]);
const editImagesLoading = ref(false);
const galleryFileInput = ref<HTMLInputElement | null>(null);

const loadEditImages = async (carId: number) => {
  editImagesLoading.value = true;
  try {
    const res = await http.get<CarImage[]>(`/cars/${carId}/images`);
    editCarImages.value = res.data;
  } catch {
    editCarImages.value = [];
  } finally {
    editImagesLoading.value = false;
  }
};

const onGalleryFileSelected = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files?.[0] || editingCarId.value == null) return;
  const formData = new FormData();
  formData.append('file', target.files[0]);
  try {
    const res = await http.post<CarImage>(`/cars/${editingCarId.value}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    editCarImages.value.push(res.data);
    await carStore.fetchMyCars();
  } catch { /* ignore */ }
  target.value = '';
};

const deleteGalleryImage = async (imageId: number) => {
  if (editingCarId.value == null) return;
  await http.delete(`/cars/${editingCarId.value}/images/${imageId}`);
  editCarImages.value = editCarImages.value.filter(i => i.id !== imageId);
  await carStore.fetchMyCars();
};

const newCar = ref<NewCarPayload>({
  name: '',
  description: '',
  price_per_km: 0,
  price_mode: 'manual',
  fuel_type: null,
  calc_battery_kwh: null,
  calc_range_km: null,
  calc_charge_cost_per_kwh: null,
  calc_consumption_per_100km: null,
  calc_fuel_price_per_liter: null,
});

const editCar = ref<UpdateCarPayload>({
  name: '',
  description: '',
  price_per_km: 0,
  is_active: true,
  price_mode: 'manual',
  fuel_type: null,
  calc_battery_kwh: null,
  calc_range_km: null,
  calc_charge_cost_per_kwh: null,
  calc_consumption_per_100km: null,
  calc_fuel_price_per_liter: null,
});

const newCarCalcPrice = computed(() => calcPricePerKm(
  newCar.value.fuel_type,
  newCar.value.calc_battery_kwh,
  newCar.value.calc_range_km,
  newCar.value.calc_charge_cost_per_kwh,
  newCar.value.calc_consumption_per_100km,
  newCar.value.calc_fuel_price_per_liter,
));

const editCarCalcPrice = computed(() => calcPricePerKm(
  editCar.value.fuel_type,
  editCar.value.calc_battery_kwh,
  editCar.value.calc_range_km,
  editCar.value.calc_charge_cost_per_kwh,
  editCar.value.calc_consumption_per_100km,
  editCar.value.calc_fuel_price_per_liter,
));

// Whenever any calc input changes, auto-fill price_per_km with the new calculated result
const calcFields = (car: typeof newCar.value | typeof editCar.value) => [
  car.fuel_type,
  car.calc_battery_kwh,
  car.calc_range_km,
  car.calc_charge_cost_per_kwh,
  car.calc_consumption_per_100km,
  car.calc_fuel_price_per_liter,
];

watch(() => calcFields(newCar.value), () => {
  if (newCarCalcPrice.value !== null)
    newCar.value.price_per_km = Math.round(newCarCalcPrice.value * 100) / 100;
});

watch(() => calcFields(editCar.value), () => {
  if (editCarCalcPrice.value !== null)
    editCar.value.price_per_km = Math.round(editCarCalcPrice.value * 100) / 100;
});

const submitCreateCar = async () => {
  const created = await carStore.createCar(newCar.value);

  if (created && newCarImage.value) {
    await carStore.uploadCarImage(created.id, newCarImage.value);
    newCarImage.value = null;
  }

  createCarDialogVisible.value = false;

  newCar.value = {
    name: '',
    description: '',
    price_per_km: 0,
    price_mode: 'manual',
    fuel_type: null,
    calc_battery_kwh: null,
    calc_range_km: null,
    calc_charge_cost_per_kwh: null,
    calc_consumption_per_100km: null,
    calc_fuel_price_per_liter: null,
  };
}

const openEditDialog = (car: Car) => {
  editingCarId.value = car.id;
  editCar.value = {
    name: car.name,
    description: car.description ?? '',
    price_per_km: car.price_per_km,
    is_active: car.is_active,
    price_mode: car.price_mode ?? 'manual',
    fuel_type: car.fuel_type ?? null,
    calc_battery_kwh: car.calc_battery_kwh ?? null,
    calc_range_km: car.calc_range_km ?? null,
    calc_charge_cost_per_kwh: car.calc_charge_cost_per_kwh ?? null,
    calc_consumption_per_100km: car.calc_consumption_per_100km ?? null,
    calc_fuel_price_per_liter: car.calc_fuel_price_per_liter ?? null,
  };
  editCarDialogVisible.value = true;
  loadEditImages(car.id);
};

const submitEditCar = async () => {
  if (editingCarId.value == null) return;
  await carStore.updateCar(editingCarId.value, editCar.value);
  editCarDialogVisible.value = false;
};

const confirmDeleteCar = (carId: number) => {
  confirm.require({
    message: t('car_manager_confirm_delete'),
    header: t('car_manager_confirm_header'),
    icon: 'pi pi-info-circle',
    rejectLabel: t('car_manager_confirm_cancel'),
    rejectProps: {
      label: t('car_manager_confirm_cancel'),
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: t('car_manager_confirm_delete_button'),
      severity: 'danger'
    },
    accept: async () => {
      await carStore.deleteCar(carId);
    }
  });
}

// Unavailability management
const unavailabilityDialogVisible = ref(false);
const unavailabilityCarId = ref<number | null>(null);
const unavailabilityCarName = ref('');
const unavailabilityBlocks = ref<UnavailabilityBlock[]>([]);
const unavailabilityLoading = ref(false);
const unavailabilityError = ref<string | null>(null);

const newBlockDates = ref<Date[] | null>(null);
const addingBlock = ref(false);
const addBlockError = ref<string | null>(null);

const openUnavailabilityDialog = async (car: Car) => {
  unavailabilityCarId.value = car.id;
  unavailabilityCarName.value = car.name;
  unavailabilityBlocks.value = [];
  unavailabilityError.value = null;
  newBlockDates.value = null;
  addBlockError.value = null;
  unavailabilityDialogVisible.value = true;
  await loadUnavailability(car.id);
};

const loadUnavailability = async (carId: number) => {
  unavailabilityLoading.value = true;
  unavailabilityError.value = null;
  try {
    const res = await http.get<UnavailabilityBlock[]>(`/cars/${carId}/unavailability`);
    unavailabilityBlocks.value = res.data;
  } catch (err: any) {
    unavailabilityError.value = err?.response?.data?.detail ?? t('car_manager_error_load_blocks');
  } finally {
    unavailabilityLoading.value = false;
  }
};

const toLocalDateString = (d: Date) => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

const addBlock = async () => {
  if (!unavailabilityCarId.value || !newBlockDates.value || newBlockDates.value.length < 2) return;
  const [startDate, endDate] = newBlockDates.value;
  if (!startDate || !endDate) {
    addBlockError.value = t('car_manager_error_select_dates');
    return;
  }

  addingBlock.value = true;
  addBlockError.value = null;
  try {
    await http.post<UnavailabilityBlock>(`/cars/${unavailabilityCarId.value}/unavailability`, {
      start_date: toLocalDateString(startDate),
      end_date: toLocalDateString(endDate),
    });
    newBlockDates.value = null;
    await loadUnavailability(unavailabilityCarId.value);
  } catch (err: any) {
    addBlockError.value = err?.response?.data?.detail ?? t('car_manager_error_add_block');
  } finally {
    addingBlock.value = false;
  }
};

const deleteBlock = async (blockId: number) => {
  if (!unavailabilityCarId.value) return;
  try {
    await http.delete(`/cars/${unavailabilityCarId.value}/unavailability/${blockId}`);
    unavailabilityBlocks.value = unavailabilityBlocks.value.filter(b => b.id !== blockId);
  } catch (err: any) {
    unavailabilityError.value = err?.response?.data?.detail ?? t('car_manager_error_delete_block');
  }
};

const formatDate = (iso: string) => formatDateOnly(iso + 'T00:00:00');

// Co-owner management
const coOwnersDialogVisible = ref(false);
const coOwnersCarId = ref<number | null>(null);
const coOwnersCarName = ref('');
const coOwnersList = ref<{ user_id: number; full_name: string; email: string; status: string }[]>([]);
const coOwnersLoading = ref(false);
const inviteEmail = ref('');
const inviteLoading = ref(false);
const inviteError = ref<string | null>(null);
const leaveLoading = ref(false);

import { useAuthStore } from '@/stores/auth';
const auth = useAuthStore();

const isPrimaryOwner = (car: Car) => car.owner_id === auth.user?.id;

const openCoOwnersDialog = async (car: Car) => {
  coOwnersCarId.value = car.id;
  coOwnersCarName.value = car.name;
  coOwnersList.value = [];
  inviteEmail.value = '';
  inviteError.value = null;
  coOwnersDialogVisible.value = true;
  await loadCoOwners(car.id);
};

const loadCoOwners = async (carId: number) => {
  coOwnersLoading.value = true;
  try {
    const res = await http.get(`/cars/${carId}/co-owners`);
    coOwnersList.value = res.data;
  } catch {
    coOwnersList.value = [];
  } finally {
    coOwnersLoading.value = false;
  }
};

const inviteCoOwner = async () => {
  if (!coOwnersCarId.value || !inviteEmail.value.trim()) return;
  inviteLoading.value = true;
  inviteError.value = null;
  try {
    await http.post(`/cars/${coOwnersCarId.value}/co-owners/invite`, { email: inviteEmail.value.trim() });
    inviteEmail.value = '';
    await loadCoOwners(coOwnersCarId.value);
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? '';
    if (detail.includes('No account')) inviteError.value = t('car_manager_invite_error_not_found');
    else if (detail.includes('yourself')) inviteError.value = t('car_manager_invite_error_self');
    else if (detail.includes('already')) inviteError.value = t('car_manager_invite_error_duplicate');
    else inviteError.value = t('car_manager_invite_error_fallback');
  } finally {
    inviteLoading.value = false;
  }
};

const removeCoOwner = async (userId: number) => {
  if (!coOwnersCarId.value) return;
  await http.delete(`/cars/${coOwnersCarId.value}/co-owners/${userId}`);
  await loadCoOwners(coOwnersCarId.value);
};

const confirmLeaveCoOwnership = (car: Car) => {
  confirm.require({
    message: t('car_manager_leave_confirm_message'),
    header: t('car_manager_leave_confirm_header'),
    rejectLabel: t('car_manager_leave_confirm_cancel'),
    rejectProps: { label: t('car_manager_leave_confirm_cancel'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('car_manager_leave_confirm_button'), severity: 'danger' },
    accept: async () => {
      leaveLoading.value = true;
      try {
        await http.delete(`/cars/${car.id}/co-owners/leave`);
        await carStore.fetchMyCars();
      } finally {
        leaveLoading.value = false;
      }
    },
  });
};
</script>


<template>
  <Dialog v-model:visible="createCarDialogVisible" modal :header="$t('car_manager_add_car_title')">
    <div class="flex flex-col gap-4">
      <InputText v-model="newCar.name" :placeholder="$t('car_manager_car_name_placeholder')" />
      <Textarea v-model="newCar.description" :placeholder="$t('car_manager_description_placeholder')" rows="3" />

      <div>
        <p class="text-sm font-medium mb-2">{{ $t('car_manager_price_mode_label') }}</p>
        <SelectButton v-model="newCar.price_mode" :options="priceModeOptions" optionLabel="label" optionValue="value" />
      </div>

      <template v-if="newCar.price_mode === 'manual'">
        <InputNumber v-model="newCar.price_per_km" mode="decimal" :min="0" :step="0.01" :minFractionDigits="2"
          :maxFractionDigits="2" locale="en-US" :placeholder="$t('car_manager_price_per_km_placeholder')" />
      </template>

      <template v-else>
        <div>
          <p class="text-sm font-medium mb-2">{{ $t('car_manager_fuel_type_label') }}</p>
          <SelectButton v-model="newCar.fuel_type" :options="fuelTypeOptions" optionLabel="label" optionValue="value" />
        </div>

        <template v-if="newCar.fuel_type === 'electric'">
          <InputNumber v-model="newCar.calc_battery_kwh" mode="decimal" :min="0" :step="1" :minFractionDigits="0"
            :maxFractionDigits="1" locale="en-US" :placeholder="$t('car_manager_calc_battery_kwh')" />
          <InputNumber v-model="newCar.calc_range_km" mode="decimal" :min="0" :step="1" :minFractionDigits="0"
            :maxFractionDigits="0" locale="en-US" :placeholder="$t('car_manager_calc_range_km')" />
          <InputNumber v-model="newCar.calc_charge_cost_per_kwh" mode="decimal" :min="0" :step="0.01"
            :minFractionDigits="2" :maxFractionDigits="3" locale="en-US" :placeholder="$t('car_manager_calc_charge_cost')" />
        </template>

        <template v-else-if="newCar.fuel_type === 'combustion'">
          <InputNumber v-model="newCar.calc_consumption_per_100km" mode="decimal" :min="0" :step="0.1"
            :minFractionDigits="1" :maxFractionDigits="2" locale="en-US" :placeholder="$t('car_manager_calc_consumption')" />
          <InputNumber v-model="newCar.calc_fuel_price_per_liter" mode="decimal" :min="0" :step="0.01"
            :minFractionDigits="2" :maxFractionDigits="3" locale="en-US" :placeholder="$t('car_manager_calc_fuel_price')" />
        </template>

        <p v-if="newCarCalcPrice === null" class="text-xs text-surface-400">{{ $t('car_manager_calc_incomplete') }}</p>
        <InputNumber v-model="newCar.price_per_km" mode="decimal" :min="0" :step="0.01" :minFractionDigits="2"
          :maxFractionDigits="2" locale="en-US" :placeholder="$t('car_manager_price_per_km_placeholder')" />
      </template>

      <input type="file" accept="image/*" @change="onNewCarImageSelected" />
    </div>
    <template #footer>
      <Button :label="$t('car_manager_cancel')" severity="secondary" outlined @click="createCarDialogVisible = false" />
      <Button :label="$t('car_manager_save')" @click="submitCreateCar" />
    </template>
  </Dialog>

  <Dialog v-model:visible="editCarDialogVisible" :header="$t('car_manager_edit_car_title')" modal :style="{ width: '36rem' }">
    <div class="flex flex-col gap-4">
      <InputText v-model="editCar.name" :placeholder="$t('car_manager_car_name_placeholder')" />
      <Textarea v-model="editCar.description" :placeholder="$t('car_manager_description_placeholder')" rows="3" />

      <div>
        <p class="text-sm font-medium mb-2">{{ $t('car_manager_price_mode_label') }}</p>
        <SelectButton v-model="editCar.price_mode" :options="priceModeOptions" optionLabel="label" optionValue="value" />
      </div>

      <template v-if="editCar.price_mode === 'manual'">
        <InputNumber v-model="editCar.price_per_km" mode="decimal" :min="0" :step="0.01" :minFractionDigits="2"
          :maxFractionDigits="2" locale="en-US" :placeholder="$t('car_manager_price_per_km_placeholder')" />
      </template>

      <template v-else>
        <div>
          <p class="text-sm font-medium mb-2">{{ $t('car_manager_fuel_type_label') }}</p>
          <SelectButton v-model="editCar.fuel_type" :options="fuelTypeOptions" optionLabel="label" optionValue="value" />
        </div>

        <template v-if="editCar.fuel_type === 'electric'">
          <InputNumber v-model="editCar.calc_battery_kwh" mode="decimal" :min="0" :step="1" :minFractionDigits="0"
            :maxFractionDigits="1" locale="en-US" :placeholder="$t('car_manager_calc_battery_kwh')" />
          <InputNumber v-model="editCar.calc_range_km" mode="decimal" :min="0" :step="1" :minFractionDigits="0"
            :maxFractionDigits="0" locale="en-US" :placeholder="$t('car_manager_calc_range_km')" />
          <InputNumber v-model="editCar.calc_charge_cost_per_kwh" mode="decimal" :min="0" :step="0.01"
            :minFractionDigits="2" :maxFractionDigits="3" locale="en-US" :placeholder="$t('car_manager_calc_charge_cost')" />
        </template>

        <template v-else-if="editCar.fuel_type === 'combustion'">
          <InputNumber v-model="editCar.calc_consumption_per_100km" mode="decimal" :min="0" :step="0.1"
            :minFractionDigits="1" :maxFractionDigits="2" locale="en-US" :placeholder="$t('car_manager_calc_consumption')" />
          <InputNumber v-model="editCar.calc_fuel_price_per_liter" mode="decimal" :min="0" :step="0.01"
            :minFractionDigits="2" :maxFractionDigits="3" locale="en-US" :placeholder="$t('car_manager_calc_fuel_price')" />
        </template>

        <p v-if="editCarCalcPrice === null" class="text-xs text-surface-400">{{ $t('car_manager_calc_incomplete') }}</p>
        <InputNumber v-model="editCar.price_per_km" mode="decimal" :min="0" :step="0.01" :minFractionDigits="2"
          :maxFractionDigits="2" locale="en-US" :placeholder="$t('car_manager_price_per_km_placeholder')" />
      </template>

      <div>
        <p class="text-sm font-medium mb-2">{{ $t('car_manager_photos') }}</p>
        <p v-if="editImagesLoading" class="text-xs text-surface-400">{{ $t('car_manager_loading_photos') }}</p>
        <div v-else class="flex flex-wrap gap-2">
          <div v-for="img in editCarImages" :key="img.id" class="relative group w-20 h-20">
            <img :src="img.url" class="w-20 h-20 object-cover rounded" />
            <button
              class="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 rounded transition-opacity"
              @click="deleteGalleryImage(img.id)"
            >
              <i class="pi pi-trash text-white text-sm" />
            </button>
          </div>
          <button
            class="w-20 h-20 border-2 border-dashed border-surface-300 rounded flex items-center justify-center text-surface-400 hover:border-primary hover:text-primary transition-colors"
            @click="galleryFileInput?.click()"
          >
            <i class="pi pi-plus text-lg" />
          </button>
        </div>
        <input ref="galleryFileInput" type="file" accept="image/*" class="hidden" @change="onGalleryFileSelected" />
      </div>
    </div>
    <template #footer>
      <Button :label="$t('car_manager_cancel')" severity="secondary" outlined @click="editCarDialogVisible = false" />
      <Button :label="$t('car_manager_save')" @click="submitEditCar" />
    </template>
  </Dialog>

  <Dialog v-model:visible="unavailabilityDialogVisible" :header="`${$t('car_manager_block_dates_title')} — ${unavailabilityCarName}`" modal
    style="width: 32rem">
    <div class="flex flex-col gap-6">
      <div v-if="unavailabilityError" class="text-sm text-red-500">{{ unavailabilityError }}</div>

      <div>
        <h3 class="font-semibold text-sm mb-2">{{ $t('car_manager_blocked_periods') }}</h3>
        <p v-if="unavailabilityLoading" class="text-sm text-surface-500">{{ $t('car_manager_loading_blocks') }}</p>
        <p v-else-if="unavailabilityBlocks.length === 0" class="text-sm text-surface-500">
          {{ $t('car_manager_no_blocks') }}
        </p>
        <ul v-else class="space-y-2">
          <li v-for="block in unavailabilityBlocks" :key="block.id"
            class="flex items-center justify-between text-sm bg-surface-50 dark:bg-surface-800 rounded px-3 py-2">
            <span>{{ formatDate(block.start_date) }} → {{ formatDate(block.end_date) }}</span>
            <Button icon="pi pi-trash" severity="danger" text rounded size="small" @click="deleteBlock(block.id)" />
          </li>
        </ul>
      </div>

      <div class="border-t pt-4">
        <h3 class="font-semibold text-sm mb-3">{{ $t('car_manager_add_blocked_period') }}</h3>
        <DatePicker v-model="newBlockDates" selectionMode="range" showIcon :manualInput="false" fluid
          :placeholder="$t('car_manager_select_date_range')" class="mb-2" />
        <p v-if="addBlockError" class="text-xs text-red-500 mb-2">{{ addBlockError }}</p>
        <Button :label="$t('car_manager_add_block')" icon="pi pi-plus" size="small" :loading="addingBlock"
          :disabled="!newBlockDates || newBlockDates.length < 2 || !newBlockDates[1] || addingBlock"
          @click="addBlock" />
      </div>
    </div>
  </Dialog>

  <Dialog v-model:visible="coOwnersDialogVisible" :header="`${$t('car_manager_co_owners_title')} — ${coOwnersCarName}`" modal style="width: 32rem">
    <div class="flex flex-col gap-6">
      <div>
        <p v-if="coOwnersLoading" class="text-sm text-surface-500">{{ $t('car_manager_loading_blocks') }}</p>
        <p v-else-if="coOwnersList.length === 0" class="text-sm text-surface-500">{{ $t('car_manager_no_co_owners') }}</p>
        <ul v-else class="space-y-2">
          <li v-for="co in coOwnersList" :key="co.user_id"
            class="flex items-center justify-between text-sm bg-surface-50 dark:bg-surface-800 rounded px-3 py-2">
            <div>
              <span class="font-medium">{{ co.full_name }}</span>
              <span class="text-surface-400 ml-2 text-xs">{{ co.email }}</span>
              <span v-if="co.status === 'pending'" class="ml-2 text-xs text-orange-500 font-medium">{{ $t('car_manager_pending_badge') }}</span>
            </div>
            <Button icon="pi pi-times" severity="danger" text rounded size="small"
              :title="$t('car_manager_cancel_invite')"
              @click="removeCoOwner(co.user_id)" />
          </li>
        </ul>
      </div>

      <div class="border-t pt-4">
        <h3 class="font-semibold text-sm mb-3">{{ $t('car_manager_invite_button') }}</h3>
        <div class="flex gap-2">
          <InputText v-model="inviteEmail" :placeholder="$t('car_manager_invite_email_placeholder')" class="flex-1" @keyup.enter="inviteCoOwner" />
          <Button :label="$t('car_manager_invite_button')" icon="pi pi-send" size="small" :loading="inviteLoading" :disabled="!inviteEmail.trim() || inviteLoading" @click="inviteCoOwner" />
        </div>
        <p v-if="inviteError" class="text-xs text-red-500 mt-2">{{ inviteError }}</p>
      </div>
    </div>
  </Dialog>

  <div class="flex flex-col w-full">
    <Toolbar class="w-full max-w-[98%] mx-auto mt-4">
      <template #start>
        <span>{{ $t('car_manager_my_cars') }}</span>
      </template>
      <template #end>
        <Button icon="pi pi-plus" severity="contrast" rounded @click="createCarDialogVisible = true" />
      </template>
    </Toolbar>
    <div class="w-full max-w-[95%] mx-auto mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card v-for="car in cars" :key="car.id" class="overflow-hidden">
        <template #header>
          <div class="h-80 w-full">
            <CarImageCarousel :car-id="car.id" :fallback-url="car.image_url" />
          </div>
        </template>
        <template #title>
          <div class="flex items-center justify-between w-full">
            <div class="flex items-center gap-2">
              {{ car.name }}
              <Tag v-if="!isPrimaryOwner(car)" :value="$t('car_manager_co_owner_badge')" severity="secondary" />
            </div>
            <div class="flex gap-2">
              <Button icon="pi pi-calendar-times" size="small" rounded variant="text" severity="secondary"
                :title="$t('car_manager_manage_blocked_dates')" @click="openUnavailabilityDialog(car)" />
              <Button icon="pi pi-ellipsis-v" size="small" rounded variant="text" severity="contrast"
                @click="openEditDialog(car)" />
              <Button v-if="isPrimaryOwner(car)" icon="pi pi-users" size="small" rounded variant="text" severity="info"
                :title="$t('car_manager_co_owners_manage')" @click="openCoOwnersDialog(car)" />
              <Button v-if="isPrimaryOwner(car)" icon="pi pi-trash" size="small" rounded variant="outlined" severity="danger"
                @click="confirmDeleteCar(car.id)" />
              <Button v-else icon="pi pi-sign-out" size="small" rounded variant="outlined" severity="warning"
                :title="$t('car_manager_leave_co_ownership')" @click="confirmLeaveCoOwnership(car)" />
            </div>
          </div>
        </template>
        <template #content>
          {{ car.price_per_km }} € / km
        </template>
      </Card>
    </div>
  </div>
</template>
