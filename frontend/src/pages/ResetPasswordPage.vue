<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Password from 'primevue/password';
import http from '@/api/http';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
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
    error.value = t('reset_password_error_invalid_link');
  }
});

async function submit() {
  error.value = null;
  if (newPassword.value !== confirmPassword.value) {
    error.value = t('reset_password_error_no_match');
    return;
  }
  if (newPassword.value.length < 6) {
    error.value = t('reset_password_error_min_length');
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
    error.value = err?.response?.data?.detail ?? t('reset_password_error_fallback');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="flex-1 flex justify-center items-center min-h-screen px-4 bg-gradient-to-br from-primary/5 via-transparent to-surface-100 dark:from-primary/10 dark:via-surface-950 dark:to-surface-900">
    <Card class="w-full max-w-sm">
      <template #title>{{ $t('reset_password_title') }}</template>
      <template #content>
        <div class="flex flex-col mt-4 w-full gap-4">
          <template v-if="!success">
            <Password v-model="newPassword" :feedback="false" toggleMask class="w-full"
              inputClass="w-full" :inputProps="{ placeholder: $t('reset_password_new_placeholder') }" />
            <Password v-model="confirmPassword" :feedback="false" toggleMask class="w-full"
              inputClass="w-full" :inputProps="{ placeholder: $t('reset_password_confirm_placeholder') }" />
            <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
            <Button :label="$t('reset_password_button')" icon="pi pi-lock" iconPos="right"
              :loading="submitting" :disabled="!newPassword || !confirmPassword || !!error && !newPassword"
              @click="submit" />
          </template>

          <template v-else>
            <p class="text-sm text-green-600">{{ $t('reset_password_success') }}</p>
            <Button :label="$t('reset_password_go_to_login')" icon="pi pi-sign-in" iconPos="right"
              @click="router.push({ name: 'login' })" />
          </template>
        </div>
      </template>
    </Card>
  </div>
</template>
