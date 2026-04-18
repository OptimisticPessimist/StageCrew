import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useScript, useReuploadScript } from "./hooks/useScripts";
import ScriptUploadModal from "./ScriptUploadModal";
import CharacterCastingEditor from "./CharacterCastingEditor";
import SceneChartView from "./SceneChartView";
import type { ScriptCharacter, ScriptScene } from "@/types";

type TabKey = "overview" | "characters" | "scenes" | "chart";

export default function ScriptDetailPage() {
  const { orgId, productionId, scriptId } = useParams<{
    orgId: string;
    productionId: string;
    scriptId: string;
  }>();

  const { data: script, isLoading, isError } = useScript(
    orgId!,
    productionId!,
    scriptId!,
  );
  const reupload = useReuploadScript(orgId!, productionId!, scriptId!);

  const [tab, setTab] = useState<TabKey>("overview");
  const [reuploadOpen, setReuploadOpen] = useState(false);

  const listPath = `/organizations/${orgId}/productions/${productionId}/scripts`;

  const characterNameMap = useMemo(() => {
    if (!script) return new Map<string, string>();
    return new Map(script.characters.map((c) => [c.id, c.name]));
  }, [script]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (isError || !script) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-3">
        <div className="text-gray-500">脚本を読み込めませんでした</div>
        <Link to={listPath} className="text-sm text-indigo-600 hover:underline">
          脚本一覧に戻る
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center gap-4">
        <Link
          to={listPath}
          className="text-gray-400 hover:text-gray-600 text-sm"
        >
          &larr; 脚本一覧
        </Link>
        <h1 className="text-lg font-bold text-gray-900 flex-1 truncate">
          {script.title}
        </h1>
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
          Rev {script.revision}
        </span>
        <button
          onClick={() => setReuploadOpen(true)}
          className="px-3 py-1.5 text-sm font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100"
        >
          再アップロード
        </button>
      </header>

      <main className="max-w-4xl mx-auto p-6 space-y-5">
        <nav className="flex items-center gap-1 border-b">
          <TabButton
            active={tab === "overview"}
            onClick={() => setTab("overview")}
          >
            概要
          </TabButton>
          <TabButton
            active={tab === "characters"}
            onClick={() => setTab("characters")}
          >
            登場人物 ({script.characters.length})
          </TabButton>
          <TabButton
            active={tab === "scenes"}
            onClick={() => setTab("scenes")}
          >
            シーン ({script.scenes.length})
          </TabButton>
          <TabButton
            active={tab === "chart"}
            onClick={() => setTab("chart")}
          >
            香盤表
          </TabButton>
        </nav>

        {tab === "overview" && <OverviewTab script={script} />}
        {tab === "characters" && (
          <CharactersTab
            characters={script.characters}
            orgId={orgId!}
            productionId={productionId!}
            scriptId={scriptId!}
          />
        )}
        {tab === "scenes" && (
          <ScenesTab
            scenes={script.scenes}
            characterNameMap={characterNameMap}
          />
        )}
        {tab === "chart" && (
          <SceneChartView
            orgId={orgId!}
            productionId={productionId!}
            scriptId={scriptId!}
          />
        )}
      </main>

      {reuploadOpen && (
        <ScriptUploadModal
          title="脚本を再アップロード（リビジョン更新）"
          submitLabel="再アップロード"
          showRevisionText
          onClose={() => setReuploadOpen(false)}
          onSubmit={({ file, revisionText }) =>
            reupload.mutateAsync({ file, revisionText })
          }
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
        active
          ? "border-indigo-600 text-indigo-700"
          : "border-transparent text-gray-500 hover:text-gray-800"
      }`}
    >
      {children}
    </button>
  );
}

function OverviewTab({
  script,
}: {
  script: {
    author: string | null;
    draft_date: string | null;
    revision: number;
    revision_text: string | null;
    copyright: string | null;
    contact: string | null;
    notes: string | null;
    synopsis: string | null;
    uploader: { display_name: string };
    uploaded_at: string;
  };
}) {
  const uploadedAt = new Date(script.uploaded_at).toLocaleString();
  const draftDate = script.draft_date
    ? new Date(script.draft_date).toLocaleDateString()
    : null;

  return (
    <div className="bg-white rounded-lg border p-5 space-y-4">
      <MetaGrid>
        <MetaItem label="作者" value={script.author} />
        <MetaItem label="初稿日" value={draftDate} />
        <MetaItem label="改訂番号" value={String(script.revision)} />
        <MetaItem label="著作権" value={script.copyright} />
        <MetaItem label="連絡先" value={script.contact} />
        <MetaItem
          label="最終アップロード"
          value={`${uploadedAt}（${script.uploader.display_name}）`}
        />
      </MetaGrid>

      {script.revision_text && (
        <Section title="改訂メモ">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {script.revision_text}
          </p>
        </Section>
      )}

      {script.synopsis && (
        <Section title="あらすじ">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {script.synopsis}
          </p>
        </Section>
      )}

      {script.notes && (
        <Section title="備考">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {script.notes}
          </p>
        </Section>
      )}
    </div>
  );
}

function CharactersTab({
  characters,
  orgId,
  productionId,
  scriptId,
}: {
  characters: ScriptCharacter[];
  orgId: string;
  productionId: string;
  scriptId: string;
}) {
  if (characters.length === 0) {
    return <EmptyState message="登場人物が登録されていません" />;
  }
  return (
    <div className="bg-white rounded-lg border divide-y">
      {characters.map((char) => (
        <CharacterRow
          key={char.id}
          char={char}
          orgId={orgId}
          productionId={productionId}
          scriptId={scriptId}
        />
      ))}
    </div>
  );
}

function CharacterRow({
  char,
  orgId,
  productionId,
  scriptId,
}: {
  char: ScriptCharacter;
  orgId: string;
  productionId: string;
  scriptId: string;
}) {
  const [editing, setEditing] = useState(false);

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-medium text-gray-900">{char.name}</span>
        {char.castings.length > 0 && (
          <span className="text-xs text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
            {char.castings.length}名配役済
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={() => setEditing(!editing)}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          {editing ? "閉じる" : "配役を編集"}
        </button>
      </div>
      {char.description && (
        <p className="mt-1 text-sm text-gray-600 whitespace-pre-wrap">
          {char.description}
        </p>
      )}
      {!editing && char.castings.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {char.castings.map((cast) => (
            <li
              key={cast.id}
              className="text-xs text-gray-500 flex items-center gap-2"
            >
              <span>&bull;</span>
              <span>{cast.display_name || "（表示名未設定）"}</span>
              {cast.memo && (
                <span className="text-gray-400">— {cast.memo}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {editing && (
        <CharacterCastingEditor
          character={char}
          orgId={orgId}
          productionId={productionId}
          scriptId={scriptId}
        />
      )}
    </div>
  );
}

function ScenesTab({
  scenes,
  characterNameMap,
}: {
  scenes: ScriptScene[];
  characterNameMap: Map<string, string>;
}) {
  if (scenes.length === 0) {
    return <EmptyState message="シーンが登録されていません" />;
  }
  return (
    <div className="space-y-3">
      {scenes.map((scene) => (
        <SceneBlock
          key={scene.id}
          scene={scene}
          characterNameMap={characterNameMap}
        />
      ))}
    </div>
  );
}

function SceneBlock({
  scene,
  characterNameMap,
}: {
  scene: ScriptScene;
  characterNameMap: Map<string, string>;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div className="bg-white rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full p-4 flex items-center gap-3 text-left hover:bg-gray-50"
      >
        <span className="text-xs text-gray-400 font-mono shrink-0">
          {scene.act_number}-{scene.scene_number}
        </span>
        <span className="font-medium text-gray-900 flex-1 truncate">
          {scene.heading}
        </span>
        <span className="text-xs text-gray-400">{scene.lines.length}行</span>
        <span className="text-gray-400 text-sm">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="border-t px-4 py-3 bg-gray-50/60 space-y-2">
          {scene.description && (
            <p className="text-sm text-gray-500 whitespace-pre-wrap italic">
              {scene.description}
            </p>
          )}
          {scene.lines.length === 0 ? (
            <p className="text-xs text-gray-400">セリフなし</p>
          ) : (
            <ul className="space-y-1.5">
              {scene.lines.map((line) => {
                const name = line.character_id
                  ? characterNameMap.get(line.character_id)
                  : null;
                return (
                  <li key={line.id} className="text-sm text-gray-800 flex gap-3">
                    <span className="shrink-0 w-24 font-medium text-gray-600 truncate">
                      {name || (line.character_id ? "?" : "")}
                    </span>
                    <span className="flex-1 whitespace-pre-wrap">
                      {line.content}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function MetaGrid({ children }: { children: React.ReactNode }) {
  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
      {children}
    </dl>
  );
}

function MetaItem({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs text-gray-500">{label}</dt>
      <dd className="text-sm text-gray-800">{value}</dd>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="pt-3 border-t">
      <h3 className="text-xs font-medium text-gray-500 uppercase mb-1">
        {title}
      </h3>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-white rounded-lg border p-12 text-center text-gray-500 text-sm">
      {message}
    </div>
  );
}
