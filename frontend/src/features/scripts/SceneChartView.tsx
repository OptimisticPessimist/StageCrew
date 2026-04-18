import { useState } from "react";
import type { AppearanceType, SceneChartCell } from "@/types";
import {
  useCreateMapping,
  useDeleteMapping,
  useGenerateSceneChart,
  useSceneChart,
  useUpdateMapping,
} from "./hooks/useSceneChart";

interface Props {
  orgId: string;
  productionId: string;
  scriptId: string;
}

// 表示順: dialogue → silent → off_stage → 空 → 空
const APPEARANCE_CYCLE: (AppearanceType | null)[] = [
  "dialogue",
  "silent",
  "off_stage",
  null,
];

const LABELS: Record<AppearanceType, { symbol: string; label: string; cls: string }> = {
  dialogue: {
    symbol: "◎",
    label: "セリフあり",
    cls: "bg-indigo-600 text-white",
  },
  silent: {
    symbol: "○",
    label: "登場のみ",
    cls: "bg-indigo-100 text-indigo-800",
  },
  off_stage: {
    symbol: "△",
    label: "声のみ",
    cls: "bg-amber-100 text-amber-800",
  },
};

export default function SceneChartView({
  orgId,
  productionId,
  scriptId,
}: Props) {
  const { data, isLoading } = useSceneChart(orgId, productionId, scriptId);
  const createMapping = useCreateMapping(orgId, productionId, scriptId);
  const updateMapping = useUpdateMapping(orgId, productionId, scriptId);
  const deleteMapping = useDeleteMapping(orgId, productionId, scriptId);
  const regenerate = useGenerateSceneChart(orgId, productionId, scriptId);

  const [busyKey, setBusyKey] = useState<string | null>(null);

  if (isLoading || !data) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center text-sm text-gray-500">
        読み込み中...
      </div>
    );
  }

  if (data.scenes.length === 0 || data.characters.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-12 text-center text-sm text-gray-500">
        シーンまたは登場人物が登録されていません
      </div>
    );
  }

  const handleCycle = async (
    sceneId: string,
    charId: string,
    cell: SceneChartCell | null,
  ) => {
    const key = `${sceneId}:${charId}`;
    if (busyKey) return;
    setBusyKey(key);
    try {
      const currentIdx = cell
        ? APPEARANCE_CYCLE.indexOf(cell.appearance_type as AppearanceType)
        : APPEARANCE_CYCLE.length - 1;
      const next =
        APPEARANCE_CYCLE[(currentIdx + 1) % APPEARANCE_CYCLE.length];

      if (!cell && next !== null) {
        await createMapping.mutateAsync({
          scene_id: sceneId,
          character_id: charId,
          appearance_type: next,
        });
      } else if (cell && next === null) {
        await deleteMapping.mutateAsync(cell.mapping_id);
      } else if (cell && next !== null) {
        await updateMapping.mutateAsync({
          mappingId: cell.mapping_id,
          body: { appearance_type: next },
        });
      }
    } finally {
      setBusyKey(null);
    }
  };

  const handleRegenerate = (preserveManual: boolean) => {
    const msg = preserveManual
      ? "セリフに基づく自動配置を再生成します（手動追加分は保持）。続行しますか？"
      : "香盤表を全てクリアして再生成します。続行しますか？";
    if (!window.confirm(msg)) return;
    regenerate.mutate(preserveManual);
  };

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-lg border p-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-3 flex-1 flex-wrap">
          <Legend type="dialogue" />
          <Legend type="silent" />
          <Legend type="off_stage" />
          <span className="text-xs text-gray-400">
            セルクリックで: セリフ → 登場 → 声のみ → 空
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleRegenerate(true)}
            disabled={regenerate.isPending}
            className="px-3 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100 disabled:opacity-50"
          >
            セリフから再生成
          </button>
          <button
            onClick={() => handleRegenerate(false)}
            disabled={regenerate.isPending}
            className="px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 disabled:opacity-50"
          >
            全消去して再生成
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-auto">
        <table className="text-xs border-collapse min-w-full">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              <th className="sticky left-0 z-20 bg-gray-50 border-b border-r px-3 py-2 text-left font-medium text-gray-600 min-w-[180px]">
                シーン
              </th>
              {data.characters.map((char) => (
                <th
                  key={char.id}
                  className="border-b border-r px-2 py-2 text-center font-medium text-gray-700 whitespace-nowrap"
                >
                  {char.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.scenes.map((scene) => (
              <tr key={scene.id} className="hover:bg-gray-50/50">
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-white border-b border-r px-3 py-2 text-left font-normal align-top"
                >
                  <div className="text-gray-400 font-mono text-[10px]">
                    {scene.act_number}-{scene.scene_number}
                  </div>
                  <div className="text-gray-800 truncate max-w-[240px]">
                    {scene.heading}
                  </div>
                </th>
                {data.characters.map((char) => {
                  const cell = data.matrix[scene.id]?.[char.id] ?? null;
                  const key = `${scene.id}:${char.id}`;
                  const busy = busyKey === key;
                  return (
                    <td
                      key={char.id}
                      className="border-b border-r p-0 text-center"
                    >
                      <button
                        type="button"
                        onClick={() => handleCycle(scene.id, char.id, cell)}
                        disabled={busy}
                        title={
                          cell
                            ? LABELS[cell.appearance_type as AppearanceType]
                                ?.label
                            : "空（クリックで配置）"
                        }
                        className={`w-full h-9 text-sm transition disabled:opacity-50 ${
                          cell
                            ? LABELS[cell.appearance_type as AppearanceType]
                                ?.cls
                            : "hover:bg-indigo-50"
                        } ${
                          cell && !cell.is_auto_generated
                            ? "ring-1 ring-inset ring-amber-400"
                            : ""
                        }`}
                      >
                        {cell
                          ? LABELS[cell.appearance_type as AppearanceType]
                              ?.symbol
                          : ""}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-400">
        <span className="inline-block w-3 h-3 ring-1 ring-inset ring-amber-400 align-middle mr-1" />
        手動で追加されたマッピング
      </p>
    </div>
  );
}

function Legend({ type }: { type: AppearanceType }) {
  const { symbol, label, cls } = LABELS[type];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-gray-600">
      <span
        className={`inline-flex items-center justify-center w-6 h-6 rounded ${cls}`}
      >
        {symbol}
      </span>
      {label}
    </span>
  );
}
