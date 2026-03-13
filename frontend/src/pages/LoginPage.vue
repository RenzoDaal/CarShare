<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
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
import Logo from '@/assets/logo.svg';

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
    await auth.login({ email: form.email, password: form.password }, rememberMe.value);
    router.push({ name: 'home' });
  } catch {
    // auth.error is set in the store
  }
};
</script>

<template>
  <div class="min-h-screen flex">
    <!-- Left brand panel (desktop only) -->
    <div class="hidden lg:flex lg:w-[45%] xl:w-1/2 bg-gradient-to-br from-primary via-primary/90 to-primary/70 flex-col items-center justify-center p-12 text-white relative overflow-hidden">
      <!-- Background decoration -->
      <div class="absolute inset-0 overflow-hidden pointer-events-none">
        <div class="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/5" />
        <div class="absolute -bottom-12 -left-12 w-64 h-64 rounded-full bg-white/5" />
        <div class="absolute top-1/2 left-1/4 w-48 h-48 rounded-full bg-white/5" />
      </div>

      <div class="relative z-10 max-w-sm w-full">
        <div class="flex items-center gap-3 mb-10">
          <Logo class="h-12 w-auto text-white" />
          <span class="font-bold text-2xl tracking-tight">CarShare</span>
        </div>

        <h1 class="text-4xl font-bold mb-4 leading-tight">
          Samen rijden.<br>Slim delen.
        </h1>
        <p class="text-white/75 text-lg mb-12 leading-relaxed">
          Deel jouw auto of reserveer een rit — eenvoudig, eerlijk en flexibel.
        </p>

        <div class="space-y-4">
          <div class="flex items-start gap-4 bg-white/10 backdrop-blur-sm rounded-2xl p-4">
            <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0 mt-0.5">
              <i class="pi pi-car text-lg" />
            </div>
            <div>
              <p class="font-semibold mb-0.5">Verhuur jouw auto</p>
              <p class="text-sm text-white/65">Verdien geld wanneer jij de auto niet gebruikt</p>
            </div>
          </div>
          <div class="flex items-start gap-4 bg-white/10 backdrop-blur-sm rounded-2xl p-4">
            <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0 mt-0.5">
              <i class="pi pi-calendar text-lg" />
            </div>
            <div>
              <p class="font-semibold mb-0.5">Reserveer een rit</p>
              <p class="text-sm text-white/65">Plan jouw ritjes en beheer alles op één plek</p>
            </div>
          </div>
          <div class="flex items-start gap-4 bg-white/10 backdrop-blur-sm rounded-2xl p-4">
            <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0 mt-0.5">
              <i class="pi pi-map text-lg" />
            </div>
            <div>
              <p class="font-semibold mb-0.5">Routes & stops</p>
              <p class="text-sm text-white/65">Plan stops, bekijk routes en deel details</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right form panel -->
    <div class="flex-1 flex flex-col items-center justify-center px-6 py-10 bg-surface-50 dark:bg-zinc-950">
      <!-- Mobile logo -->
      <div class="lg:hidden flex items-center gap-2 mb-10">
        <Logo class="h-10 w-auto text-primary" />
        <span class="font-bold text-xl tracking-tight">CarShare</span>
      </div>

      <div class="w-full max-w-sm">
        <div class="mb-8">
          <h2 class="text-2xl font-bold tracking-tight mb-1">{{ $t('login_title') }}</h2>
          <p class="text-sm text-surface-500">
            {{ $t('login_no_account') }}
            <RouterLink :to="{ name: 'register' }" class="text-primary hover:underline font-medium">
              {{ $t('login_create_account') }}
            </RouterLink>
          </p>
        </div>

        <div class="bg-white dark:bg-zinc-900 rounded-2xl shadow-sm border border-surface-200 dark:border-zinc-700 p-6">
          <Form :resolver="resolver" @submit="onFormSubmit" v-slot="$form">
            <div class="flex flex-col gap-4">
              <!-- Email -->
              <div class="flex flex-col gap-1.5">
                <label class="text-sm font-medium">{{ $t('login_email_placeholder') }}</label>
                <InputText name="email" v-model="form.email" :placeholder="$t('login_email_placeholder')"
                  :invalid="$form.email?.invalid" class="w-full" />
                <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.email.error?.message }}
                </Message>
              </div>

              <!-- Password -->
              <div class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                  <label class="text-sm font-medium">{{ $t('login_password_placeholder') }}</label>
                  <RouterLink :to="{ name: 'forgot-password' }" class="text-xs text-primary hover:underline">
                    {{ $t('login_forgot_password') }}
                  </RouterLink>
                </div>
                <Password name="password" v-model="form.password" :feedback="false" toggleMask class="w-full"
                  inputClass="w-full" :inputProps="{ placeholder: $t('login_password_placeholder') }"
                  :invalid="$form.password?.invalid" />
                <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
                  {{ $form.password.error?.message }}
                </Message>
              </div>

              <!-- Remember me -->
              <div class="flex items-center gap-2">
                <Checkbox v-model="rememberMe" :binary="true" inputId="rememberMe" />
                <label for="rememberMe" class="text-sm text-surface-600 dark:text-surface-400">
                  {{ $t('login_remember_me') }}
                </label>
              </div>

              <!-- Backend auth error -->
              <p v-if="auth.error" class="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 rounded-xl px-3 py-2">
                {{ auth.error }}
              </p>

              <Button type="submit" :label="$t('login_button')" icon="pi pi-sign-in" iconPos="right"
                :loading="auth.loading" class="w-full" />
            </div>
          </Form>
        </div>
      </div>
    </div>
  </div>
</template>
