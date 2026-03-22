import { useState } from "react";
import { Droppable } from "@hello-pangea/dnd";
import type { Issue, StatusDefinition, StatusUpdate } from "@/types";
import KanbanCard from "./KanbanCard";

interface Props {
  status: StatusDefinition | null;
  issues: Issue[];
  onCardClick: (issue: Issue) => void;
  onAddClick: (statusId: string | null) => void;
  onUpdateStatus?: (statusId: string, body: StatusUpdate) => void;
  onDeleteStatus?: (statusId: string) => void;
}

export default function KanbanColumn({
  status,
  issues,
  onCardClick,
  onAddClick,
  onUpdateStatus,
  onDeleteStatus,
}: Props) {
  const columnId = status?.id ?? "__uncategorized__";
  const columnName = status?.name ?? "未分類";
  const columnColor = status?.color ?? "#9ca3af";

  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(columnName);
  const [editColor, setEditColor] = useState(columnColor);
  const [editIsClosed, setEditIsClosed] = useState(
    status?.is_closed ?? false,
  );
  const [showMenu, setShowMenu] = useState(false);

  const handleSave = () => {
    if (!status || !onUpdateStatus || !editName.trim()) return;
    onUpdateStatus(status.id, {
      name: editName.trim(),
      color: editColor,
      is_closed: editIsClosed,
    });
    setEditing(false);
  };

  const handleDelete = () => {
    if (!status || !onDeleteStatus) return;
    if (issues.length > 0) {
      alert(
        "このステータスにはまだ課題があります。課題を移動してから削除してください。",
      );
      return;
    }
    onDeleteStatus(status.id);
    setShowMenu(false);
  };

  return (
    <div className="flex flex-col w-72 min-w-[18rem] bg-gray-50 rounded-lg shrink-0">
      <div className="flex items-center justify-between px-3 py-2 border-b">
        {editing && status ? (
          <div className="flex items-center gap-1.5 flex-1 min-w-0">
            <input
              type="color"
              value={editColor}
              onChange={(e) => setEditColor(e.target.value)}
              className="w-6 h-6 rounded cursor-pointer shrink-0 border-0 p-0"
            />
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") setEditing(false);
              }}
              className="flex-1 min-w-0 rounded border border-gray-300 px-1.5 py-0.5 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              autoFocus
            />
            <label className="flex items-center gap-0.5 text-xs text-gray-500 cursor-pointer whitespace-nowrap shrink-0">
              <input
                type="checkbox"
                checked={editIsClosed}
                onChange={(e) => setEditIsClosed(e.target.checked)}
                className="rounded border-gray-300 text-green-600 focus:ring-green-500"
              />
              完了
            </label>
            <button
              onClick={handleSave}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium shrink-0"
            >
              保存
            </button>
            <button
              onClick={() => setEditing(false)}
              className="text-xs text-gray-400 hover:text-gray-600 shrink-0"
            >
              ✕
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: columnColor }}
              />
              <h3 className="text-sm font-semibold text-gray-700 truncate">
                {columnName}
              </h3>
              {status?.is_closed && (
                <span
                  className="text-xs text-green-600"
                  title="完了ステータス"
                >
                  ✓
                </span>
              )}
              <span className="text-xs text-gray-400 bg-gray-200 rounded-full px-1.5">
                {issues.length}
              </span>
            </div>
            <div className="flex items-center gap-0.5 shrink-0">
              {status && (
                <div className="relative">
                  <button
                    onClick={() => setShowMenu(!showMenu)}
                    className="text-gray-300 hover:text-gray-500 text-sm px-1"
                    title="ステータスを編集"
                  >
                    ⋯
                  </button>
                  {showMenu && (
                    <>
                      <div
                        className="fixed inset-0 z-10"
                        onClick={() => setShowMenu(false)}
                      />
                      <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[120px]">
                        <button
                          onClick={() => {
                            setEditName(status.name);
                            setEditColor(status.color ?? "#9ca3af");
                            setEditIsClosed(status.is_closed);
                            setEditing(true);
                            setShowMenu(false);
                          }}
                          className="w-full text-left px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                        >
                          編集
                        </button>
                        <button
                          onClick={handleDelete}
                          className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
                        >
                          削除
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
              <button
                onClick={() => onAddClick(status?.id ?? null)}
                className="text-gray-400 hover:text-indigo-600 text-lg leading-none px-1"
                title="課題を追加"
              >
                +
              </button>
            </div>
          </>
        )}
      </div>

      <Droppable droppableId={columnId}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`flex-1 overflow-y-auto p-2 min-h-[120px] transition-colors ${
              snapshot.isDraggingOver ? "bg-indigo-50" : ""
            }`}
          >
            {issues.map((issue, index) => (
              <KanbanCard
                key={issue.id}
                issue={issue}
                index={index}
                isClosed={status?.is_closed ?? false}
                onClick={onCardClick}
              />
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </div>
  );
}
