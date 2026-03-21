import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { Department } from "@/types";
import {
  useDepartments,
  useCreateDepartment,
  useUpdateDepartment,
  useDeleteDepartment,
  useCreateStaffRole,
  useDeleteStaffRole,
} from "./hooks/useDepartments";

export default function DepartmentsPage() {
  const { orgId, productionId } = useParams<{
    orgId: string;
    productionId: string;
  }>();

  const { data: departments = [], isLoading } = useDepartments(
    orgId!,
    productionId!,
  );
  const createDept = useCreateDepartment(orgId!, productionId!);
  const updateDept = useUpdateDepartment(orgId!, productionId!);
  const deleteDept = useDeleteDepartment(orgId!, productionId!);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#6366f1");
  const [expandedDept, setExpandedDept] = useState<string | null>(null);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createDept.mutate(
      { name: newName.trim(), color: newColor },
      {
        onSuccess: () => {
          setNewName("");
          setShowCreateForm(false);
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
          <h1 className="text-lg font-bold text-gray-900">部門管理</h1>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
        >
          + 部門を追加
        </button>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-4">
        {showCreateForm && (
          <form
            onSubmit={handleCreate}
            className="bg-white rounded-lg border p-4 flex items-center gap-3"
          >
            <input
              type="color"
              value={newColor}
              onChange={(e) => setNewColor(e.target.value)}
              className="w-8 h-8 rounded cursor-pointer"
            />
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="部門名"
              className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={!newName.trim()}
              className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
            >
              作成
            </button>
            <button
              type="button"
              onClick={() => setShowCreateForm(false)}
              className="px-2 py-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              キャンセル
            </button>
          </form>
        )}

        {departments.length === 0 && !showCreateForm ? (
          <div className="text-center py-12 text-gray-500">
            <p className="mb-2">まだ部門がありません</p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="text-indigo-600 hover:text-indigo-700 text-sm font-medium"
            >
              最初の部門を作成
            </button>
          </div>
        ) : (
          departments.map((dept) => (
            <DepartmentCard
              key={dept.id}
              dept={dept}
              orgId={orgId!}
              productionId={productionId!}
              expanded={expandedDept === dept.id}
              onToggle={() =>
                setExpandedDept(expandedDept === dept.id ? null : dept.id)
              }
              onUpdate={(body) =>
                updateDept.mutate({ deptId: dept.id, body })
              }
              onDelete={() => deleteDept.mutate(dept.id)}
            />
          ))
        )}
      </main>
    </div>
  );
}

function DepartmentCard({
  dept,
  orgId,
  productionId,
  expanded,
  onToggle,
  onUpdate,
  onDelete,
}: {
  dept: Department;
  orgId: string;
  productionId: string;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (body: { name?: string; color?: string }) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(dept.name);
  const [editColor, setEditColor] = useState(dept.color || "#6366f1");
  const [newRoleName, setNewRoleName] = useState("");

  const createRole = useCreateStaffRole(orgId, productionId, dept.id);
  const deleteRole = useDeleteStaffRole(orgId, productionId, dept.id);

  const handleSave = () => {
    onUpdate({ name: editName, color: editColor });
    setEditing(false);
  };

  const handleAddRole = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoleName.trim()) return;
    createRole.mutate(
      { name: newRoleName.trim(), sort_order: dept.staff_roles.length },
      { onSuccess: () => setNewRoleName("") },
    );
  };

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="p-4 flex items-center gap-3">
        <div
          className="w-4 h-4 rounded-full shrink-0"
          style={{ backgroundColor: dept.color || "#94a3b8" }}
        />
        {editing ? (
          <div className="flex items-center gap-2 flex-1">
            <input
              type="color"
              value={editColor}
              onChange={(e) => setEditColor(e.target.value)}
              className="w-8 h-8 rounded cursor-pointer"
            />
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="flex-1 rounded border border-gray-300 px-3 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
            />
            <button
              onClick={handleSave}
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              保存
            </button>
            <button
              onClick={() => setEditing(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              取消
            </button>
          </div>
        ) : (
          <>
            <span className="font-medium text-gray-900 flex-1">
              {dept.name}
            </span>
            <span className="text-xs text-gray-400">
              {dept.staff_roles.length}ロール
            </span>
            <button
              onClick={onToggle}
              className="text-sm text-gray-400 hover:text-gray-600"
            >
              {expanded ? "閉じる" : "詳細"}
            </button>
            <button
              onClick={() => {
                setEditName(dept.name);
                setEditColor(dept.color || "#6366f1");
                setEditing(true);
              }}
              className="text-sm text-gray-400 hover:text-gray-600"
            >
              編集
            </button>
            <button
              onClick={onDelete}
              className="text-sm text-red-400 hover:text-red-600"
            >
              削除
            </button>
          </>
        )}
      </div>

      {expanded && (
        <div className="border-t px-4 py-3 bg-gray-50">
          <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
            スタッフロール
          </h4>
          <div className="space-y-1 mb-3">
            {dept.staff_roles.map((role) => (
              <div
                key={role.id}
                className="flex items-center justify-between py-1"
              >
                <span className="text-sm text-gray-700">{role.name}</span>
                <button
                  onClick={() => deleteRole.mutate(role.id)}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  削除
                </button>
              </div>
            ))}
            {dept.staff_roles.length === 0 && (
              <p className="text-xs text-gray-400">ロールなし</p>
            )}
          </div>
          <form onSubmit={handleAddRole} className="flex items-center gap-2">
            <input
              type="text"
              value={newRoleName}
              onChange={(e) => setNewRoleName(e.target.value)}
              placeholder="ロール名を入力"
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
            />
            <button
              type="submit"
              disabled={!newRoleName.trim()}
              className="px-2 py-1 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
            >
              追加
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
