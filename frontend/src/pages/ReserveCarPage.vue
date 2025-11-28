<script setup lang="ts">
  import InputText from 'primevue/inputtext';
  import Card from 'primevue/card';
  import DatePicker from 'primevue/datepicker';
  import Button from 'primevue/button';
  import Step from 'primevue/step';
  import Stepper from 'primevue/stepper';
  import StepList from 'primevue/steplist';
  import StepPanels from 'primevue/steppanels';
  import StepPanel from 'primevue/steppanel';

  import { ref, computed } from 'vue';
  import type { Car } from '@/stores/cars';
  import { useRouter } from 'vue-router';
  import { useAuthStore } from '@/stores/auth';

  import http from '@/api/http';

  const router = useRouter();
  const auth = useAuthStore();

  const bookingError = ref<string | null>(null);
  const bookingCompleted = ref(false);
  const bookingSubmitting = ref(false);

  // Step 1: Dates & Times
  const start = ref<Date | null>(null);
  const end = ref<Date | null>(null);
  const loadingCars = ref(false);
  const datesError = ref<string | null>(null);

  const canGoNextFromDates = computed(() => {
    if (!start.value || !end.value)
    {
      return false;
    }
    return end.value > start.value;
  })

  const handleDatesNext = async (activateCallback: (step: number) => void) => {
    if (!canGoNextFromDates.value) {
      datesError.value = 'Please pick a valid start and end datetime.';
      return;
    }
    await loadAvailableCars();
    if (!datesError.value) {
      activateCallback(2);
    }
  };

  // Step 2: available cars
  const availableCars = ref<Car[]>([]);
  const selectedCar = ref<Car | null>(null);

  const handleSelectCar = (car: Car, activateCallback: (step: number) => void) => {
    selectedCar.value = car;
    bookingCompleted.value = false;
    bookingError.value = null;
    activateCallback(3);
  };

  // Step 3: confirmation
  const fullName = ref(auth.user?.full_name ?? '');
  const email = ref(auth.user?.email ?? '');

  const resetFlow = () => {
    start.value = null;
    end.value = null;
    datesError.value = null;
    availableCars.value = [];
    selectedCar.value = null;
    bookingCompleted.value = false;
    bookingError.value = null;
    fullName.value = auth.user?.full_name ?? '';
    email.value = auth.user?.email ?? '';
  };

  const loadAvailableCars = async () => {
    if (!start.value || !end.value)
    {
      return;
    }
    loadingCars.value = true;
    datesError.value = null;

    try {
      const res = await http.get<Car[]>('/cars/available', {
        params: {
          start_datetime: start.value.toISOString(),
          end_datetime: end.value.toISOString()
        }
      });
      availableCars.value = res.data;
    } catch (err: any) {
      datesError.value = err?.response?.data?.detail ?? 'Failed to load available cars.';
      availableCars.value = [];
    } finally {
      loadingCars.value = false;
    }
  };

  const hasAvailableCars = computed(() => availableCars.value.length > 0);

  const canSubmitBooking = computed(() => {
    return !!selectedCar.value && !!start.value && !!end.value && !bookingSubmitting.value;
  });

  const submitBooking = async () => {
    if (!auth.user) {
      bookingError.value = 'You must be logged in to create a reservation.';
      return;
    }
    if (!selectedCar.value || !start.value || !end.value) {
      return;
    }

    bookingSubmitting.value = true;
    bookingError.value = null;
    bookingCompleted.value = false;

    try {
      await http.post('/bookings', null, {
        params: {
          borrower_id: auth.user.id,
          car_id: selectedCar.value.id,
          start_datetime: start.value.toISOString(),
          end_datetime: end.value.toISOString()
        }
      });

      bookingCompleted.value = true;
    } catch (err: any) {
      bookingError.value = err?.response?.data?.detail ?? 'Failed to complete booking.';
    } finally {
      bookingSubmitting.value = false;
    }
  };
</script>

