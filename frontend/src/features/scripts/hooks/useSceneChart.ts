import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  SceneCharacterMapping,
  SceneCharacterMappingCreate,
  SceneCharacterMappingUpdate,
  SceneChartResponse,
} from "@/types";

function basePath(orgId: string, productionId: string, scriptId: string) {
  return `/organizations/${orgId}/productions/${productionId}/scripts/${scriptId}/scene-chart`;
}

function queryKey(orgId: string, productionId: string, scriptId: string) {
  return ["scene-chart", orgId, productionId, scriptId] as const;
}

export function useSceneChart(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  return useQuery({
    queryKey: queryKey(orgId, productionId, scriptId),
    queryFn: () =>
      api.get<SceneChartResponse>(
        `${basePath(orgId, productionId, scriptId)}/`,
      ),
  });
}

export function useGenerateSceneChart(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (preserveManual: boolean) =>
      api.post<SceneChartResponse>(
        `${basePath(orgId, productionId, scriptId)}/generate`,
        { preserve_manual: preserveManual },
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKey(orgId, productionId, scriptId),
      }),
  });
}

export function useCreateMapping(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SceneCharacterMappingCreate) =>
      api.post<SceneCharacterMapping>(
        `${basePath(orgId, productionId, scriptId)}/mappings`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKey(orgId, productionId, scriptId),
      }),
  });
}

export function useUpdateMapping(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      mappingId,
      body,
    }: {
      mappingId: string;
      body: SceneCharacterMappingUpdate;
    }) =>
      api.patch<SceneCharacterMapping>(
        `${basePath(orgId, productionId, scriptId)}/mappings/${mappingId}`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKey(orgId, productionId, scriptId),
      }),
  });
}

export function useDeleteMapping(
  orgId: string,
  productionId: string,
  scriptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mappingId: string) =>
      api.delete(
        `${basePath(orgId, productionId, scriptId)}/mappings/${mappingId}`,
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKey(orgId, productionId, scriptId),
      }),
  });
}
