import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  BatchStatusUpdateItem,
  Issue,
  IssueCreate,
  IssueDetail,
  IssueUpdate,
} from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/issues`;
}

function queryKey(orgId: string, productionId: string) {
  return ["issues", orgId, productionId] as const;
}

export function useIssues(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<Issue[]>(`${basePath(orgId, productionId)}/`),
  });
}

export function useIssueDetail(
  orgId: string,
  productionId: string,
  issueId: string | null,
) {
  return useQuery({
    queryKey: ["issue-detail", orgId, productionId, issueId],
    queryFn: () =>
      api.get<IssueDetail>(
        `${basePath(orgId, productionId)}/${issueId}`,
      ),
    enabled: !!issueId,
  });
}

export function useCreateIssue(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IssueCreate) =>
      api.post<IssueDetail>(`${basePath(orgId, productionId)}/`, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useUpdateIssue(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      issueId,
      body,
    }: {
      issueId: string;
      body: IssueUpdate;
    }) =>
      api.patch<IssueDetail>(
        `${basePath(orgId, productionId)}/${issueId}`,
        body,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) });
      qc.invalidateQueries({ queryKey: ["issue-detail"] });
    },
  });
}

export function useDeleteIssue(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (issueId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${issueId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useUpdateIssueStatus(orgId: string, productionId: string) {
  const qc = useQueryClient();
  const key = queryKey(orgId, productionId);

  return useMutation({
    mutationFn: ({
      issueId,
      statusId,
    }: {
      issueId: string;
      statusId: string | null;
    }) =>
      api.patch<IssueDetail>(
        `${basePath(orgId, productionId)}/${issueId}`,
        { status_id: statusId },
      ),
    onMutate: async ({ issueId, statusId }) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<Issue[]>(key);
      qc.setQueryData<Issue[]>(key, (old) =>
        old?.map((issue) =>
          issue.id === issueId ? { ...issue, status_id: statusId } : issue,
        ),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(key, context.previous);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: key });
    },
  });
}

export function useBatchUpdateStatus(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: BatchStatusUpdateItem[]) =>
      api.patch<void>(
        `${basePath(orgId, productionId)}/batch-update-status`,
        { items },
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}