<template>
  <div class="flex-1 flex items-center justify-center w-full">
    <Card class="w-full max-w-[95%]">
      <template #title>
        <div class="flex items-center justify-between">
          <span>Reserve a car</span>
        </div>
      </template>

      <template #content>
        <Stepper :value="1" linear class="w-full">
          <StepList>
            <Step :value="1">Dates & Time</Step>
            <Step :value="2">Select Car</Step>
            <Step :value="3">Confirm</Step>
          </StepList>
          
          <StepPanels>
            <StepPanel v-slot="{ activateCallback }" :value="1">
              <div class="flex flex-col gap-6">
                <div class="grid gap-4 md:grid-cols-2">
                  <div class="space-y-2">
                    <span class="block text-sm font-medium">Start</span>
                    <DatePicker
                      v-model="start"
                      showTime
                      hourFormat="24"
                      showIcon
                      :manualInput="false"
                      fluid
                      inline
                    />
                  </div>

                  <div class="space-y-2">
                    <span class="block text-sm font-medium">End</span>
                    <DatePicker
                      v-model="end"
                      showTime
                      hourFormat="24"
                      showIcon
                      :manualInput="false"
                      fluid
                      inline
                    />
                  </div>
                </div>

                <div v-if="datesError" class="text-sm text-red-500">
                  {{ datesError }}
                </div>

                <div class="flex justify-end gap-2">
                  <Button
                    label="Next"
                    icon="pi pi-arrow-right"
                    iconPos="right"
                    :disabled="!canGoNextFromDates || loadingCars"
                    :loading="loadingCars"
                    @click="handleDatesNext(activateCallback)"
                  />
                </div>
              </div>
            </StepPanel>

            <StepPanel v-slot="{ activateCallback }" :value="2">
              <div class="flex flex-col gap-6">
                <div
                  v-if="!hasAvailableCars && !loadingCars"
                  class="text-sm text-surface-500"
                >
                  No cars are available for the selected dates.<br />
                  You can go back and pick different dates.
                </div>

                <div
                  v-else
                  class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
                >
                  <Card
                    v-for="car in availableCars"
                    :key="car.id"
                    class="flex flex-col justify-between"
                  >
                    <template #title>
                      <div class="flex flex-col gap-1">
                        <span class="font-semibold">{{ car.name }}</span>
                        <span class="text-sm text-surface-500">
                          {{ car.price_per_km }} € / km
                        </span>
                      </div>
                    </template>

                    <template #content>
                      <p class="text-sm text-surface-600 mb-4">
                        {{ car.description || 'No description provided.' }}
                      </p>
                      <div class="flex justify-end">
                        <Button
                          label="Select"
                          size="small"
                          @click="handleSelectCar(car, activateCallback)"
                        />
                      </div>
                    </template>
                  </Card>
                </div>

                <div class="flex justify-between">
                  <Button
                    label="Previous"
                    icon="pi pi-arrow-left"
                    severity="secondary"
                    outlined
                    @click="activateCallback(1)"
                  />
                </div>
              </div>
            </StepPanel>

            <StepPanel v-slot="{ activateCallback }" :value="3">
              <div class="flex flex-col gap-6">
                <div class="space-y-2">
                  <h2 class="font-semibold text-base">Reservation summary</h2>
                  <div v-if="selectedCar" class="text-sm space-y-1">
                    <div>
                      <span class="font-medium">Car:</span>
                      <span class="ml-2">{{ selectedCar.name }}</span>
                    </div>
                    <div>
                      <span class="font-medium">Price per km:</span>
                      <span class="ml-2">
                        {{ selectedCar.price_per_km }} € / km
                      </span>
                    </div>
                  </div>

                  <div v-if="start && end" class="text-sm space-y-1">
                    <div>
                      <span class="font-medium">Start:</span>
                      <span class="ml-2">{{ start.toLocaleString() }}</span>
                    </div>
                    <div>
                      <span class="font-medium">End:</span>
                      <span class="ml-2">{{ end.toLocaleString() }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="!bookingCompleted" class="space-y-4">
                  <h2 class="font-semibold text-base">Your details</h2>
                  <div class="space-y-2">
                    <span class="block text-sm font-medium">Name</span>
                    <InputText v-model="fullName" class="w-full" />
                  </div>

                  <div class="space-y-2">
                    <span class="block text-sm font-medium">Email</span>
                    <InputText v-model="email" class="w-full" />
                  </div>

                  <div v-if="bookingError" class="text-sm text-red-500">
                    {{ bookingError }}
                  </div>

                  <div class="flex justify-between">
                    <Button
                      label="Previous"
                      icon="pi pi-arrow-left"
                      severity="secondary"
                      outlined
                      @click="activateCallback(2)"
                    />
                    <Button
                      label="Confirm reservation"
                      icon="pi pi-check"
                      :disabled="!canSubmitBooking"
                      :loading="bookingSubmitting"
                      @click="submitBooking"
                    />
                  </div>
                </div>
                
                <div v-else class="space-y-4">
                  <div class="text-sm text-emerald-600">
                    Booking successful!
                    <br />
                    A confirmation email has been sent.
                  </div>
                  
                  <div class="flex gap-2">
                    <Button
                      label="Make another reservation"
                      @click="() => { resetFlow(); activateCallback(1); }"
                    />
                    <Button
                      label="Go to homepage"
                      severity="secondary"
                      outlined
                      @click="router.push({ name: 'home' })"
                    />
                  </div>
                </div>
              </div>
            </StepPanel>
          </StepPanels>
        </Stepper>
      </template>
    </Card>
  </div>
</template>
