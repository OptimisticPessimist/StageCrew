import { useParams, Link } from "react-router-dom";
import { useDashboard } from "./hooks/useDashboard";
import CountdownBadge from "@/features/production/CountdownBadge";
import type {
  DashboardIssue,
  DepartmentProgress,
  ProgressSummary,
  StatusCount,
} from "@/types";

const PRIORITY_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-blue-100 text-blue-800",
};


function formatLocalDate(utcDateStr: string): string {
  const d = new Date(utcDateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function daysFromNow(utcDateStr: string): number {
  const due = new Date(utcDateStr);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export default function DashboardPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const { data, isLoading } = useDashboard(orgId!, productionId!);

  if (isLoading || !data) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  const { progress, my_tasks, deadline_warnings } = data;
  const boardPath = `/organizations/${orgId}/productions/${productionId}/board`;
  const ganttPath = `/organizations/${orgId}/productions/${productionId}/gantt`;
  const scriptsPath = `/organizations/${orgId}/productions/${productionId}/scripts`;
  const calendarPath = `/organizations/${orgId}/productions/${productionId}/calendar`;

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* ヘッダー */}
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-gray-400 hover:text-gray-600 text-sm">
            &larr; ホーム
          </Link>
          <h1 className="text-lg font-bold text-gray-900">ダッシュボード</h1>
          <Link
            to={boardPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            カンバンボード
          </Link>
          <Link
            to={ganttPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            ガントチャート
          </Link>
          <Link
            to={scriptsPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            脚本
          </Link>
          <Link
            to={calendarPath}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            カレンダー
          </Link>
          <CountdownBadge orgId={orgId!} productionId={productionId!} />
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6 space-y-6">
        {/* 公演進捗サマリー */}
        <ProgressSection progress={progress} />

        {/* 2カラムレイアウト */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 担当タスク一覧 */}
          <MyTasksSection tasks={my_tasks} boardPath={boardPath} />

          {/* 期限警告 */}
          <DeadlineSection warnings={deadline_warnings} boardPath={boardPath} />
        </div>
      </main>
    </div>
  );
}

// ---- 公演進捗サマリー ----
function ProgressSection({
  progress,
}: {
  progress: ProgressSummary;
}) {
  const pct = progress.completion_percentage;

  return (
    <div className="bg-white rounded-lg border p-6 space-y-5">
      <h2 className="text-base font-bold text-gray-900">公演進捗サマリー</h2>

      {/* 全体統計 */}
      <div className="flex flex-wrap gap-6 items-center">
        <div className="space-y-1">
          <div className="text-sm text-gray-500">全体進捗</div>
          <div className="text-2xl font-bold text-gray-900">
            {progress.completed_issues}/{progress.total_issues}
            <span className="text-sm font-normal text-gray-500 ml-2">
              ({pct}%)
            </span>
          </div>
        </div>

        {progress.current_phase && (
          <div className="space-y-1">
            <div className="text-sm text-gray-500">現在フェーズ</div>
            <div className="text-sm font-medium text-indigo-700 bg-indigo-50 px-3 py-1 rounded-full">
              {progress.current_phase}
            </div>
          </div>
        )}

        {progress.days_to_opening !== null && (
          <div className="space-y-1">
            <div className="text-sm text-gray-500">開演まで</div>
            <div className="text-lg font-bold text-gray-900">
              {progress.days_to_opening > 0
                ? `${progress.days_to_opening}日`
                : progress.days_to_opening === 0
                  ? "本日"
                  : `${Math.abs(progress.days_to_opening)}日前`}
            </div>
          </div>
        )}

        {progress.days_to_closing !== null && (
          <div className="space-y-1">
            <div className="text-sm text-gray-500">千秋楽まで</div>
            <div className="text-lg font-bold text-gray-900">
              {progress.days_to_closing > 0
                ? `${progress.days_to_closing}日`
                : progress.days_to_closing === 0
                  ? "本日"
                  : `${Math.abs(progress.days_to_closing)}日前`}
            </div>
          </div>
        )}
      </div>

      {/* プログレスバー */}
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className="bg-indigo-600 h-3 rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      {/* 部門別進捗 & ステータス分布 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {progress.by_department.length > 0 && (
          <DepartmentBreakdown departments={progress.by_department} />
        )}
        {progress.by_status.length > 0 && (
          <StatusBreakdown statuses={progress.by_status} />
        )}
      </div>
    </div>
  );
}

function DepartmentBreakdown({
  departments,
}: {
  departments: DepartmentProgress[];
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-3">部門別進捗</h3>
      <div className="space-y-2">
        {departments.map((dept) => {
          const pct = dept.total > 0 ? (dept.completed / dept.total) * 100 : 0;
          return (
            <div key={dept.department_id} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: dept.department_color || "#9ca3af" }}
              />
              <div className="text-sm text-gray-700 w-24 truncate">
                {dept.department_name}
              </div>
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-indigo-500 h-2 rounded-full transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 w-16 text-right">
                {dept.completed}/{dept.total}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatusBreakdown({ statuses }: { statuses: StatusCount[] }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-3">
        ステータス別分布
      </h3>
      <div className="flex flex-wrap gap-2">
        {statuses.map((s, i) => (
          <span
            key={s.status_id ?? `none-${i}`}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm border"
            style={{
              borderColor: s.status_color || "#d1d5db",
              color: s.status_color || "#6b7280",
            }}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: s.status_color || "#9ca3af" }}
            />
            {s.status_name}
            <span className="font-bold">{s.count}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ---- 担当タスク ----
function MyTasksSection({
  tasks,
  boardPath,
}: {
  tasks: DashboardIssue[];
  boardPath: string;
}) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h2 className="text-base font-bold text-gray-900 mb-4">
        担当タスク一覧
        {tasks.length > 0 && (
          <span className="text-sm font-normal text-gray-500 ml-2">
            ({tasks.length}件)
          </span>
        )}
      </h2>
      {tasks.length === 0 ? (
        <p className="text-sm text-gray-400">担当タスクはありません</p>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <IssueRow key={task.id} issue={task} boardPath={boardPath} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---- 期限警告 ----
function DeadlineSection({
  warnings,
  boardPath,
}: {
  warnings: { overdue: DashboardIssue[]; near_deadline: DashboardIssue[] };
  boardPath: string;
}) {
  const hasWarnings =
    warnings.overdue.length > 0 || warnings.near_deadline.length > 0;

  return (
    <div className="bg-white rounded-lg border p-6">
      <h2 className="text-base font-bold text-gray-900 mb-4">期限警告</h2>
      {!hasWarnings ? (
        <p className="text-sm text-gray-400">期限警告はありません</p>
      ) : (
        <div className="space-y-4">
          {warnings.overdue.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-red-700 mb-2">
                期限切れ ({warnings.overdue.length}件)
              </h3>
              <div className="space-y-2">
                {warnings.overdue.map((issue) => (
                  <DeadlineRow
                    key={issue.id}
                    issue={issue}
                    variant="overdue"
                    boardPath={boardPath}
                  />
                ))}
              </div>
            </div>
          )}
          {warnings.near_deadline.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-amber-700 mb-2">
                期限間近 ({warnings.near_deadline.length}件)
              </h3>
              <div className="space-y-2">
                {warnings.near_deadline.map((issue) => (
                  <DeadlineRow
                    key={issue.id}
                    issue={issue}
                    variant="near"
                    boardPath={boardPath}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---- 共通行コンポーネント ----
function IssueRow({
  issue,
  boardPath,
}: {
  issue: DashboardIssue;
  boardPath: string;
}) {
  return (
    <Link
      to={boardPath}
      className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 transition-colors"
    >
      <span
        className={`text-xs font-medium px-2 py-0.5 rounded ${PRIORITY_COLORS[issue.priority] || "bg-gray-100 text-gray-700"}`}
      >
        {PRIORITY_LABELS[issue.priority] || issue.priority}
      </span>
      <span className="text-sm text-gray-900 flex-1 truncate">
        {issue.title}
      </span>
      {issue.department_name && (
        <span className="text-xs text-gray-400">{issue.department_name}</span>
      )}
      {issue.status_name && (
        <span
          className="text-xs px-2 py-0.5 rounded-full border"
          style={{
            borderColor: issue.status_color || "#d1d5db",
            color: issue.status_color || "#6b7280",
          }}
        >
          {issue.status_name}
        </span>
      )}
      {issue.due_date && (
        <span className="text-xs text-gray-500">
          {formatLocalDate(issue.due_date)}
        </span>
      )}
    </Link>
  );
}

function DeadlineRow({
  issue,
  variant,
  boardPath,
}: {
  issue: DashboardIssue;
  variant: "overdue" | "near";
  boardPath: string;
}) {
  const bgClass =
    variant === "overdue"
      ? "bg-red-50 border-red-200"
      : "bg-amber-50 border-amber-200";

  const days = issue.due_date ? daysFromNow(issue.due_date) : null;

  return (
    <Link
      to={boardPath}
      className={`flex items-center gap-3 p-2 rounded border ${bgClass} hover:opacity-80 transition-opacity`}
    >
      <span
        className={`text-xs font-medium px-2 py-0.5 rounded ${PRIORITY_COLORS[issue.priority] || "bg-gray-100 text-gray-700"}`}
      >
        {PRIORITY_LABELS[issue.priority] || issue.priority}
      </span>
      <span className="text-sm text-gray-900 flex-1 truncate">
        {issue.title}
      </span>
      {issue.department_name && (
        <span className="text-xs text-gray-500">{issue.department_name}</span>
      )}
      {issue.due_date && (
        <span className="text-xs text-gray-600">
          {formatLocalDate(issue.due_date)}
        </span>
      )}
      {days !== null && (
        <span
          className={`text-xs font-medium ${variant === "overdue" ? "text-red-700" : "text-amber-700"}`}
        >
          {variant === "overdue"
            ? `${Math.abs(days)}日超過`
            : days === 0
              ? "本日"
              : `あと${days}日`}
        </span>
      )}
    </Link>
  );
}

