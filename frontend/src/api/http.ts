import axios from "axios";
import { useAuthStore } from "../stores/auth";

const API_BASE = "http://10.142.1.159:8000";

const http = axios.create({
  baseURL: API_BASE,
});

http.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

export default http;
