import { useState, type ChangeEvent } from "react";
import { useParams, Link } from "react-router-dom";
import { useScriptDetail, useReuploadScript, useScriptPdfUrl } from "./hooks/useScripts";
import { useCastings, useCreateCasting, useDeleteCasting } from "./hooks/useCastings";
import { useSceneChart, useGenerateSceneChart } from "./hooks/useSceneChart";
import { useProductionMembers } from "@/features/members/hooks/useProductionMembers";
import CountdownBadge from "@/features/production/CountdownBadge";
import type { ScriptCharacter, ScriptDetail, SceneChart } from "@/types";

type TabKey = "scenes" | "characters" | "casting" | "scene-chart";

export default function ScriptDetailPage() {
  const { orgId, productionId, scriptId } = useParams<{
    orgId: string;
    productionId: string;
    scriptId: string;
  }>();

  const [activeTab, setActiveTab] = useState<TabKey>("scenes");

  const { data: script, isLoading } = useScriptDetail(orgId!, productionId!, scriptId!);
  const reupload = useReuploadScript(orgId!, productionId!);
  const pdfUrl = useScriptPdfUrl(orgId!, productionId!, scriptId!);

  const scriptsPath = `/organizations/${orgId}/productions/${productionId}/scripts`;

  const handleReupload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    reupload.mutate({ scriptId: scriptId!, file });
    e.target.value = "";
  };

  if (isLoading || !script) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center text-gray-500">
        読み込み中...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to={scriptsPath} className="text-gray-400 hover:text-gray-600 text-sm">
            &larr; 脚本一覧
          </Link>
          <h1 className="text-lg font-bold text-gray-900 truncate max-w-xs">
            {script.title}
          </h1>
          {script.author && (
            <span className="text-sm text-gray-500">作: {script.author}</span>
          )}
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
            第{script.revision}稿
          </span>
          <CountdownBadge orgId={orgId!} productionId={productionId!} />
        </div>
        <div className="flex items-center gap-2">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-gray-600 hover:text-gray-800 border border-gray-300 px-3 py-1.5 rounded"
          >
            PDFダウンロード
          </a>
          <label className="cursor-pointer text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 px-3 py-1.5 rounded">
            再アップロード
            <input
              type="file"
              accept=".txt,.fountain"
              className="hidden"
              onChange={handleReupload}
            />
          </label>
        </div>
      </header>

      {/* メタ情報 */}
      {(script.synopsis || script.notes) && (
        <div className="bg-white border-b px-6 py-3">
          {script.synopsis && (
            <p className="text-sm text-gray-700">
              <span className="font-medium">あらすじ: </span>
              {script.synopsis}
            </p>
          )}
          {script.notes && (
            <p className="text-sm text-gray-500 mt-1">{script.notes}</p>
          )}
        </div>
      )}

      {/* タブ */}
      <div className="bg-white border-b px-6 flex gap-0">
        {(
          [
            ["scenes", "シーン"],
            ["characters", "登場人物"],
            ["casting", "配役"],
            ["scene-chart", "香盤表"],
          ] as [TabKey, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2.5 text-sm border-b-2 -mb-px transition-colors ${
              activeTab === key
                ? "border-indigo-600 text-indigo-600 font-medium"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
            {key === "scenes" && (
              <span className="ml-1 text-xs text-gray-400">
                ({script.scenes.length})
              </span>
            )}
            {key === "characters" && (
              <span className="ml-1 text-xs text-gray-400">
                ({script.characters.length})
              </span>
            )}
          </button>
        ))}
      </div>

      <main className="flex-1 overflow-auto p-6">
        {activeTab === "scenes" && <ScenesTab scenes={script.scenes} />}
        {activeTab === "characters" && <CharactersTab characters={script.characters} />}
        {activeTab === "casting" && (
          <CastingTab orgId={orgId!} productionId={productionId!} scriptId={scriptId!} characters={script.characters} />
        )}
        {activeTab === "scene-chart" && (
          <SceneChartTab orgId={orgId!} productionId={productionId!} scriptId={scriptId!} />
        )}
      </main>
    </div>
  );
}

