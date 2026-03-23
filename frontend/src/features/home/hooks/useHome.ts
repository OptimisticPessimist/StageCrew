import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { HomeResponse } from "@/types";

export function useHome() {
  return useQuery({
    queryKey: ["home"],
    queryFn: () => api.get<HomeResponse>("/home"),
  });
}
