import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { OrgMember } from "@/types";

function basePath(orgId: string) {
  return `/organizations/${orgId}/members`;
}

function queryKey(orgId: string) {
  return ["orgMembers", orgId] as const;
}

export function useOrgMembers(orgId: string) {
  return useQuery({
    queryKey: queryKey(orgId),
    queryFn: () => api.get<OrgMember[]>(`${basePath(orgId)}/`),
  });
}

export function useAddOrgMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { user_id: string; org_role?: string }) =>
      api.post<OrgMember>(`${basePath(orgId)}/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId) }),
  });
}

export function useUpdateOrgMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      membershipId,
      org_role,
    }: {
      membershipId: string;
      org_role: string;
    }) =>
      api.patch<OrgMember>(`${basePath(orgId)}/${membershipId}`, { org_role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId) }),
  });
}

export function useRemoveOrgMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) =>
      api.delete(`${basePath(orgId)}/${membershipId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId) }),
  });
}
