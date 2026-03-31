import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Casting, CastingCreate, CastingUpdate } from "@/types";

function basePath(orgId: string, productionId: string, scriptId: string) {
  return `/organizations/${orgId}/productions/${productionId}/scripts/${scriptId}/castings`;
}

function listKey(orgId: string, productionId: string, scriptId: string) {
  return ["castings", orgId, productionId, scriptId] as const;
}

export function useCastings(orgId: string, productionId: string, scriptId: string) {
  return useQuery({
    queryKey: listKey(orgId, productionId, scriptId),
    queryFn: () => api.get<Casting[]>(`${basePath(orgId, productionId, scriptId)}/`),
    enabled: !!scriptId,
  });
}

export function useCreateCasting(orgId: string, productionId: string, scriptId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CastingCreate) =>
      api.post<Casting>(`${basePath(orgId, productionId, scriptId)}/`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId, scriptId) });
      qc.invalidateQueries({ queryKey: ["script-detail", orgId, productionId, scriptId] });
    },
  });
}

export function useUpdateCasting(orgId: string, productionId: string, scriptId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ castingId, body }: { castingId: string; body: CastingUpdate }) =>
      api.patch<Casting>(
        `${basePath(orgId, productionId, scriptId)}/${castingId}`,
        body,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId, scriptId) });
      qc.invalidateQueries({ queryKey: ["script-detail", orgId, productionId, scriptId] });
    },
  });
}

export function useDeleteCasting(orgId: string, productionId: string, scriptId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (castingId: string) =>
      api.delete(`${basePath(orgId, productionId, scriptId)}/${castingId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId, scriptId) });
      qc.invalidateQueries({ queryKey: ["script-detail", orgId, productionId, scriptId] });
    },
  });
}
