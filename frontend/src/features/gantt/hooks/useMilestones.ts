import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Milestone } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/milestones`;
}

function queryKey(orgId: string, productionId: string) {
  return ["milestones", orgId, productionId] as const;
}

export function useMilestones(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<Milestone[]>(`${basePath(orgId, productionId)}/`),
  });
}
