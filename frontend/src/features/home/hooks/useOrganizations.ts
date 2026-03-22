import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { OrganizationSummary } from "@/types";

export function useOrganizations() {
  return useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<OrganizationSummary[]>("/organizations"),
  });
}
