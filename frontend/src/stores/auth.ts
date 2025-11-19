import { defineStore } from "pinia";
import http from "../api/http";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role_owner: boolean;
  role_borrower: boolean;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

type LoginPayload = {
  email: string;
  password: string;
};

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as User | null,
    token: null as string | null,
    loading: false,
    error: null as string | null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    loadFromStorage() {
      const token = localStorage.getItem("auth_token");
      const userJson = localStorage.getItem("auth_user");
      if (token && userJson) {
        this.token = token;
        this.user = JSON.parse(userJson) as User;
      }
    },

    saveToStorage() {
      if (this.token && this.user) {
        localStorage.setItem("auth_token", this.token);
        localStorage.setItem("auth_user", JSON.stringify(this.user));
      } else {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
      }
    },

    async login(payload: LoginPayload) {
      this.loading = true;
      this.error = null;
      try {
        const res = await http.post<TokenResponse>("/auth/login", payload);
        this.token = res.data.access_token;
        this.user = res.data.user;
        this.saveToStorage();
      } catch (err: any) {
        this.error =
          err?.response?.data?.detail ??
          "Login failed. Please check you details.";
        throw err;
      } finally {
        this.loading = false;
      }
    },

    logout() {
      this.token = null;
      this.user = null;
      this.saveToStorage();
    },
  },
});
