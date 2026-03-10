<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import AutoComplete from 'primevue/autocomplete'
import Textarea from 'primevue/textarea'
import http from '@/api/http'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'

const { t } = useI18n()
const toast = useToast()

type BookingForReschedule = {
  id: number
  car: { price_per_km: number }
  start_datetime: string
  end_datetime: string
  stops?: string[] | null
  notes?: string | null
}

const props = defineProps<{
  visible: boolean
  booking: BookingForReschedule | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'rescheduled': []
}>()

function toUtcDate(value: string): Date {
  const normalized = value.endsWith('Z') || value.includes('+') ? value : value + 'Z'
  return new Date(normalized)
}

const rescheduleStart = ref<Date | null>(null)
const rescheduleEnd = ref<Date | null>(null)
const rescheduleNotes = ref('')
const rescheduleStops = ref<string[]>(['', ''])
const locationSuggestions = ref<string[]>([])
const rescheduleDistanceKm = ref<number | null>(null)
const rescheduleRouteEstimating = ref(false)
const rescheduleRouteError = ref<string | null>(null)
const rescheduleSubmitting = ref(false)
const rescheduleError = ref<string | null>(null)

const rescheduleTrimmedStops = computed(() =>
  rescheduleStops.value.map(s => s.trim()).filter(Boolean)
)

const rescheduleEstimatedPrice = computed(() => {
  const pricePerKm = props.booking?.car.price_per_km
  if (pricePerKm == null || rescheduleDistanceKm.value == null) return null
  return rescheduleDistanceKm.value * pricePerKm
})

watch(() => props.visible, (val) => {
  if (val && props.booking) {
    rescheduleStart.value = toUtcDate(props.booking.start_datetime)
    rescheduleEnd.value = toUtcDate(props.booking.end_datetime)
    rescheduleStops.value = props.booking.stops && props.booking.stops.length >= 2
      ? [...props.booking.stops]
      : ['', '']
    rescheduleNotes.value = props.booking.notes ?? ''
    rescheduleDistanceKm.value = null
    rescheduleRouteError.value = null
    rescheduleError.value = null
  }
})

watch(rescheduleStops, () => {
  rescheduleDistanceKm.value = null
  rescheduleRouteError.value = null
}, { deep: true })

function addStop() {
  rescheduleStops.value.splice(rescheduleStops.value.length - 1, 0, '')
}

function removeStop(index: number) {
  if (rescheduleStops.value.length <= 2) return
  rescheduleStops.value.splice(index, 1)
}

async function searchLocations(event: { query: string }) {
  const query = (event.query || '').trim()
  if (!query || query.length < 3) { locationSuggestions.value = []; return }
  try {
    const res = await http.get<string[]>('/locations/suggest', { params: { query } })
    locationSuggestions.value = res.data
  } catch {
    locationSuggestions.value = []
  }
}

async function estimateRoute() {
  rescheduleRouteError.value = null
  rescheduleDistanceKm.value = null
  if (rescheduleTrimmedStops.value.length < 2) {
    rescheduleRouteError.value = t('borrower_reschedule_error_route')
    return
  }
  rescheduleRouteEstimating.value = true
  try {
    const res = await http.post('/routes/estimate', { stops: rescheduleTrimmedStops.value })
    rescheduleDistanceKm.value = res.data.distance_km
  } catch (err: any) {
    rescheduleRouteError.value = err?.response?.data?.detail ?? t('borrower_reschedule_error_estimate')
  } finally {
    rescheduleRouteEstimating.value = false
  }
}

async function submitReschedule() {
  if (!props.booking || !rescheduleStart.value || !rescheduleEnd.value) return
  if (rescheduleEnd.value <= rescheduleStart.value) {
    rescheduleError.value = t('borrower_reschedule_error_end_after_start')
    return
  }
  rescheduleSubmitting.value = true
  rescheduleError.value = null
  try {
    await http.patch(`/bookings/${props.booking.id}/reschedule`, {
      start_datetime: rescheduleStart.value.toISOString(),
      end_datetime: rescheduleEnd.value.toISOString(),
      distance_km: rescheduleDistanceKm.value,
      stops: rescheduleTrimmedStops.value.length >= 2 ? rescheduleTrimmedStops.value : null,
      notes: rescheduleNotes.value || null,
    })
    emit('update:visible', false)
    emit('rescheduled')
    toast.add({ severity: 'success', summary: t('borrower_reschedule_success_toast'), life: 3000 })
  } catch (err: any) {
    rescheduleError.value = err?.response?.data?.detail ?? t('borrower_reschedule_error_submit')
  } finally {
    rescheduleSubmitting.value = false
  }
}
</script>

