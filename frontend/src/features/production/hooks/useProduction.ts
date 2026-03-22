import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ProductionSummary } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/summary`;
}

function queryKey(orgId: string, productionId: string) {
  return ["production-summary", orgId, productionId] as const;
}

export function useProduction(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<ProductionSummary>(basePath(orgId, productionId)),
  });
}
