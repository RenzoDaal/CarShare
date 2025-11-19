<script setup lang="ts">
  import Toolbar from 'primevue/toolbar';
  import logo from '../assets/logo.png';
  import Button from 'primevue/button';
  import Drawer from 'primevue/drawer';
</script>


<template>
  <div>
    <div>
      <Toolbar class="shadow-md !border-none !rounded-none">
        <template #start>
          <div class="flex items-center gap-4 ml-2">
            <Button icon="pi pi-bars" variant="text" severity="secondary" rounded/>
            <div class="flex items-center gap-1">
              <img :src="logo" alt="carshare logo" class="h-11" />
              <span class="text-xl">CarShare</span>
            </div>
          </div>
        </template>
      </Toolbar>
    </div>
  </div>
</template>
