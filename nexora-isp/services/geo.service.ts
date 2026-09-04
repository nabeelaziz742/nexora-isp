import { apiRequest } from "@/services/api-client";

export interface Country {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
  cities_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CountryPayload {
  name: string;
  code: string;
  is_active?: boolean;
}

export interface City {
  id: string;
  country?: string | null;
  country_name?: string | null;
  name: string;
  code?: string;
  is_active: boolean;
  areas_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CityPayload {
  name: string;
  code?: string;
  country?: string | null;
  is_active?: boolean;
}

export interface Area {
  id: string;
  city?: string | null;
  city_name?: string | null;
  country_name?: string | null;
  name: string;
  code?: string;
  postal_code?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AreaPayload {
  name: string;
  code?: string;
  postal_code?: string;
  city?: string | null;
  is_active?: boolean;
}

function buildQueryString(params?: Record<string, string | undefined>) {
  if (!params) return "";
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim()) {
      searchParams.set(key, value.trim());
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export const geoService = {
  // ==================== COUNTRIES ====================
  getCountries(params?: { search?: string; status?: "active" | "inactive" | "" }): Promise<Country[]> {
    return apiRequest<Country[]>(`/customers/countries/${buildQueryString(params)}`);
  },

  getCountry(countryId: string): Promise<Country> {
    return apiRequest<Country>(`/customers/countries/${countryId}/`);
  },

  createCountry(payload: CountryPayload): Promise<Country> {
    return apiRequest<Country>("/customers/countries/", {
      method: "POST",
      body: payload,
    });
  },

  updateCountry(countryId: string, payload: Partial<CountryPayload>): Promise<Country> {
    return apiRequest<Country>(`/customers/countries/${countryId}/`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteCountry(countryId: string): Promise<void> {
    return apiRequest<void>(`/customers/countries/${countryId}/`, {
      method: "DELETE",
    });
  },

  toggleCountryStatus(countryId: string): Promise<Country> {
    return apiRequest<Country>(`/customers/countries/${countryId}/status/`, {
      method: "PATCH",
    });
  },

  // ==================== CITIES ====================
  getCities(params?: { search?: string; country?: string; status?: "active" | "inactive" | "" }): Promise<City[]> {
    return apiRequest<City[]>(`/customers/cities/${buildQueryString(params)}`);
  },

  getCity(cityId: string): Promise<City> {
    return apiRequest<City>(`/customers/cities/${cityId}/`);
  },

  createCity(payload: CityPayload): Promise<City> {
    return apiRequest<City>("/customers/cities/", {
      method: "POST",
      body: payload,
    });
  },

  updateCity(cityId: string, payload: Partial<CityPayload>): Promise<City> {
    return apiRequest<City>(`/customers/cities/${cityId}/`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteCity(cityId: string): Promise<void> {
    return apiRequest<void>(`/customers/cities/${cityId}/`, {
      method: "DELETE",
    });
  },

  toggleCityStatus(cityId: string): Promise<City> {
    return apiRequest<City>(`/customers/cities/${cityId}/status/`, {
      method: "PATCH",
    });
  },

  // ==================== AREAS ====================
  getAreas(params?: { search?: string; city?: string; status?: "active" | "inactive" | "" }): Promise<Area[]> {
    return apiRequest<Area[]>(`/customers/areas/${buildQueryString(params)}`);
  },

  getArea(areaId: string): Promise<Area> {
    return apiRequest<Area>(`/customers/areas/${areaId}/`);
  },

  createArea(payload: AreaPayload): Promise<Area> {
    return apiRequest<Area>("/customers/areas/", {
      method: "POST",
      body: payload,
    });
  },

  updateArea(areaId: string, payload: Partial<AreaPayload>): Promise<Area> {
    return apiRequest<Area>(`/customers/areas/${areaId}/`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteArea(areaId: string): Promise<void> {
    return apiRequest<void>(`/customers/areas/${areaId}/`, {
      method: "DELETE",
    });
  },

  toggleAreaStatus(areaId: string): Promise<Area> {
    return apiRequest<Area>(`/customers/areas/${areaId}/status/`, {
      method: "PATCH",
    });
  },
};
