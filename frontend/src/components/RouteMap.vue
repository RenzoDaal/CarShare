<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import L, { Map as LeafletMap, Polyline as LeafletPolyline } from 'leaflet';
import type { LatLngExpression } from 'leaflet';

const props = defineProps<{
  coordinates: [number, number][]; // [lat, lon]
}>();

const mapContainer = ref<HTMLDivElement | null>(null);
let map: LeafletMap | null = null;
let polyline: LeafletPolyline | null = null;

// Default center if no route yet (NL-ish)
const DEFAULT_CENTER: LatLngExpression = [52.1, 5.1];
const DEFAULT_ZOOM_NO_ROUTE = 7;
const DEFAULT_ZOOM_ROUTE = 10;

const initMap = () => {
  if (!mapContainer.value) return;

  const hasRoute = props.coordinates.length > 0;
  const center: LatLngExpression = hasRoute
    ? props.coordinates[0]
    : DEFAULT_CENTER;

  map = L.map(mapContainer.value).setView(
    center,
    hasRoute ? DEFAULT_ZOOM_ROUTE : DEFAULT_ZOOM_NO_ROUTE
  );

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map);

  if (hasRoute) {
    polyline = L.polyline(props.coordinates as LatLngExpression[]).addTo(map);
    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
  }
};

onMounted(() => {
  initMap();
});

watch(
  () => props.coordinates,
  (newCoords) => {
    if (!map) return;

    // No coords: remove route if present, keep base map
    if (!newCoords.length) {
      if (polyline) {
        map.removeLayer(polyline);
        polyline = null;
      }
      return;
    }

    // Coords present: add/update route
    if (polyline) {
      polyline.setLatLngs(newCoords as LatLngExpression[]);
    } else {
      polyline = L.polyline(newCoords as LatLngExpression[]).addTo(map);
    }
    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
  },
  { deep: true }
);

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
    polyline = null;
  }
});
</script>

<template>
  <div
    ref="mapContainer"
    class="w-full h-full rounded-xl overflow-hidden"
  />
</template>
