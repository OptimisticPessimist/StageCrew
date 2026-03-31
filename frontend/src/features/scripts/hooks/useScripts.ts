import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ScriptDetail, ScriptListItem, ScriptCreate, ScriptUpdate } from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/scripts`;
}

function listKey(orgId: string, productionId: string) {
  return ["scripts", orgId, productionId] as const;
}

function detailKey(orgId: string, productionId: string, scriptId: string) {
  return ["script-detail", orgId, productionId, scriptId] as const;
}

export function useScripts(orgId: string, productionId: string) {
  return useQuery({
    queryKey: listKey(orgId, productionId),
    queryFn: () => api.get<ScriptListItem[]>(`${basePath(orgId, productionId)}/`),
  });
}

export function useScriptDetail(orgId: string, productionId: string, scriptId: string) {
  return useQuery({
    queryKey: detailKey(orgId, productionId, scriptId),
    queryFn: () =>
      api.get<ScriptDetail>(`${basePath(orgId, productionId)}/${scriptId}`),
    enabled: !!scriptId,
  });
}

export function useCreateScript(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ScriptCreate) =>
      api.post<ScriptDetail>(`${basePath(orgId, productionId)}/`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId) });
    },
  });
}

export function useUploadScript(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload<ScriptDetail>(
        `${basePath(orgId, productionId)}/upload`,
        formData,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId) });
    },
  });
}

export function useUpdateScript(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ scriptId, body }: { scriptId: string; body: ScriptUpdate }) =>
      api.patch<ScriptDetail>(`${basePath(orgId, productionId)}/${scriptId}`, body),
    onSuccess: (_data, { scriptId }) => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId) });
      qc.invalidateQueries({ queryKey: detailKey(orgId, productionId, scriptId) });
    },
  });
}

export function useDeleteScript(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scriptId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${scriptId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId) });
    },
  });
}

export function useReuploadScript(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ scriptId, file }: { scriptId: string; file: File }) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload<ScriptDetail>(
        `${basePath(orgId, productionId)}/${scriptId}/reupload`,
        formData,
      );
    },
    onSuccess: (_data, { scriptId }) => {
      qc.invalidateQueries({ queryKey: listKey(orgId, productionId) });
      qc.invalidateQueries({ queryKey: detailKey(orgId, productionId, scriptId) });
    },
  });
}

export function useScriptPdfUrl(orgId: string, productionId: string, scriptId: string) {
  return `/api/organizations/${orgId}/productions/${productionId}/scripts/${scriptId}/pdf`;
}
