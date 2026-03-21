import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useOrgMembers,
  useAddOrgMember,
  useUpdateOrgMember,
  useRemoveOrgMember,
} from "./hooks/useOrgMembers";
import {
  useInvitations,
  useCreateInvitation,
  useCancelInvitation,
} from "./hooks/useInvitations";

const ROLE_LABELS: Record<string, string> = {
  owner: "オーナー",
  admin: "管理者",
  member: "メンバー",
};

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber-100 text-amber-800",
  admin: "bg-blue-100 text-blue-800",
  member: "bg-gray-100 text-gray-700",
};

export default function OrgMembersPage() {
  const { orgId } = useParams<{ orgId: string }>();

  const { data: members = [], isLoading } = useOrgMembers(orgId!);
  const addMember = useAddOrgMember(orgId!);
  const updateMember = useUpdateOrgMember(orgId!);
  const removeMember = useRemoveOrgMember(orgId!);

  const { data: invitations = [] } = useInvitations(orgId!);
  const createInvitation = useCreateInvitation(orgId!);
  const cancelInvitation = useCancelInvitation(orgId!);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newUserId, setNewUserId] = useState("");
  const [newRole, setNewRole] = useState("member");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserId.trim()) return;
    addMember.mutate(
      { user_id: newUserId.trim(), org_role: newRole },
      {
        onSuccess: () => {
          setNewUserId("");
          setShowAddForm(false);
        },
      },
    );
  };

  const handleInvite = () => {
    createInvitation.mutate({});
  };

  const handleCopyLink = (token: string) => {
    const url = `${window.location.origin}/invitations/${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
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
          <Link to="/" className="text-gray-400 hover:text-gray-600 text-sm">
            &larr; ホーム
          </Link>
          <h1 className="text-lg font-bold text-gray-900">メンバー管理</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleInvite}
            className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
          >
            招待リンクを作成
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
          >
            + メンバーを追加
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        {/* 招待一覧 */}
        {invitations.length > 0 && (
          <div className="bg-white rounded-lg border">
            <div className="px-4 py-3 border-b">
              <h2 className="text-sm font-medium text-gray-700">
                保留中の招待 ({invitations.length})
              </h2>
            </div>
            <div className="divide-y">
              {invitations.map((inv) => (
                <div
                  key={inv.id}
                  className="px-4 py-3 flex items-center justify-between"
                >
                  <div className="text-sm">
                    <span className="text-gray-600">
                      {inv.email || "リンク招待"}
                    </span>
                    <span className="text-gray-400 ml-2">
                      ({ROLE_LABELS[inv.org_role] || inv.org_role})
                    </span>
                    <span className="text-gray-400 ml-2 text-xs">
                      by {inv.invited_by_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleCopyLink(inv.token)}
                      className="text-xs text-indigo-600 hover:text-indigo-700"
                    >
                      {copiedToken === inv.token
                        ? "コピー済み!"
                        : "リンクをコピー"}
                    </button>
                    <button
                      onClick={() => cancelInvitation.mutate(inv.id)}
                      className="text-xs text-red-400 hover:text-red-600"
                    >
                      取消
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* メンバー追加フォーム */}
        {showAddForm && (
          <form
            onSubmit={handleAdd}
            className="bg-white rounded-lg border p-4 flex items-center gap-3"
          >
            <input
              type="text"
              value={newUserId}
              onChange={(e) => setNewUserId(e.target.value)}
              placeholder="ユーザーID (UUID)"
              className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              autoFocus
            />
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="member">メンバー</option>
              <option value="admin">管理者</option>
            </select>
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
          </form>
        )}

        {/* メンバー一覧 */}
        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b">
            <h2 className="text-sm font-medium text-gray-700">
              メンバー ({members.length})
            </h2>
          </div>
          <div className="divide-y">
            {members.map((m) => (
              <div
                key={m.id}
                className="px-4 py-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium text-gray-600">
                    {m.display_name.charAt(0)}
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-900">
                      {m.display_name}
                    </span>
                    <span
                      className={`ml-2 text-xs px-1.5 py-0.5 rounded ${ROLE_COLORS[m.org_role] || "bg-gray-100"}`}
                    >
                      {ROLE_LABELS[m.org_role] || m.org_role}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {m.org_role !== "owner" && (
                    <>
                      <select
                        value={m.org_role}
                        onChange={(e) =>
                          updateMember.mutate({
                            membershipId: m.id,
                            org_role: e.target.value,
                          })
                        }
                        className="text-xs rounded border border-gray-300 px-1 py-0.5"
                      >
                        <option value="member">メンバー</option>
                        <option value="admin">管理者</option>
                        <option value="owner">オーナー</option>
                      </select>
                      <button
                        onClick={() => removeMember.mutate(m.id)}
                        className="text-xs text-red-400 hover:text-red-600"
                      >
                        除外
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
