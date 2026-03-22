import { useMemo } from "react";
import { useIssues } from "@/features/kanban/hooks/useIssues";
import { useDepartments } from "@/features/departments/hooks/useDepartments";
import { usePhases } from "./usePhases";
import { useMilestones } from "./useMilestones";
import type { Issue, Department } from "@/types";

export interface DepartmentGroup {
  department: Department | null;
  issues: Issue[];
}

export function useGanttData(orgId: string, productionId: string) {
  const { data: issues = [], isLoading: loadingIssues } = useIssues(orgId, productionId);
  const { data: departments = [], isLoading: loadingDepartments } = useDepartments(orgId, productionId);
  const { data: phases = [], isLoading: loadingPhases } = usePhases(orgId, productionId);
  const { data: milestones = [], isLoading: loadingMilestones } = useMilestones(orgId, productionId);

  const isLoading = loadingIssues || loadingDepartments || loadingPhases || loadingMilestones;

  const { scheduledGroups, unscheduledIssues, timelineStart, timelineEnd } = useMemo(() => {
    const scheduled: Issue[] = [];
    const unscheduled: Issue[] = [];

    for (const issue of issues) {
      if (issue.start_date && issue.due_date) {
        scheduled.push(issue);
      } else {
        unscheduled.push(issue);
      }
    }

    // Group by department
    const deptMap = new Map<string | null, Issue[]>();
    for (const issue of scheduled) {
      const key = issue.department_id;
      if (!deptMap.has(key)) {
        deptMap.set(key, []);
      }
      deptMap.get(key)!.push(issue);
    }

    // Build groups sorted by department sort_order
    const deptById = new Map(departments.map((d) => [d.id, d]));
    const groups: DepartmentGroup[] = [];

    // Departments with issues, sorted
    const sortedDeptIds = [...deptMap.keys()]
      .filter((id) => id !== null)
      .sort((a, b) => {
        const da = deptById.get(a!);
        const db = deptById.get(b!);
        return (da?.sort_order ?? 0) - (db?.sort_order ?? 0);
      });

    for (const deptId of sortedDeptIds) {
      groups.push({
        department: deptById.get(deptId!) ?? null,
        issues: deptMap.get(deptId)!,
      });
    }

    // Unclassified group (null department_id)
    if (deptMap.has(null)) {
      groups.push({
        department: null,
        issues: deptMap.get(null)!,
      });
    }

    // Calculate timeline range
    const allDates: Date[] = [];

    for (const issue of scheduled) {
      allDates.push(new Date(issue.start_date!));
      allDates.push(new Date(issue.due_date!));
    }

    for (const phase of phases) {
      if (phase.start_date) allDates.push(new Date(phase.start_date));
      if (phase.end_date) allDates.push(new Date(phase.end_date));
    }

    for (const milestone of milestones) {
      if (milestone.date) allDates.push(new Date(milestone.date));
    }

    let start: Date;
    let end: Date;

    if (allDates.length > 0) {
      const timestamps = allDates.map((d) => d.getTime());
      start = new Date(Math.min(...timestamps));
      end = new Date(Math.max(...timestamps));
      // Normalize to start of day (strip time component)
      start = new Date(start.getFullYear(), start.getMonth(), start.getDate());
      end = new Date(end.getFullYear(), end.getMonth(), end.getDate());
      // Add 1 week padding
      start.setDate(start.getDate() - 7);
      end.setDate(end.getDate() + 7);
    } else {
      // Default to current month
      const now = new Date();
      start = new Date(now.getFullYear(), now.getMonth(), 1);
      end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    }

    return {
      scheduledGroups: groups,
      unscheduledIssues: unscheduled,
      timelineStart: start,
      timelineEnd: end,
    };
  }, [issues, departments, phases, milestones]);

  return {
    scheduledGroups,
    unscheduledIssues,
    phases,
    milestones,
    departments,
    timelineStart,
    timelineEnd,
    isLoading,
  };
}
