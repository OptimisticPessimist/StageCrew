// ---- Production ----
export interface ProductionSummary {
  id: string;
  name: string;
  opening_date: string | null;
  closing_date: string | null;
  current_phase: string | null;
}

// ---- Status ----
export interface StatusDefinition {
  id: string;
  production_id: string;
  department_id: string | null;
  name: string;
  color: string | null;
  sort_order: number;
  is_closed: boolean;
}

export interface StatusCreate {
  name: string;
  color?: string | null;
  sort_order?: number;
  is_closed?: boolean;
  department_id?: string | null;
}

export interface StatusUpdate {
  name?: string;
  color?: string | null;
  sort_order?: number;
  is_closed?: boolean;
}

// ---- Issue ----
export interface IssueAssignee {
  user_id: string;
  display_name: string;
}

export interface IssueLabel {
  label_id: string;
  name: string;
  color: string | null;
}

export interface Issue {
  id: string;
  title: string;
  issue_type: string;
  priority: string;
  status_id: string | null;
  department_id: string | null;
  due_date: string | null;
  start_date: string | null;
  assignees: IssueAssignee[];
  labels: IssueLabel[];
  created_at: string;
  updated_at: string;
}

export interface IssueDetail extends Issue {
  description: string | null;
  start_date: string | null;
  parent_issue_id: string | null;
  phase_id: string | null;
  milestone_id: string | null;
  created_by: string;
}

export interface IssueCreate {
  title: string;
  description?: string | null;
  issue_type?: string;
  priority?: string;
  status_id?: string | null;
  department_id?: string | null;
  due_date?: string | null;
  start_date?: string | null;
  assignee_ids?: string[];
  label_ids?: string[];
}

export interface IssueUpdate {
  title?: string;
  description?: string | null;
  issue_type?: string;
  priority?: string;
  status_id?: string | null;
  department_id?: string | null;
  due_date?: string | null;
  start_date?: string | null;
  assignee_ids?: string[];
  label_ids?: string[];
}

export interface BatchStatusUpdateItem {
  issue_id: string;
  status_id: string | null;
}

// ---- Department ----
export interface StaffRole {
  id: string;
  department_id: string;
  name: string;
  sort_order: number;
}

export interface Department {
  id: string;
  production_id: string;
  name: string;
  color: string | null;
  sort_order: number;
  created_at: string;
  staff_roles: StaffRole[];
}

export interface DepartmentCreate {
  name: string;
  color?: string | null;
  sort_order?: number;
  staff_roles?: { name: string; sort_order?: number }[];
}

export interface DepartmentUpdate {
  name?: string;
  color?: string | null;
  sort_order?: number;
}

export interface StaffRoleCreate {
  name: string;
  sort_order?: number;
}

export interface StaffRoleUpdate {
  name?: string;
  sort_order?: number;
}

// ---- Organization Member ----
export interface OrgMember {
  id: string;
  user_id: string;
  display_name: string;
  org_role: string;
  created_at: string;
}

// ---- Production Member ----
export interface DeptMembershipBrief {
  id: string;
  department_id: string;
  department_name: string;
  staff_role_id: string | null;
  staff_role_name: string | null;
  capabilities: string[];
}

export interface ProductionMember {
  id: string;
  user_id: string;
  display_name: string;
  production_role: string;
  is_cast: boolean;
  cast_capabilities: string[] | null;
  created_at: string;
  department_memberships: DeptMembershipBrief[];
}

// ---- Invitation ----
export interface Invitation {
  id: string;
  organization_id: string;
  email: string | null;
  token: string;
  org_role: string;
  status: string;
  expires_at: string;
  created_at: string;
  invited_by_name: string;
}

export interface InvitationCreate {
  email?: string | null;
  org_role?: string;
}

// ---- Production Phase ----
export interface ProductionPhase {
  id: string;
  production_id: string;
  name: string;
  sort_order: number;
  start_date: string | null;
  end_date: string | null;
}

export interface PhaseCreate {
  name: string;
  sort_order?: number;
  start_date?: string | null;
  end_date?: string | null;
}

export interface PhaseUpdate {
  name?: string;
  sort_order?: number;
  start_date?: string | null;
  end_date?: string | null;
}

// ---- Milestone ----
export interface Milestone {
  id: string;
  production_id: string;
  name: string;
  date: string | null;
  color: string | null;
}

export interface MilestoneCreate {
  name: string;
  date?: string | null;
  color?: string | null;
}

export interface MilestoneUpdate {
  name?: string;
  date?: string | null;
  color?: string | null;
}
