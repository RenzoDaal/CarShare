<script setup lang="ts">
import { reactive, ref } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Checkbox from 'primevue/checkbox';
import Message from 'primevue/message';
import { useAuthStore } from '@/stores/auth';
import http from '@/api/http';
import type { User } from '@/stores/auth';

const auth = useAuthStore();

// Profile form
const profile = reactive({
  full_name: auth.user?.full_name ?? '',
  email: auth.user?.email ?? '',
  role_owner: auth.user?.role_owner ?? false,
  role_borrower: auth.user?.role_borrower ?? true,
});
const profileSaving = ref(false);
const profileSuccess = ref(false);
const profileError = ref<string | null>(null);

async function saveProfile() {
  profileSaving.value = true;
  profileError.value = null;
  profileSuccess.value = false;
  try {
    const { data } = await http.patch<User>('/users/me', {
      full_name: profile.full_name,
      email: profile.email,
      role_owner: profile.role_owner,
      role_borrower: profile.role_borrower,
    });
    auth.updateUser(data);
    profileSuccess.value = true;
  } catch (err: any) {
    profileError.value = err?.response?.data?.detail ?? 'Failed to save profile';
  } finally {
    profileSaving.value = false;
  }
}

// Password change form
const passwords = reactive({
  current: '',
  next: '',
  confirm: '',
});
const passwordSaving = ref(false);
const passwordSuccess = ref(false);
const passwordError = ref<string | null>(null);

async function changePassword() {
  passwordError.value = null;
  passwordSuccess.value = false;
  if (passwords.next !== passwords.confirm) {
    passwordError.value = 'New passwords do not match';
    return;
  }
  if (passwords.next.length < 6) {
    passwordError.value = 'New password must be at least 6 characters';
    return;
  }
  passwordSaving.value = true;
  try {
    await http.post('/users/me/change-password', {
      current_password: passwords.current,
      new_password: passwords.next,
    });
    passwords.current = '';
    passwords.next = '';
    passwords.confirm = '';
    passwordSuccess.value = true;
  } catch (err: any) {
    passwordError.value = err?.response?.data?.detail ?? 'Failed to change password';
  } finally {
    passwordSaving.value = false;
  }
}
</script>

<template>
  <div class="p-4 flex flex-col gap-4 max-w-xl mx-auto w-full">
    <h1 class="text-2xl font-semibold mb-2">My profile</h1>

    <!-- Profile details -->
    <Card>
      <template #title>Account details</template>
      <template #content>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium">Full name</label>
            <InputText v-model="profile.full_name" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium">Email</label>
            <InputText v-model="profile.email" />
          </div>
          <div class="flex flex-col gap-2">
            <span class="text-sm font-medium">Roles</span>
            <div class="flex items-center gap-2">
              <Checkbox v-model="profile.role_owner" :binary="true" inputId="profile_role_owner" />
              <label for="profile_role_owner" class="text-sm">I want to list my own cars</label>
            </div>
            <div class="flex items-center gap-2">
              <Checkbox v-model="profile.role_borrower" :binary="true" inputId="profile_role_borrower" />
              <label for="profile_role_borrower" class="text-sm">I want to borrow cars</label>
            </div>
          </div>

          <Message v-if="profileError" severity="error" :closable="false">{{ profileError }}</Message>
          <Message v-if="profileSuccess" severity="success" :closable="false">Profile saved.</Message>

          <div class="flex justify-end">
            <Button label="Save" icon="pi pi-check" :loading="profileSaving" @click="saveProfile" />
          </div>
        </div>
      </template>
    </Card>

    <!-- Change password -->
    <Card>
      <template #title>Change password</template>
      <template #content>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium">Current password</label>
            <Password v-model="passwords.current" :feedback="false" toggleMask class="w-full" inputClass="w-full" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium">New password</label>
            <Password v-model="passwords.next" :feedback="false" toggleMask class="w-full" inputClass="w-full" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium">Confirm new password</label>
            <Password v-model="passwords.confirm" :feedback="false" toggleMask class="w-full" inputClass="w-full" />
          </div>

          <Message v-if="passwordError" severity="error" :closable="false">{{ passwordError }}</Message>
          <Message v-if="passwordSuccess" severity="success" :closable="false">Password changed successfully.</Message>

          <div class="flex justify-end">
            <Button label="Change password" icon="pi pi-lock" :loading="passwordSaving" @click="changePassword" />
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>
