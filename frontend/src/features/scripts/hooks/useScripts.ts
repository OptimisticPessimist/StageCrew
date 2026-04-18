import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ScriptDetail, ScriptListItem } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/scripts`;
}

function queryKey(orgId: string, productionId: string) {
  return ["scripts", orgId, productionId] as const;
}

export function useScripts(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () =>
      api.get<ScriptListItem[]>(`${basePath(orgId, productionId)}/`),
  });
}

export function useScript(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  return useQuery({
    queryKey: ["scripts", orgId, productionId, scriptId] as const,
    queryFn: () =>
      api.get<ScriptDetail>(`${basePath(orgId, productionId)}/${scriptId}`),
  });
}

export function useDeleteScript(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scriptId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${scriptId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}
