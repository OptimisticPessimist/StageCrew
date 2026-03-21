import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useProductionMembers,
  useAddProductionMember,
  useUpdateProductionMember,
  useRemoveProductionMember,
} from "./hooks/useProductionMembers";

const ROLE_LABELS: Record<string, string> = {
  manager: "マネージャー",
  member: "メンバー",
};

export default function ProductionMembersPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const { data: members = [], isLoading } = useProductionMembers(
    orgId!,
    productionId!,
  );
  const addMember = useAddProductionMember(orgId!, productionId!);
  const updateMember = useUpdateProductionMember(orgId!, productionId!);
  const removeMember = useRemoveProductionMember(orgId!, productionId!);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newUserId, setNewUserId] = useState("");
  const [newRole, setNewRole] = useState("member");
  const [newIsCast, setNewIsCast] = useState(false);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserId.trim()) return;
    addMember.mutate(
      {
        user_id: newUserId.trim(),
        production_role: newRole,
        is_cast: newIsCast,
      },
      {
        onSuccess: () => {
          setNewUserId("");
          setShowAddForm(false);
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to={`/organizations/${orgId}/productions/${productionId}/board`}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            &larr; ボード
          </Link>
          <h1 className="text-lg font-bold text-gray-900">公演メンバー管理</h1>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
        >
          + メンバーを追加
        </button>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-4">
        {showAddForm && (
          <form
            onSubmit={handleAdd}
            className="bg-white rounded-lg border p-4 space-y-3"
          >
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={newUserId}
                onChange={(e) => setNewUserId(e.target.value)}
                placeholder="ユーザーID (UUID) ※団体メンバーであること"
                className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                autoFocus
              />
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="member">メンバー</option>
                <option value="manager">マネージャー</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={newIsCast}
                  onChange={(e) => setNewIsCast(e.target.checked)}
                  className="rounded"
                />
                キャスト
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={!newUserId.trim()}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
                >
                  追加
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  キャンセル
                </button>
              </div>
            </div>
          </form>
        )}

        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b">
            <h2 className="text-sm font-medium text-gray-700">
              メンバー ({members.length})
            </h2>
          </div>
          <div className="divide-y">
            {members.map((m) => (
              <div key={m.id} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium text-gray-600">
                      {m.display_name.charAt(0)}
                    </div>
                    <div>
                      <span className="text-sm font-medium text-gray-900">
                        {m.display_name}
                      </span>
                      <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                        {ROLE_LABELS[m.production_role] || m.production_role}
                      </span>
                      {m.is_cast && (
                        <span className="ml-1 text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                          キャスト
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={m.production_role}
                      onChange={(e) =>
                        updateMember.mutate({
                          membershipId: m.id,
                          body: { production_role: e.target.value },
                        })
                      }
                      className="text-xs rounded border border-gray-300 px-1 py-0.5"
                    >
                      <option value="member">メンバー</option>
                      <option value="manager">マネージャー</option>
                    </select>
                    <button
                      onClick={() =>
                        updateMember.mutate({
                          membershipId: m.id,
                          body: { is_cast: !m.is_cast },
                        })
                      }
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      {m.is_cast ? "キャスト解除" : "キャスト設定"}
                    </button>
                    <button
                      onClick={() => removeMember.mutate(m.id)}
                      className="text-xs text-red-400 hover:text-red-600"
                    >
                      除外
                    </button>
                  </div>
                </div>
                {m.department_memberships.length > 0 && (
                  <div className="mt-2 ml-11 flex flex-wrap gap-1">
                    {m.department_memberships.map((dm) => (
                      <span
                        key={dm.id}
                        className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600"
                      >
                        {dm.department_name}
                        {dm.staff_role_name && ` / ${dm.staff_role_name}`}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {members.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-400 text-sm">
                メンバーがいません
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
