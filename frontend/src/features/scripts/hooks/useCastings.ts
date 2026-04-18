import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Casting, CastingCreate, CastingUpdate } from "@/types";

function basePath(orgId: string, productionId: string, scriptId: string) {
  return `/organizations/${orgId}/productions/${productionId}/scripts/${scriptId}/castings`;
}

function queryKey(orgId: string, productionId: string, scriptId: string) {
  return ["castings", orgId, productionId, scriptId] as const;
}

function scriptDetailKey(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  return ["scripts", orgId, productionId, scriptId] as const;
}

export function useCastings(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  return useQuery({
    queryKey: queryKey(orgId, productionId, scriptId),
    queryFn: () =>
      api.get<Casting[]>(`${basePath(orgId, productionId, scriptId)}/`),
  });
}

function invalidate(
  qc: ReturnType<typeof useQueryClient>,
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  qc.invalidateQueries({ queryKey: queryKey(orgId, productionId, scriptId) });
  qc.invalidateQueries({
    queryKey: scriptDetailKey(orgId, productionId, scriptId),
  });
}

export function useCreateCasting(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CastingCreate) =>
      api.post<Casting>(`${basePath(orgId, productionId, scriptId)}/`, body),
    onSuccess: () => invalidate(qc, orgId, productionId, scriptId),
  });
}

export function useUpdateCasting(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      castingId,
      body,
    }: {
      castingId: string;
      body: CastingUpdate;
    }) =>
      api.patch<Casting>(
        `${basePath(orgId, productionId, scriptId)}/${castingId}`,
        body,
      ),
    onSuccess: () => invalidate(qc, orgId, productionId, scriptId),
  });
}

export function useDeleteCasting(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (castingId: string) =>
      api.delete(
        `${basePath(orgId, productionId, scriptId)}/${castingId}`,
      ),
    onSuccess: () => invalidate(qc, orgId, productionId, scriptId),
  });
}
