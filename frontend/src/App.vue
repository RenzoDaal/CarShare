<script setup lang="ts">
  import MenubarAndDrawer from '@/snippets/MenubarAndDrawer.vue';
  import { useRoute } from 'vue-router';
  import ConfirmDialog from 'primevue/confirmdialog';
  
  const route = useRoute();
</script>


<template>
  <div class="h-screen flex flex-col">
    <MenubarAndDrawer v-if="!route.meta.hideLayout"/>
    <ConfirmDialog />
    <div class="flex-1 flex">
      <router-view />
    </div>
  </div>
</template>
