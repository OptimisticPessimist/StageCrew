import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { SceneChart } from "@/types";

function basePath(orgId: string, productionId: string, scriptId: string) {
  return `/organizations/${orgId}/productions/${productionId}/scripts/${scriptId}/scene-chart`;
}

function chartKey(orgId: string, productionId: string, scriptId: string) {
  return ["scene-chart", orgId, productionId, scriptId] as const;
}

export function useSceneChart(orgId: string, productionId: string, scriptId: string) {
  return useQuery({
    queryKey: chartKey(orgId, productionId, scriptId),
    queryFn: () => api.get<SceneChart>(`${basePath(orgId, productionId, scriptId)}/`),
    enabled: !!scriptId,
  });
}

export function useGenerateSceneChart(orgId: string, productionId: string, scriptId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (preserveManual = true) =>
      api.post<SceneChart>(
        `${basePath(orgId, productionId, scriptId)}/generate`,
        { preserve_manual: preserveManual },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: chartKey(orgId, productionId, scriptId) });
    },
  });
}