<template>
  <Dialog :visible="visible" @update:visible="emit('update:visible', $event)"
    :header="$t('borrower_reschedule_dialog_title')" modal :style="{ width: '42rem' }" :breakpoints="{ '640px': '95vw' }">
    <div class="flex flex-col gap-5 mt-2">
      <div class="grid gap-4 md:grid-cols-2">
        <div class="space-y-2">
          <span class="block text-sm font-medium">{{ $t('borrower_reschedule_new_start') }}</span>
          <DatePicker v-model="rescheduleStart" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5" fluid />
        </div>
        <div class="space-y-2">
          <span class="block text-sm font-medium">{{ $t('borrower_reschedule_new_end') }}</span>
          <DatePicker v-model="rescheduleEnd" showTime hourFormat="24" showIcon :manualInput="true" :stepMinute="5" fluid />
        </div>
      </div>

      <div class="space-y-3">
        <span class="block text-sm font-medium">{{ $t('borrower_reschedule_route') }}</span>
        <div v-for="(_stop, index) in rescheduleStops" :key="index" class="flex items-center gap-2">
          <div class="flex-1 min-w-0">
            <span class="block text-xs text-surface-400 mb-1">
              {{ index === 0 ? $t('borrower_start_location') : index === rescheduleStops.length - 1 ? $t('borrower_end_location') : $t('borrower_stop_label').replace('{index}', String(index)) }}
            </span>
            <AutoComplete v-model="rescheduleStops[index]" :suggestions="locationSuggestions" :minLength="3"
              :delay="300" :placeholder="$t('borrower_address_placeholder')" class="w-full" inputClass="w-full"
              @complete="searchLocations" />
          </div>
          <Button icon="pi pi-trash" severity="danger" text rounded :disabled="rescheduleStops.length <= 2" @click="removeStop(index)" />
        </div>
        <Button :label="$t('borrower_reschedule_add_stop')" icon="pi pi-plus" text size="small" @click="addStop" />
        <div class="flex items-center gap-4 flex-wrap">
          <Button :label="$t('borrower_reschedule_calculate_distance')" icon="pi pi-map" size="small"
            :loading="rescheduleRouteEstimating"
            :disabled="rescheduleRouteEstimating || rescheduleTrimmedStops.length < 2"
            @click="estimateRoute" />
          <div v-if="rescheduleDistanceKm != null" class="text-sm space-y-0.5">
            <div><span class="font-medium">{{ $t('borrower_reschedule_distance') }}</span> {{ rescheduleDistanceKm.toFixed(1) }} km</div>
            <div v-if="rescheduleEstimatedPrice != null"><span class="font-medium">{{ $t('borrower_reschedule_estimated_cost') }}</span> €{{ rescheduleEstimatedPrice.toFixed(2) }}</div>
          </div>
        </div>
        <p v-if="rescheduleRouteError" class="text-sm text-red-500">{{ rescheduleRouteError }}</p>
        <p class="text-xs text-surface-400">{{ $t('borrower_reschedule_keep_route') }}</p>
      </div>

      <div class="space-y-2">
        <span class="block text-sm font-medium">{{ $t('borrower_reschedule_notes_label') }}</span>
        <Textarea v-model="rescheduleNotes" rows="3" :placeholder="$t('borrower_reschedule_notes_placeholder')" class="w-full" fluid />
      </div>

      <p class="text-xs text-surface-400">{{ $t('borrower_reschedule_pending_warning') }}</p>
      <p v-if="rescheduleError" class="text-sm text-red-500">{{ rescheduleError }}</p>
      <div class="flex justify-end gap-2">
        <Button :label="$t('borrower_reschedule_cancel')" severity="secondary" outlined @click="emit('update:visible', false)" />
        <Button :label="$t('borrower_reschedule_confirm')" icon="pi pi-check" :loading="rescheduleSubmitting"
          :disabled="!rescheduleStart || !rescheduleEnd || rescheduleSubmitting"
          @click="submitReschedule" />
      </div>
    </div>
  </Dialog>
</template>
