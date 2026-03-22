import { useState, useEffect } from "react";
import type { OrganizationSummary } from "@/types";

const STORAGE_KEY = "stagecrew_selected_org";

export function useSelectedOrg(organizations: OrganizationSummary[] | undefined) {
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  );

  // org一覧が読み込まれたら、無効なIDをフォールバック
  useEffect(() => {
    if (!organizations || organizations.length === 0) return;
    const valid = organizations.some((o) => o.id === selectedOrgId);
    if (!valid) {
      setSelectedOrgId(organizations[0].id);
    }
  }, [organizations, selectedOrgId]);

  // localStorageに永続化
  useEffect(() => {
    if (selectedOrgId) {
      localStorage.setItem(STORAGE_KEY, selectedOrgId);
    }
  }, [selectedOrgId]);

  return [selectedOrgId, setSelectedOrgId] as const;
}
