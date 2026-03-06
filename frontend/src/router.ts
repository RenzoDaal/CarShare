import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import LoginPage from "@/pages/LoginPage.vue";
import HomePage from "@/pages/HomePage.vue";
import CarManagerPage from "@/pages/CarManagerPage.vue";
import ReserveCarPage from "@/pages/ReserveCarPage.vue";
import OwnerAppointmentsPage from "@/pages/OwnerAppointmentsPage.vue";
import BorrowersAppointmentsPage from "@/pages/BorrowerAppointmentsPage.vue";
import CarAvailabilityPage from "@/pages/CarAvailabilityPage.vue";
import RegisterPage from "@/pages/RegisterPage.vue";
import { useAuthStore } from "@/stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
    meta: { hideLayout: true },
  },
  { path: "/", name: "home", component: HomePage },
  {
    path: "/managecars",
    name: "manage cars",
    component: CarManagerPage,
  },
  {
    path: "/reservecar",
    name: "reserve car",
    component: ReserveCarPage,
  },
  {
    path: "/register",
    name: "register",
    component: RegisterPage,
    meta: { hideLayout: true },
  },
  {
    path: "/ownerappointments",
    name: "ownerappointments",
    component: OwnerAppointmentsPage,
  },
  {
    path: "/borrowerappointments",
    name: "borrowerappointments",
    component: BorrowersAppointmentsPage,
  },
  {
    path: "/availability",
    name: "availability",
    component: CarAvailabilityPage,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { left: 0, top: 0 };
  },
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!auth.isAuthenticated && to.name !== "login" && to.name !== "register") {
    return { name: "login" };
  }

  if (auth.isAuthenticated && to.name === "login") {
    return { name: "home" };
  }

  return true;
});

export default router;
