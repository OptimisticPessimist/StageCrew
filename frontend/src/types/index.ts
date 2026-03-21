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
