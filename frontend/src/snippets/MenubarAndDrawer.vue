<script setup lang="ts">
  import Toolbar from 'primevue/toolbar';
  import Button from 'primevue/button';
  import Menu from 'primevue/menu';
  import Drawer from 'primevue/drawer';
  import Logo from '@/assets/logo.svg';

  import { ref, computed } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '../stores/auth';

  const auth = useAuthStore();
  const router = useRouter()

  const drawerVisible = ref(false);
  const isCarOwner = computed(() => auth.user?.role_owner ?? false);
  const isCarBorrower = computed(() => auth.user?.role_borrower ?? false);
  const homeDrawerItems = ref([
    {
      label: 'Home',
      items: [
        {
          label: 'Dashboard',
          icon: 'pi pi-home',
          command: () => {
            router.push({ name: 'home' });
            drawerVisible.value = false;
          },
        }
      ]
    }
  ])

  const carOwnerDrawerItems = ref([
    { 
      label: 'Owner', 
      items: [
        {
          label: 'Manage Cars',
          icon: 'pi pi-car', 
          command: () => {
            router.push({ name: 'manage cars' }); 
            drawerVisible.value = false;
          }
        },
        {
          label: 'Appointments',
          icon: "pi pi-calendar",
          command: () => {
            router.push({ name: 'ownerappointments' });
            drawerVisible.value = false;
          }
        }
      ]
    }
  ]);

  const carBorrowerDrawerItems = ref([
    {
      label: 'Borrower',
      items: [
        {
          label: 'Reserve',
          icon: 'pi pi-calendar',
          command: () => {
            router.push({ name: 'reserve car' });
            drawerVisible.value = false;
          }
        },
        {
          label: 'My appointments',
          icon: 'pi pi-calendar',
          command:() => {
            router.push({ name: 'borrowerappointments' });
            drawerVisible.value = false;
          }
        },
        {
          label: 'Availability',
          icon: 'pi pi-calendar-clock',
          command: () => {
            router.push({ name: 'availability' });
            drawerVisible.value = false;
          }
        }
      ]
    }
  ]); 
</script>


<template>
  <Drawer v-model:visible="drawerVisible">
    <template #container>
      <Menu class="!border-none" :model=homeDrawerItems />
      <Menu class="!border-none" :model="carOwnerDrawerItems" v-if="isCarOwner"/>
      <Menu class="!border-none" :model="carBorrowerDrawerItems" v-if="isCarBorrower"/>
    </template>
  </Drawer>
  <div>
    <Toolbar class="!border-none !rounded-none">
      <template #start>
        <div class="flex items-center gap-4 ml-2">
          <Button 
            icon="pi pi-bars" 
            variant="text" 
            severity="secondary" 
            rounded
            @click="drawerVisible = true"
          />
          <div class="flex items-center gap-1">
            <Logo class="h-11 w-auto text-primary" />
          </div>
        </div>
      </template>
    </Toolbar>
  </div>
</template>
