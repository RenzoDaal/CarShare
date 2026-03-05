import { defineStore } from "pinia";
import http from "@/api/http";

export type Car = {
  id: number;
  owner_id: number;
  name: string;
  description?: string | null;
  price_per_km: number;
  is_active: boolean;
  image_url?: string | null;
};

export type NewCarPayload = {
  name: string;
  description?: string | null;
  price_per_km: number;
};

export type UpdateCarPayload = {
  name?: string;
  description?: string | null;
  price_per_km?: number;
  is_active?: boolean;
};

export const useCarStore = defineStore("cars", {
  state: () => ({
    cars: [] as Car[],
    loading: false,
    error: null as string | null,
  }),

  actions: {
    async fetchCars() {
      this.loading = true;
      this.error = null;
      try {
        const res = await http.get<Car[]>("/cars");
        this.cars = res.data;
      } catch (err: any) {
        this.error = err.response?.data?.detail ?? "Failed to load cars";
      } finally {
        this.loading = false;
      }
    },

    async createCar(payload: NewCarPayload) {
      this.loading = true;
      this.error = null;
      try {
        const res = await http.post<Car>("/cars", payload);
        const created = res.data;

        this.cars.push(created);

        return created;
      } catch (err: any) {
        this.error = err.response?.data?.detail ?? "Failed to create car";
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async updateCar(id: number, payload: UpdateCarPayload) {
      this.loading = true;
      this.error = null;
      try {
        const res = await http.patch<Car>(`/cars/${id}`, payload);
        const updated = res.data;

        const index = this.cars.findIndex((c) => c.id === id);
        if (index !== -1) {
          this.cars[index] = updated;
        }

        return updated;
      } catch (err: any) {
        this.error = err.response?.data?.detail ?? "Failed to update car";
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async uploadCarImage(id: number, file: File) {
      this.loading = true;
      this.error = null;
      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await http.post<Car>(`/cars/${id}/image`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        const updated = res.data;
        const index = this.cars.findIndex((c) => c.id === id);
        if (index !== -1) {
          this.cars[index] = updated;
        }

        return updated;
      } catch (err: any) {
        this.error = err.response?.data?.detail ?? "Failed to upload image";
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async deleteCar(id: number) {
      this.loading = true;
      this.error = null;
      try {
        await http.delete(`/cars/${id}`);
        this.cars = this.cars.filter((car) => car.id !== id);
      } catch (err: any) {
        this.error = err.response?.data?.detail ?? "Failed to delete car";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async fetchMyCars() {
      const res = await http.get<Car[]>("/cars/mine");
      this.cars = res.data;
    },
  },
});
