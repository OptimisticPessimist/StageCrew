import { useMemo, useState } from "react";
import type { ScriptCharacter } from "@/types";
import { useProductionMembers } from "@/features/members/hooks/useProductionMembers";
import {
  useCreateCasting,
  useDeleteCasting,
  useUpdateCasting,
} from "./hooks/useCastings";

interface Props {
  character: ScriptCharacter;
  orgId: string;
  productionId: string;
  scriptId: string;
}

export default function CharacterCastingEditor({
  character,
  orgId,
  productionId,
  scriptId,
}: Props) {
  const { data: members = [], isLoading: membersLoading } =
    useProductionMembers(orgId, productionId);
  const createCasting = useCreateCasting(orgId, productionId, scriptId);
  const updateCasting = useUpdateCasting(orgId, productionId, scriptId);
  const deleteCasting = useDeleteCasting(orgId, productionId, scriptId);

  const assignedIds = useMemo(
    () => new Set(character.castings.map((c) => c.production_membership_id)),
    [character.castings],
  );

  const selectableMembers = useMemo(
    () => members.filter((m) => !assignedIds.has(m.id)),
    [members, assignedIds],
  );

  const [selectedMemberId, setSelectedMemberId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [memo, setMemo] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMemberId) {
      setError("メンバーを選択してください");
      return;
    }
    setError(null);
    createCasting.mutate(
      {
        character_id: character.id,
        production_membership_id: selectedMemberId,
        display_name: displayName.trim() || null,
        memo: memo.trim() || null,
        sort_order: character.castings.length,
      },
      {
        onSuccess: () => {
          setSelectedMemberId("");
          setDisplayName("");
          setMemo("");
        },
        onError: (err) =>
          setError(
            err instanceof Error ? err.message : "配役の追加に失敗しました",
          ),
      },
    );
  };

  return (
    <div className="mt-3 border-t pt-3 space-y-3 bg-gray-50/60 -mx-4 -mb-4 px-4 pb-4 rounded-b-lg">
      <h4 className="text-xs font-medium text-gray-500 uppercase">配役</h4>

      {character.castings.length === 0 ? (
        <p className="text-xs text-gray-400">まだ配役がありません</p>
      ) : (
        <ul className="space-y-2">
          {character.castings.map((cast) => (
            <CastingEditRow
              key={cast.id}
              castingId={cast.id}
              defaultDisplayName={cast.display_name}
              defaultMemo={cast.memo}
              memberLabel={
                members.find((m) => m.id === cast.production_membership_id)
                  ?.display_name || "（未参加メンバー）"
              }
              onSave={(body) =>
                updateCasting.mutateAsync({ castingId: cast.id, body })
              }
              onDelete={() => deleteCasting.mutate(cast.id)}
            />
          ))}
        </ul>
      )}

      <form
        onSubmit={handleAdd}
        className="space-y-2 pt-2 border-t border-gray-200"
      >
        <h5 className="text-xs font-medium text-gray-500">配役を追加</h5>
        <div className="flex flex-col gap-2">
          <select
            value={selectedMemberId}
            onChange={(e) => setSelectedMemberId(e.target.value)}
            disabled={membersLoading}
            className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          >
            <option value="">メンバーを選択...</option>
            {selectableMembers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
                {m.is_cast ? "" : "（スタッフ）"}
              </option>
            ))}
          </select>
          {selectableMembers.length === 0 && !membersLoading && (
            <p className="text-xs text-gray-400">
              割当可能なメンバーがいません（全員既に配役済）
            </p>
          )}
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="表示名（任意: 例「Aキャスト」）"
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          />
          <input
            type="text"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            placeholder="メモ（任意）"
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          />
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!selectedMemberId || createCasting.isPending}
            className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-40"
          >
            追加
          </button>
        </div>
      </form>
    </div>
  );
}

function CastingEditRow({
  castingId,
  defaultDisplayName,
  defaultMemo,
  memberLabel,
  onSave,
  onDelete,
}: {
  castingId: string;
  defaultDisplayName: string | null;
  defaultMemo: string | null;
  memberLabel: string;
  onSave: (body: {
    display_name: string | null;
    memo: string | null;
  }) => Promise<unknown>;
  onDelete: () => void;
}) {
  const [displayName, setDisplayName] = useState(defaultDisplayName || "");
  const [memo, setMemo] = useState(defaultMemo || "");
  const [saving, setSaving] = useState(false);

  const dirty =
    displayName !== (defaultDisplayName || "") ||
    memo !== (defaultMemo || "");

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({
        display_name: displayName.trim() || null,
        memo: memo.trim() || null,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <li
      className="bg-white rounded border border-gray-200 p-2 space-y-1.5"
      data-casting-id={castingId}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-800 flex-1 truncate">
          {memberLabel}
        </span>
        <button
          onClick={onDelete}
          className="text-xs text-red-400 hover:text-red-600"
        >
          削除
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="表示名"
          className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
        />
        <input
          type="text"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          placeholder="メモ"
          className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
        />
      </div>
      {dirty && (
        <div className="flex justify-end gap-2">
          <button
            onClick={() => {
              setDisplayName(defaultDisplayName || "");
              setMemo(defaultMemo || "");
            }}
            className="text-xs text-gray-400 hover:text-gray-600"
            disabled={saving}
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      )}
    </li>
  );
}