// ---- シーンタブ ----
function ScenesTab({ scenes }: { scenes: ScriptDetail["scenes"] }) {

  if (scenes.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        シーンがありません
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {scenes.map((scene) => (
        <div key={scene.id} className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900 mb-1">
            第{scene.act_number}幕 第{scene.scene_number}場: {scene.heading}
          </h3>
          {scene.description && (
            <p className="text-sm text-gray-500 mb-3">{scene.description}</p>
          )}
          {scene.lines.length > 0 && (
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {scene.lines.map((line) => (
                <p key={line.id} className="text-sm text-gray-700 leading-relaxed">
                  {line.content}
                </p>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-400 mt-2">{scene.lines.length} セリフ</p>
        </div>
      ))}
    </div>
  );
}

// ---- 登場人物タブ ----
function CharactersTab({ characters }: { characters: ScriptCharacter[] }) {
  if (characters.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        登場人物がありません
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {characters.map((char) => (
        <div key={char.id} className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900">{char.name}</h3>
          {char.description && (
            <p className="text-sm text-gray-500 mt-1">{char.description}</p>
          )}
          {char.castings.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <p className="text-xs text-gray-400 mb-1">配役</p>
              {char.castings.map((c) => (
                <p key={c.id} className="text-sm text-gray-700">
                  {c.display_name ?? "(名前未設定)"}
                  {c.memo && <span className="text-gray-400 ml-1">({c.memo})</span>}
                </p>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---- 配役タブ ----
function CastingTab({
  orgId,
  productionId,
  scriptId,
  characters,
}: {
  orgId: string;
  productionId: string;
  scriptId: string;
  characters: ScriptCharacter[];
}) {
  const { data: castings = [], isLoading } = useCastings(orgId, productionId, scriptId);
  const { data: members = [] } = useProductionMembers(orgId, productionId);
  const createCasting = useCreateCasting(orgId, productionId, scriptId);
  const deleteCasting = useDeleteCasting(orgId, productionId, scriptId);

  const [form, setForm] = useState({
    character_id: "",
    production_membership_id: "",
    display_name: "",
    memo: "",
  });
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreate = () => {
    if (!form.character_id || !form.production_membership_id) {
      setFormError("登場人物とメンバーを選択してください");
      return;
    }
    setFormError(null);
    createCasting.mutate(
      {
        character_id: form.character_id,
        production_membership_id: form.production_membership_id,
        display_name: form.display_name || null,
        memo: form.memo || null,
      },
      {
        onError: (err) =>
          setFormError(err instanceof Error ? err.message : "追加に失敗しました"),
        onSuccess: () =>
          setForm({ character_id: "", production_membership_id: "", display_name: "", memo: "" }),
      },
    );
  };

  if (isLoading) {
    return <div className="text-center py-12 text-gray-500">読み込み中...</div>;
  }

  return (
    <div className="space-y-6">
      {/* 追加フォーム */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="font-medium text-gray-900 mb-3">配役を追加</h3>
        {formError && (
          <p className="text-sm text-red-600 mb-2">{formError}</p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <select
            value={form.character_id}
            onChange={(e) => setForm((f) => ({ ...f, character_id: e.target.value }))}
            className="border border-gray-300 rounded px-3 py-2 text-sm"
          >
            <option value="">登場人物を選択</option>
            {characters.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            value={form.production_membership_id}
            onChange={(e) =>
              setForm((f) => ({ ...f, production_membership_id: e.target.value }))
            }
            className="border border-gray-300 rounded px-3 py-2 text-sm"
          >
            <option value="">メンバーを選択</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="表示名（任意）"
            value={form.display_name}
            onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
            className="border border-gray-300 rounded px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="メモ（任意）"
            value={form.memo}
            onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))}
            className="border border-gray-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={handleCreate}
          disabled={createCasting.isPending}
          className="mt-3 bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          追加
        </button>
      </div>

      {/* 配役一覧 */}
      {castings.length === 0 ? (
        <div className="text-center py-8 text-gray-400">配役がありません</div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-2 text-gray-600 font-medium">登場人物</th>
                <th className="text-left px-4 py-2 text-gray-600 font-medium">キャスト</th>
                <th className="text-left px-4 py-2 text-gray-600 font-medium">表示名</th>
                <th className="text-left px-4 py-2 text-gray-600 font-medium">メモ</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {castings.map((casting) => (
                <tr key={casting.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">{casting.character.name}</td>
                  <td className="px-4 py-2">
                    {casting.production_membership.user.display_name}
                  </td>
                  <td className="px-4 py-2 text-gray-500">
                    {casting.display_name ?? "-"}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{casting.memo ?? "-"}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => deleteCasting.mutate(casting.id)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      削除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---- 香盤表タブ ----
const APPEARANCE_LABELS: Record<string, string> = {
  dialogue: "台詞",
  silent: "出演",
  off_stage: "声のみ",
};

const APPEARANCE_COLORS: Record<string, string> = {
  dialogue: "bg-indigo-100 text-indigo-700",
  silent: "bg-green-100 text-green-700",
  off_stage: "bg-yellow-100 text-yellow-700",
};

function SceneChartTab({
  orgId,
  productionId,
  scriptId,
}: {
  orgId: string;
  productionId: string;
  scriptId: string;
}) {
  const { data: chart, isLoading } = useSceneChart(orgId, productionId, scriptId);
  const generate = useGenerateSceneChart(orgId, productionId, scriptId);

  if (isLoading) {
    return <div className="text-center py-12 text-gray-500">読み込み中...</div>;
  }

  if (!chart || (chart.scenes.length === 0 && chart.characters.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <p className="mb-4">香盤表データがありません</p>
        <button
          onClick={() => generate.mutate(true)}
          disabled={generate.isPending}
          className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          セリフデータから自動生成
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-4 text-xs text-gray-500">
          {Object.entries(APPEARANCE_LABELS).map(([key, label]) => (
            <span key={key} className={`px-2 py-0.5 rounded ${APPEARANCE_COLORS[key]}`}>
              {label}
            </span>
          ))}
        </div>
        <button
          onClick={() => generate.mutate(true)}
          disabled={generate.isPending}
          className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 px-3 py-1.5 rounded disabled:opacity-50"
        >
          {generate.isPending ? "生成中..." : "再生成"}
        </button>
      </div>

      <SceneChartMatrix chart={chart} />
    </div>
  );
}

function SceneChartMatrix({ chart }: { chart: SceneChart }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="sticky left-0 bg-gray-50 border border-gray-200 px-3 py-2 text-left text-gray-600 font-medium min-w-36 z-10">
              シーン / 登場人物
            </th>
            {chart.characters.map((char) => (
              <th
                key={char.id}
                className="border border-gray-200 px-2 py-2 text-center text-gray-600 font-medium min-w-16 max-w-24"
              >
                <span className="block truncate" title={char.name}>
                  {char.name}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {chart.scenes.map((scene) => {
            const row = chart.matrix[scene.id] ?? {};
            return (
              <tr key={scene.id} className="hover:bg-gray-50">
                <td className="sticky left-0 bg-white border border-gray-200 px-3 py-2 text-gray-700 font-medium z-10">
                  <span className="block text-gray-400 text-xs">
                    {scene.act_number}-{scene.scene_number}
                  </span>
                  <span className="block truncate max-w-32" title={scene.heading}>
                    {scene.heading}
                  </span>
                </td>
                {chart.characters.map((char) => {
                  const cell = row[char.id];
                  return (
                    <td
                      key={char.id}
                      className="border border-gray-200 px-2 py-2 text-center"
                    >
                      {cell ? (
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-xs ${
                            APPEARANCE_COLORS[cell.appearance_type] ??
                            "bg-gray-100 text-gray-600"
                          }`}
                          title={cell.note ?? undefined}
                        >
                          {APPEARANCE_LABELS[cell.appearance_type] ?? cell.appearance_type}
                        </span>
                      ) : (
                        <span className="text-gray-200">-</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
