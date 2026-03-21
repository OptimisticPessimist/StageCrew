import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ProductionMember } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/members`;
}

function queryKey(orgId: string, productionId: string) {
  return ["productionMembers", orgId, productionId] as const;
}

export function useProductionMembers(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () =>
      api.get<ProductionMember[]>(`${basePath(orgId, productionId)}/`),
  });
}

export function useAddProductionMember(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      user_id: string;
      production_role?: string;
      is_cast?: boolean;
    }) =>
      api.post<ProductionMember>(
        `${basePath(orgId, productionId)}/`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useUpdateProductionMember(
  orgId: string,
  productionId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      membershipId,
      body,
    }: {
      membershipId: string;
      body: {
        production_role?: string;
        is_cast?: boolean;
        cast_capabilities?: string[] | null;
      };
    }) =>
      api.patch<ProductionMember>(
        `${basePath(orgId, productionId)}/${membershipId}`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useRemoveProductionMember(
  orgId: string,
  productionId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${membershipId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}
