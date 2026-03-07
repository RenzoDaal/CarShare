<script setup lang="ts">
import Card from 'primevue/card';
import Toolbar from 'primevue/toolbar';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import InputNumber from 'primevue/inputnumber';
import DatePicker from 'primevue/datepicker';

import { useCarStore, type NewCarPayload, type UpdateCarPayload, type Car } from '@/stores/cars';
import { formatDateOnly } from '@/utils/formatDate';
import CarImageCarousel from '@/components/CarImageCarousel.vue';
import { onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useConfirm } from 'primevue/useconfirm';
import http from '@/api/http';

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
});

const editCar = ref<UpdateCarPayload>({
  name: '',
  description: '',
  price_per_km: 0,
  is_active: true,
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
  };
}

const openEditDialog = (car: Car) => {
  editingCarId.value = car.id;
  editCar.value = {
    name: car.name,
    description: car.description ?? '',
    price_per_km: car.price_per_km,
    is_active: car.is_active,
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
    message: 'Do you want to delete this car?',
    header: 'Confirmation',
    icon: 'pi pi-info-circle',
    rejectLabel: 'Cancel',
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Delete',
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
    unavailabilityError.value = err?.response?.data?.detail ?? 'Failed to load unavailability blocks.';
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
    addBlockError.value = 'Please select a start and end date.';
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
    addBlockError.value = err?.response?.data?.detail ?? 'Failed to add block.';
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
    unavailabilityError.value = err?.response?.data?.detail ?? 'Failed to delete block.';
  }
};

const formatDate = (iso: string) => formatDateOnly(iso + 'T00:00:00');
</script>


<template>
  <Dialog v-model:visible="createCarDialogVisible" modal header="Add new car">
    <div class="flex flex-col gap-4">
      <InputText v-model="newCar.name" placeholder="Car name" />
      <Textarea v-model="newCar.description" placeholder="Description" rows="3" />
      <InputNumber v-model="newCar.price_per_km" mode="decimal" :min="0" :step="0.01" :minFractionDigits="2"
        :maxFractionDigits="2" locale="en-US" placeholder="Price per km" />
      <input type="file" accept="image/*" @change="onNewCarImageSelected" />
    </div>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="createCarDialogVisible = false" />
      <Button label="Save" @click="submitCreateCar" />
    </template>
  </Dialog>

  <Dialog v-model:visible="editCarDialogVisible" header="Edit car" modal :style="{ width: '36rem' }">
    <div class="flex flex-col gap-4">
      <InputText v-model="editCar.name" placeholder="Car name" />
      <Textarea v-model="editCar.description" placeholder="Description" rows="3" />
      <InputNumber v-model="editCar.price_per_km" mode="decimal" :min="0" :step="0.01" :minFractionDigits="2"
        :maxFractionDigits="2" locale="en-US" placeholder="Price per km" />

      <div>
        <p class="text-sm font-medium mb-2">Photos</p>
        <p v-if="editImagesLoading" class="text-xs text-surface-400">Loading…</p>
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
      <Button label="Cancel" severity="secondary" outlined @click="editCarDialogVisible = false" />
      <Button label="Save" @click="submitEditCar" />
    </template>
  </Dialog>

  <Dialog v-model:visible="unavailabilityDialogVisible" :header="`Block dates — ${unavailabilityCarName}`" modal
    style="width: 32rem">
    <div class="flex flex-col gap-6">
      <div v-if="unavailabilityError" class="text-sm text-red-500">{{ unavailabilityError }}</div>

      <div>
        <h3 class="font-semibold text-sm mb-2">Blocked periods</h3>
        <p v-if="unavailabilityLoading" class="text-sm text-surface-500">Loading…</p>
        <p v-else-if="unavailabilityBlocks.length === 0" class="text-sm text-surface-500">
          No dates blocked — car is fully available.
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
        <h3 class="font-semibold text-sm mb-3">Add blocked period</h3>
        <DatePicker v-model="newBlockDates" selectionMode="range" showIcon :manualInput="false" fluid
          placeholder="Select date range" class="mb-2" />
        <p v-if="addBlockError" class="text-xs text-red-500 mb-2">{{ addBlockError }}</p>
        <Button label="Add block" icon="pi pi-plus" size="small" :loading="addingBlock"
          :disabled="!newBlockDates || newBlockDates.length < 2 || !newBlockDates[1] || addingBlock"
          @click="addBlock" />
      </div>
    </div>
  </Dialog>

  <div class="flex flex-col w-full">
    <Toolbar class="w-full max-w-[98%] mx-auto mt-4">
      <template #start>
        <span>My cars</span>
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
            {{ car.name }}
            <div class="flex gap-2">
              <Button icon="pi pi-calendar-times" size="small" rounded variant="text" severity="secondary"
                title="Manage blocked dates" @click="openUnavailabilityDialog(car)" />
              <Button icon="pi pi-ellipsis-v" size="small" rounded variant="text" severity="contrast"
                @click="openEditDialog(car)" />
              <Button icon="pi pi-trash" size="small" rounded variant="outlined" severity="danger"
                @click="confirmDeleteCar(car.id)" />
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
