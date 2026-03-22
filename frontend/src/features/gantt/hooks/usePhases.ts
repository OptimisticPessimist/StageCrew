import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ProductionPhase } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/phases`;
}

function queryKey(orgId: string, productionId: string) {
  return ["phases", orgId, productionId] as const;
}

export function usePhases(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<ProductionPhase[]>(`${basePath(orgId, productionId)}/`),
  });
}
