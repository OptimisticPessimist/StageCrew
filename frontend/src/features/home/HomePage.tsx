import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/AuthProvider";
import { useOrganizations } from "./hooks/useOrganizations";
import { useProductions } from "./hooks/useProductions";
import { useHome } from "./hooks/useHome";
import { useSelectedOrg } from "./hooks/useSelectedOrg";
import { parseLocalDate } from "@/features/production/CountdownBadge";
import { api } from "@/api/client";
import type { HomeIssue, ProductionListItem, OrganizationSummary } from "@/types";

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

const TYPE_LABELS: Record<string, string> = {
  physical: "物理演劇",
  vr: "VR演劇",
  hybrid: "ハイブリッド",
};

const TYPE_COLORS: Record<string, string> = {
  physical: "bg-green-100 text-green-800",
  vr: "bg-purple-100 text-purple-800",
  hybrid: "bg-blue-100 text-blue-800",
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

function countdownText(openingDate: string): string {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const opening = parseLocalDate(openingDate);
  const diff = Math.round(
    (opening.getTime() - today.getTime()) / 86_400_000,
  );
  if (diff > 0) return `開幕まで${diff}日`;
  if (diff === 0) return "本番当日";
  return `開幕${Math.abs(diff)}日前`;
}

// ---- Issue Row ----
function HomeIssueRow({ issue }: { issue: HomeIssue }) {
  const boardPath = `/organizations/${issue.organization_id}/productions/${issue.production_id}/board`;
  return (
    <Link
      to={boardPath}
      className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 transition-colors"
    >
      <span
        className={`text-xs font-medium px-2 py-0.5 rounded shrink-0 ${PRIORITY_COLORS[issue.priority] || "bg-gray-100 text-gray-700"}`}
      >
        {PRIORITY_LABELS[issue.priority] || issue.priority}
      </span>
      <span className="text-sm text-gray-900 flex-1 truncate">
        {issue.title}
      </span>
      <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded shrink-0">
        {issue.production_name}
      </span>
      {issue.department_name && (
        <span className="text-xs text-gray-400 shrink-0">
          {issue.department_name}
        </span>
      )}
      {issue.status_name && (
        <span
          className="text-xs px-2 py-0.5 rounded-full border shrink-0"
          style={{
            borderColor: issue.status_color || "#d1d5db",
            color: issue.status_color || "#6b7280",
          }}
        >
          {issue.status_name}
        </span>
      )}
      {issue.due_date && (
        <span className="text-xs text-gray-500 shrink-0">
          {formatLocalDate(issue.due_date)}
        </span>
      )}
    </Link>
  );
}

// ---- Deadline Row ----
function HomeDeadlineRow({
  issue,
  variant,
}: {
  issue: HomeIssue;
  variant: "overdue" | "near";
}) {
  const boardPath = `/organizations/${issue.organization_id}/productions/${issue.production_id}/board`;
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
        className={`text-xs font-medium px-2 py-0.5 rounded shrink-0 ${PRIORITY_COLORS[issue.priority] || "bg-gray-100 text-gray-700"}`}
      >
        {PRIORITY_LABELS[issue.priority] || issue.priority}
      </span>
      <span className="text-sm text-gray-900 flex-1 truncate">
        {issue.title}
      </span>
      <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded shrink-0">
        {issue.production_name}
      </span>
      {issue.department_name && (
        <span className="text-xs text-gray-500 shrink-0">
          {issue.department_name}
        </span>
      )}
      {issue.due_date && (
        <span className="text-xs text-gray-600 shrink-0">
          {formatLocalDate(issue.due_date)}
        </span>
      )}
      {days !== null && (
        <span
          className={`text-xs font-medium shrink-0 ${variant === "overdue" ? "text-red-700" : "text-amber-700"}`}
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

// ---- My Tasks Section ----
function MyTasksSection({ tasks }: { tasks: HomeIssue[] }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h2 className="text-base font-bold text-gray-900 mb-4">
        マイタスク
        {tasks.length > 0 && (
          <span className="text-sm font-normal text-gray-500 ml-2">
            ({tasks.length}件)
          </span>
        )}
      </h2>
      {tasks.length === 0 ? (
        <p className="text-sm text-gray-400">担当タスクはありません</p>
      ) : (
        <div className="space-y-1">
          {tasks.map((task) => (
            <HomeIssueRow key={task.id} issue={task} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Deadline Section ----
function DeadlineSection({
  warnings,
}: {
  warnings: { overdue: HomeIssue[]; near_deadline: HomeIssue[] };
}) {
  const hasWarnings =
    warnings.overdue.length > 0 || warnings.near_deadline.length > 0;

  if (!hasWarnings) return null;

  return (
    <div className="bg-white rounded-lg border p-6">
      <h2 className="text-base font-bold text-gray-900 mb-4">期限警告</h2>
      <div className="space-y-4">
        {warnings.overdue.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-red-700 mb-2">
              期限切れ ({warnings.overdue.length}件)
            </h3>
            <div className="space-y-2">
              {warnings.overdue.map((issue) => (
                <HomeDeadlineRow
                  key={issue.id}
                  issue={issue}
                  variant="overdue"
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
                <HomeDeadlineRow
                  key={issue.id}
                  issue={issue}
                  variant="near"
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Production Card ----
function ProductionCard({
  prod,
  orgId,
}: {
  prod: ProductionListItem;
  orgId: string;
}) {
  const base = `/organizations/${orgId}/productions/${prod.id}`;

  return (
    <div className="border rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="font-medium text-gray-900">{prod.name}</h3>
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[prod.production_type] ?? "bg-gray-100 text-gray-800"}`}
        >
          {TYPE_LABELS[prod.production_type] ?? prod.production_type}
        </span>
        {prod.current_phase && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
            {prod.current_phase}
          </span>
        )}
        {prod.opening_date && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
            {countdownText(prod.opening_date)}
          </span>
        )}
      </div>
      {(prod.opening_date || prod.closing_date) && (
        <p className="text-xs text-gray-500 mb-3">
          {prod.opening_date &&
            new Date(prod.opening_date).toLocaleDateString()}
          {prod.opening_date && prod.closing_date && " 〜 "}
          {prod.closing_date &&
            new Date(prod.closing_date).toLocaleDateString()}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Link
          to={`${base}/dashboard`}
          className="text-sm px-3 py-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
        >
          ダッシュボード
        </Link>
        <Link
          to={`${base}/board`}
          className="text-sm px-3 py-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
        >
          カンバンボード
        </Link>
        <Link
          to={`${base}/gantt`}
          className="text-sm px-3 py-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
        >
          ガントチャート
        </Link>
        <Link
          to={`${base}/departments`}
          className="text-sm px-3 py-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
        >
          部門管理
        </Link>
        <Link
          to={`${base}/members`}
          className="text-sm px-3 py-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
        >
          メンバー
        </Link>
      </div>
    </div>
  );
}

// ---- Production Section (for selected org) ----
function ProductionSection({ orgId }: { orgId: string }) {
  const { data: productions, isLoading } = useProductions(orgId);

  if (isLoading) {
    return <p className="text-sm text-gray-400 py-2">読み込み中...</p>;
  }

  if (!productions || productions.length === 0) {
    return <p className="text-sm text-gray-400 py-2">公演がありません</p>;
  }

  return (
    <div className="space-y-3">
      {productions.map((prod) => (
        <ProductionCard key={prod.id} prod={prod} orgId={orgId} />
      ))}
    </div>
  );
}

// ---- Create Organization Form ----
function CreateOrganizationForm() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  const createOrg = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.post<OrganizationSummary>("/organizations", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      setName("");
      setDescription("");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createOrg.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
    });
  };

  return (
    <div className="bg-white rounded-lg border p-6 max-w-md mx-auto">
      <h2 className="text-base font-bold text-gray-900 mb-4">
        団体を作成
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            団体名
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例: 劇団ステージクルー"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            説明（任意）
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="団体の説明"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={!name.trim() || createOrg.isPending}
          className="w-full bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {createOrg.isPending ? "作成中..." : "団体を作成"}
        </button>
      </form>
    </div>
  );
}

// ---- Main Page ----
export default function HomePage() {
  const { user, logout } = useAuth();
  const { data: organizations, isLoading: orgsLoading } = useOrganizations();
  const { data: homeData, isLoading: homeLoading } = useHome();
  const [selectedOrgId, setSelectedOrgId] = useSelectedOrg(organizations);

  const selectedOrg = organizations?.find((o) => o.id === selectedOrgId);

  return (
    <div className="min-h-screen bg-gray-100">
      {/* ヘッダー */}
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-gray-900">StageCrew</h1>
          {organizations && organizations.length > 0 && (
            <select
              value={selectedOrgId ?? ""}
              onChange={(e) => setSelectedOrgId(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none bg-white"
            >
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.display_name}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ログアウト
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto py-8 px-4 space-y-6">
        {orgsLoading ? (
          <p className="text-center text-gray-500">読み込み中...</p>
        ) : !organizations || organizations.length === 0 ? (
          <div className="py-16 space-y-8">
            <p className="text-center text-gray-500">
              所属する団体がありません
            </p>
            <CreateOrganizationForm />
          </div>
        ) : (
          <>
            {/* マイタスク（全公演横断） */}
            {homeLoading ? (
              <div className="bg-white rounded-lg border p-6">
                <p className="text-sm text-gray-400">タスクを読み込み中...</p>
              </div>
            ) : homeData ? (
              <>
                <MyTasksSection tasks={homeData.my_tasks} />
                <DeadlineSection warnings={homeData.deadline_warnings} />
              </>
            ) : null}

            {/* 選択中の団体の公演一覧 */}
            {selectedOrg && (
              <div className="bg-white rounded-lg border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-bold text-gray-900">
                    {selectedOrg.name} の公演
                  </h2>
                  <Link
                    to={`/organizations/${selectedOrg.id}/members`}
                    className="text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    メンバー管理 ({selectedOrg.member_count})
                  </Link>
                </div>
                <ProductionSection orgId={selectedOrg.id} />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
