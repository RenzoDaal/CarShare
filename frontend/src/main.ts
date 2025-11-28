import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "@/App.vue";
import router from "./router";
import "@/assets/main.css";
import "@/assets/tailwind.css";
import ConfirmationService from "primevue/confirmationservice";

import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";
import "primeicons/primeicons.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(ConfirmationService);

const MyTheme = definePreset(Aura, {
  semantic: {
    primary: {
      //500: "#ff7f00", // Only override “primary-500”
    },
  },
});

app.use(PrimeVue, {
  theme: {
    preset: MyTheme,
  },
});

app.use(router);
app.mount("#app");
