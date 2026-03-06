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
import AdminPage from "@/pages/AdminPage.vue";
import ProfilePage from "@/pages/ProfilePage.vue";
import { useAuthStore } from "@/stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
    meta: { hideLayout: true },
  },
  {
    path: "/register",
    name: "register",
    component: RegisterPage,
    meta: { hideLayout: true },
  },
  { path: "/", name: "home", component: HomePage },
  {
    path: "/managecars",
    name: "manage cars",
    component: CarManagerPage,
    meta: { requiresOwner: true },
  },
  {
    path: "/reservecar",
    name: "reserve car",
    component: ReserveCarPage,
    meta: { requiresBorrower: true },
  },
  {
    path: "/ownerappointments",
    name: "ownerappointments",
    component: OwnerAppointmentsPage,
    meta: { requiresOwner: true },
  },
  {
    path: "/borrowerappointments",
    name: "borrowerappointments",
    component: BorrowersAppointmentsPage,
    meta: { requiresBorrower: true },
  },
  {
    path: "/availability",
    name: "availability",
    component: CarAvailabilityPage,
    meta: { requiresBorrower: true },
  },
  {
    path: "/admin",
    name: "admin",
    component: AdminPage,
    meta: { requiresAdmin: true },
  },
  {
    path: "/profile",
    name: "profile",
    component: ProfilePage,
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

  if (auth.isAuthenticated && (to.name === "login" || to.name === "register")) {
    return { name: "home" };
  }

  if (to.meta.requiresOwner && !auth.user?.role_owner) {
    return { name: "home" };
  }

  if (to.meta.requiresBorrower && !auth.user?.role_borrower) {
    return { name: "home" };
  }

  if (to.meta.requiresAdmin && !auth.user?.is_admin) {
    return { name: "home" };
  }

  return true;
});

export default router;
