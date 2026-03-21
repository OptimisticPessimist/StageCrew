import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { StatusCreate, StatusDefinition, StatusUpdate } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/statuses`;
}

function queryKey(orgId: string, productionId: string) {
  return ["statuses", orgId, productionId] as const;
}

export function useStatuses(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () =>
      api.get<StatusDefinition[]>(`${basePath(orgId, productionId)}/`),
  });
}

export function useCreateStatus(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StatusCreate) =>
      api.post<StatusDefinition>(`${basePath(orgId, productionId)}/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useUpdateStatus(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ statusId, body }: { statusId: string; body: StatusUpdate }) =>
      api.patch<StatusDefinition>(`${basePath(orgId, productionId)}/${statusId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useDeleteStatus(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (statusId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${statusId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}
