<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Password from 'primevue/password';
import http from '@/api/http';

const router = useRouter();
const route = useRoute();

const token = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const submitting = ref(false);
const success = ref(false);
const error = ref<string | null>(null);

onMounted(() => {
  token.value = String(route.query.token ?? '');
  if (!token.value) {
    error.value = 'Invalid reset link.';
  }
});

async function submit() {
  error.value = null;
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Passwords do not match.';
    return;
  }
  if (newPassword.value.length < 6) {
    error.value = 'Password must be at least 6 characters.';
    return;
  }
  submitting.value = true;
  try {
    await http.post('/auth/reset-password', {
      token: token.value,
      new_password: newPassword.value,
    });
    success.value = true;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to reset password.';
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="flex-1 flex justify-center items-center h-screen">
    <Card>
      <template #title>Set new password</template>
      <template #content>
        <div class="flex flex-col mt-4 w-96 gap-4">
          <template v-if="!success">
            <Password v-model="newPassword" :feedback="false" toggleMask class="w-full"
              inputClass="w-full" :inputProps="{ placeholder: 'New password' }" />
            <Password v-model="confirmPassword" :feedback="false" toggleMask class="w-full"
              inputClass="w-full" :inputProps="{ placeholder: 'Confirm new password' }" />
            <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
            <Button label="Set new password" icon="pi pi-lock" iconPos="right"
              :loading="submitting" :disabled="!newPassword || !confirmPassword || !!error && !newPassword"
              @click="submit" />
          </template>

          <template v-else>
            <p class="text-sm text-green-600">Password reset successfully.</p>
            <Button label="Go to login" icon="pi pi-sign-in" iconPos="right"
              @click="router.push({ name: 'login' })" />
          </template>
        </div>
      </template>
    </Card>
  </div>
</template>
