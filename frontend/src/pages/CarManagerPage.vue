<script setup lang="ts">
  import Card from 'primevue/card';
  import Toolbar from 'primevue/toolbar';
  import Button from 'primevue/button';
  import Dialog from 'primevue/dialog';
  import InputText from 'primevue/inputtext';
  import Textarea from 'primevue/textarea';
  import InputNumber from 'primevue/inputnumber';

  import { useCarStore, type NewCarPayload, type UpdateCarPayload, type Car } from '@/stores/cars';
  import { onMounted, ref } from 'vue';
  import { storeToRefs } from 'pinia';
  import { useConfirm } from 'primevue/useconfirm';

  const carStore = useCarStore();
  const confirm = useConfirm();
  const { cars } = storeToRefs(carStore);

  onMounted(() => {
    carStore.fetchCars();
  })

  const createCarDialogVisible = ref(false);
  const editCarDialogVisible = ref(false);
  const editingCarId = ref<number | null>(null);
  const newCarImage = ref<File | null>(null);
  const editCarImage = ref<File | null>(null);

  const onNewCarImageSelected = (event: Event) => {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files[0]) {
      newCarImage.value = target.files[0];
    }
  };

  const onEditCarImageSelected = (event: Event) => {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files[0]) {
      editCarImage.value = target.files[0];
    }
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
  }

  const submitEditCar = async () => {
    if (editingCarId.value == null) return;
    await carStore.updateCar(editingCarId.value, editCar.value);

    if (editCarImage.value) {
      await carStore.uploadCarImage(editingCarId.value, editCarImage.value);
      editCarImage.value = null;
    }

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
</script>


<template>
  <Dialog v-model:visible="createCarDialogVisible" modal header="Add new car">
    <div class="flex flex-col gap-4">
      <InputText v-model="newCar.name" placeholder="Car name" />
      <Textarea v-model="newCar.description" placeholder="Description" rows="3" />
      <InputNumber
          v-model="newCar.price_per_km"
          mode="decimal"
          :min="0"
          placeholder="Price per km"
      />
      <input type="file" accept="image/*" @change="onNewCarImageSelected" />
    </div>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="createCarDialogVisible = false" />
      <Button label="Save" @click="submitCreateCar" />
    </template>
  </Dialog>
  <Dialog v-model:visible="editCarDialogVisible" header="Edit car" modal>
    <div class="flex flex-col gap-4">
      <InputText v-model="editCar.name" placeholder="Car name" />
      <Textarea v-model="editCar.description" placeholder="Description" rows="3" />
      <InputNumber
          v-model="editCar.price_per_km"
          mode="decimal"
          :min="0"
          placeholder="Price per km" />
      <input type="file" accept="image/*" @change="onEditCarImageSelected" />
    </div>
    <template #footer>
      <Button
          label="Cancel"
          severity="secondary"
          outlined
          @click="editCarDialogVisible = false" />
      <Button
          label="Save"
          @click="submitEditCar" />
    </template>
  </Dialog>
  <div class="flex flex-col w-full">
    <Toolbar class="w-full max-w-[98%] mx-auto mt-4">
      <template #start>
        <span>My cars</span>
      </template>
      <template #end>
        <Button 
          icon="pi pi-plus" 
          severity="contrast" 
          rounded 
          @click="createCarDialogVisible = true"
        />
      </template>
    </Toolbar>
    <div class="w-full max-w-[95%] mx-auto mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card v-for="car in cars" :key="car.id">
        <template #header>
          <img
            v-if="car.image_url"
            :src="car.image_url"
            alt=""
            class="w-full h-72 object-cover rounded-md"
        </template>
        <template #title>
          <div class="flex items-center justify-between w-full">
            {{ car.name }}
            <div class="flex gap-2">
              <Button 
                icon="pi pi-ellipsis-v" 
                size="small" 
                rounded 
                variant="text"
                severity="contrast"
                @click="openEditDialog(car)"/>
              <Button
                icon="pi pi-trash"
                size="small"
                rounded
                variant="outlined"
                severity="danger"
                @click="confirmDeleteCar(car.id)"/>
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
