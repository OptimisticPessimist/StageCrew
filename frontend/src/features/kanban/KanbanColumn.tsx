import { Droppable } from "@hello-pangea/dnd";
import type { Issue, StatusDefinition } from "@/types";
import KanbanCard from "./KanbanCard";

interface Props {
  status: StatusDefinition | null;
  issues: Issue[];
  onCardClick: (issue: Issue) => void;
  onAddClick: (statusId: string | null) => void;
}

export default function KanbanColumn({
  status,
  issues,
  onCardClick,
  onAddClick,
}: Props) {
  const columnId = status?.id ?? "__uncategorized__";
  const columnName = status?.name ?? "未分類";
  const columnColor = status?.color ?? "#9ca3af";

  return (
    <div className="flex flex-col w-72 min-w-[18rem] bg-gray-50 rounded-lg shrink-0">
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full shrink-0"
            style={{ backgroundColor: columnColor }}
          />
          <h3 className="text-sm font-semibold text-gray-700 truncate">
            {columnName}
          </h3>
          <span className="text-xs text-gray-400 bg-gray-200 rounded-full px-1.5">
            {issues.length}
          </span>
        </div>
        <button
          onClick={() => onAddClick(status?.id ?? null)}
          className="text-gray-400 hover:text-indigo-600 text-lg leading-none px-1"
          title="課題を追加"
        >
          +
        </button>
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
