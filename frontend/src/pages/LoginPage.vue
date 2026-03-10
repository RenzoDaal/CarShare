<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Checkbox from 'primevue/checkbox';
import Message from 'primevue/message';
import { Form } from '@primevue/forms';
import { z } from 'zod';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { stringFromNullish } from '@/utils/zod';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const form = reactive({
  email: '',
  password: '',
});

const rememberMe = ref(false);

const resolver = ref(
  zodResolver(
    z.object({
      email: stringFromNullish(
        z.string().min(1, { message: t('login_error_email_required') })
      ),
      password: stringFromNullish(
        z.string().min(1, { message: t('login_error_password_required') })
      ),
    })
  )
);

const onFormSubmit = async ({ valid }: { valid: boolean }) => {
  if (!valid) return;

  try {
    await auth.login({
      email: form.email,
      password: form.password,
    }, rememberMe.value);
    router.push({ name: 'home' });
  } catch (e) {
    // auth.error is already set in the store and shown in the template
  }
};
</script>

<template>
  <div class="flex-1 flex justify-center items-center min-h-screen px-4 bg-gradient-to-br from-primary/5 via-transparent to-surface-100 dark:from-primary/10 dark:via-surface-950 dark:to-surface-900">
    <Card class="w-full max-w-sm">
      <template #title>{{ $t('login_title') }}</template>
      <template #content>
        <Form :resolver="resolver" @submit="onFormSubmit" v-slot="$form">
          <div class="flex flex-col mt-4 w-full">
            <!-- Email -->
            <div class="flex flex-col gap-1 mb-4">
              <InputText name="email" v-model="form.email" :placeholder="$t('login_email_placeholder')" />
              <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
                {{ $form.email.error?.message }}
              </Message>
            </div>

            <!-- Password -->
            <div class="flex flex-col gap-1 mb-4">
              <Password name="password" v-model="form.password" :feedback="false" toggleMask class="w-full"
                inputClass="w-full" :inputProps="{ placeholder: $t('login_password_placeholder') }" />
              <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
                {{ $form.password.error?.message }}
              </Message>
            </div>

            <!-- Remember me -->
            <div class="flex items-center gap-2 mb-4">
              <Checkbox v-model="rememberMe" :binary="true" inputId="rememberMe" />
              <label for="rememberMe" class="text-sm">{{ $t('login_remember_me') }}</label>
            </div>

            <!-- Backend auth error -->
            <p v-if="auth.error" class="text-red-500 text-sm mb-2">
              {{ auth.error }}
            </p>

            <Button type="submit" :label="$t('login_button')" icon="pi pi-sign-in" iconPos="right" :loading="auth.loading" />

            <p class="mt-3 text-sm text-center">
              <RouterLink :to="{ name: 'forgot-password' }" class="text-blue-500 hover:underline">
                {{ $t('login_forgot_password') }}
              </RouterLink>
            </p>

            <p class="mt-2 text-sm text-center">
              {{ $t('login_no_account') }}
              <RouterLink :to="{ name: 'register' }" class="text-blue-500 hover:underline">
                {{ $t('login_create_account') }}
              </RouterLink>
            </p>
          </div>
        </Form>
      </template>
    </Card>
  </div>
</template>
