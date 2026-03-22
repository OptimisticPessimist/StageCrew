import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ProductionListItem } from "@/types";

export function useProductions(orgId: string) {
  return useQuery({
    queryKey: ["productions", orgId],
    queryFn: () =>
      api.get<ProductionListItem[]>(`/organizations/${orgId}/productions`),
  });
}
