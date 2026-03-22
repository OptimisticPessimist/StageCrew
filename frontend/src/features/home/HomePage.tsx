import { Link } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthProvider";
import { useOrganizations } from "./hooks/useOrganizations";
import { useProductions } from "./hooks/useProductions";
import type { OrganizationSummary } from "@/types";

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
      {productions.map((prod) => {
        const base = `/organizations/${orgId}/productions/${prod.id}`;
        return (
          <div
            key={prod.id}
            className="border rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
          >
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
      })}
    </div>
  );
}

function OrganizationCard({ org }: { org: OrganizationSummary }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{org.name}</h2>
          {org.description && (
            <p className="text-sm text-gray-500 mt-1">{org.description}</p>
          )}
        </div>
        <Link
          to={`/organizations/${org.id}/members`}
          className="text-sm text-indigo-600 hover:text-indigo-800"
        >
          メンバー管理 ({org.member_count})
        </Link>
      </div>
      <ProductionSection orgId={org.id} />
    </div>
  );
}

export default function HomePage() {
  const { user, logout } = useAuth();
  const { data: organizations, isLoading } = useOrganizations();

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <h1 className="text-lg font-bold text-gray-900">StageCrew</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {user?.display_name}
          </span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ログアウト
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto py-8 px-4">
        {isLoading ? (
          <p className="text-center text-gray-500">読み込み中...</p>
        ) : !organizations || organizations.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-500">所属する団体がありません</p>
          </div>
        ) : (
          <div className="space-y-6">
            {organizations.map((org) => (
              <OrganizationCard key={org.id} org={org} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
