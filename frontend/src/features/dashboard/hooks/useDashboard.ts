import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { DashboardResponse } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/dashboard`;
}

function queryKey(orgId: string, productionId: string) {
  return ["dashboard", orgId, productionId] as const;
}

export function useDashboard(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<DashboardResponse>(basePath(orgId, productionId)),
  });
}
