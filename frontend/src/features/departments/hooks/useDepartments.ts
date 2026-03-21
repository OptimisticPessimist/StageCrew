import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  Department,
  DepartmentCreate,
  DepartmentUpdate,
  StaffRole,
  StaffRoleCreate,
  StaffRoleUpdate,
} from "@/types";

function basePath(orgId: string, productionId: string) {
  return `/organizations/${orgId}/productions/${productionId}/departments`;
}

function queryKey(orgId: string, productionId: string) {
  return ["departments", orgId, productionId] as const;
}

export function useDepartments(orgId: string, productionId: string) {
  return useQuery({
    queryKey: queryKey(orgId, productionId),
    queryFn: () => api.get<Department[]>(`${basePath(orgId, productionId)}/`),
  });
}

export function useCreateDepartment(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DepartmentCreate) =>
      api.post<Department>(`${basePath(orgId, productionId)}/`, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useUpdateDepartment(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      deptId,
      body,
    }: {
      deptId: string;
      body: DepartmentUpdate;
    }) =>
      api.patch<Department>(
        `${basePath(orgId, productionId)}/${deptId}`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useDeleteDepartment(orgId: string, productionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (deptId: string) =>
      api.delete(`${basePath(orgId, productionId)}/${deptId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

// ---- Staff Roles ----

export function useCreateStaffRole(
  orgId: string,
  productionId: string,
  deptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StaffRoleCreate) =>
      api.post<StaffRole>(
        `${basePath(orgId, productionId)}/${deptId}/staff-roles`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useUpdateStaffRole(
  orgId: string,
  productionId: string,
  deptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      roleId,
      body,
    }: {
      roleId: string;
      body: StaffRoleUpdate;
    }) =>
      api.patch<StaffRole>(
        `${basePath(orgId, productionId)}/${deptId}/staff-roles/${roleId}`,
        body,
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}

export function useDeleteStaffRole(
  orgId: string,
  productionId: string,
  deptId: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (roleId: string) =>
      api.delete(
        `${basePath(orgId, productionId)}/${deptId}/staff-roles/${roleId}`,
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKey(orgId, productionId) }),
  });
}
