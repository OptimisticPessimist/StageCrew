import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Invitation, InvitationCreate } from "@/types";

function basePath(orgId: string) {
  return `/organizations/${orgId}/invitations`;
}

function queryKey(orgId: string) {
  return ["invitations", orgId] as const;
}

export function useInvitations(orgId: string) {
  return useQuery({
    queryKey: queryKey(orgId),
    queryFn: () => api.get<Invitation[]>(`${basePath(orgId)}/`),
  });
}

export function useCreateInvitation(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InvitationCreate) =>
      api.post<Invitation>(`${basePath(orgId)}/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId) }),
  });
}

export function useCancelInvitation(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) =>
      api.delete(`${basePath(orgId)}/${invitationId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey(orgId) }),
  });
}

export function useAcceptInvitation() {
  return useMutation({
    mutationFn: (token: string) =>
      api.post<{ message: string; organization_id: string; membership_id: string }>(
        `/invitations/${token}/accept`,
        {},
      ),
  });
}
