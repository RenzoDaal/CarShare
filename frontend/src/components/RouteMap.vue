<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from "vue";
import L, { Map as LeafletMap, Polyline as LeafletPolyline } from "leaflet";
import type { LatLngExpression } from "leaflet";

const props = defineProps<{
  coordinates: [number, number][]; // [lat, lon]
}>();

const mapContainer = ref<HTMLDivElement | null>(null);
let map: LeafletMap | null = null;
let polyline: LeafletPolyline | null = null;
let resizeObserver: ResizeObserver | null = null;

// Default center if no route yet (NL-ish)
const DEFAULT_CENTER: LatLngExpression = [52.1, 5.1];
const DEFAULT_ZOOM_NO_ROUTE = 7;
const DEFAULT_ZOOM_ROUTE = 10;

const initMap = () => {
  if (!mapContainer.value || map) return;

  const hasRoute = props.coordinates.length > 0;

  const center: LatLngExpression =
    hasRoute && props.coordinates[0] ? (props.coordinates[0] as LatLngExpression) : DEFAULT_CENTER;

  map = L.map(mapContainer.value).setView(
    center,
    hasRoute ? DEFAULT_ZOOM_ROUTE : DEFAULT_ZOOM_NO_ROUTE
  );

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  if (hasRoute) {
    polyline = L.polyline(props.coordinates as LatLngExpression[]).addTo(map);
    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
  }
};

const refreshSize = () => {
  if (!map) return;
  map.invalidateSize();
};

onMounted(async () => {
  // Ensure the DOM is painted before initializing
  await nextTick();
  initMap();

  // Critical: invalidate size once after mount (Stepper panels often start hidden)
  requestAnimationFrame(() => refreshSize());

  // Critical: keep it correct when the StepPanel becomes visible / resizes
  if (mapContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      refreshSize();
    });
    resizeObserver.observe(mapContainer.value);
  }
});

watch(
  () => props.coordinates,
  async (newCoords) => {
    if (!map) return;

    // If the panel just became visible, ensure Leaflet knows the real size
    await nextTick();
    refreshSize();

    if (!newCoords.length) {
      if (polyline) {
        map.removeLayer(polyline);
        polyline = null;
      }
      return;
    }

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
  if (resizeObserver && mapContainer.value) {
    resizeObserver.unobserve(mapContainer.value);
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (map) {
    map.remove();
    map = null;
    polyline = null;
  }
});
</script>

<template>
  <div ref="mapContainer" class="w-full h-full rounded-xl overflow-hidden" />
</template>
