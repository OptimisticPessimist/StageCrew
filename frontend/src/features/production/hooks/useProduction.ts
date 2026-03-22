import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Production } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}`;
}

function queryKey(orgId: string, productionId: string) {
  return ["production", orgId, productionId] as const;
}

export function useProduction(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<Production>(basePath(orgId, productionId)),
  });
}
