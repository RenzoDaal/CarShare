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
        z.string().min(1, { message: 'Email is required' })
      ),
      password: stringFromNullish(
        z.string().min(1, { message: 'Password is required' })
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
  <div class="flex-1 flex justify-center items-center h-screen">
    <Card>
      <template #title>Login</template>
      <template #content>
        <Form :resolver="resolver" @submit="onFormSubmit" v-slot="$form">
          <div class="flex flex-col mt-4 w-96">
            <!-- Email -->
            <div class="flex flex-col gap-1 mb-4">
              <InputText name="email" v-model="form.email" placeholder="Email" />
              <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
                {{ $form.email.error?.message }}
              </Message>
            </div>

            <!-- Password -->
            <div class="flex flex-col gap-1 mb-4">
              <Password name="password" v-model="form.password" :feedback="false" toggleMask class="w-full"
                inputClass="w-full" :inputProps="{ placeholder: 'Password' }" />
              <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
                {{ $form.password.error?.message }}
              </Message>
            </div>

            <!-- Remember me -->
            <div class="flex items-center gap-2 mb-4">
              <Checkbox v-model="rememberMe" :binary="true" inputId="rememberMe" />
              <label for="rememberMe" class="text-sm">Remember me</label>
            </div>

            <!-- Backend auth error -->
            <p v-if="auth.error" class="text-red-500 text-sm mb-2">
              {{ auth.error }}
            </p>

            <Button type="submit" label="Login" icon="pi pi-sign-in" iconPos="right" :loading="auth.loading" />

            <p class="mt-3 text-sm text-center">
              <RouterLink :to="{ name: 'forgot-password' }" class="text-blue-500 hover:underline">
                Forgot your password?
              </RouterLink>
            </p>

            <p class="mt-2 text-sm text-center">
              Don't have an account yet?
              <RouterLink :to="{ name: 'register' }" class="text-blue-500 hover:underline">
                Create one
              </RouterLink>
            </p>
          </div>
        </Form>
      </template>
    </Card>
  </div>
</template>
