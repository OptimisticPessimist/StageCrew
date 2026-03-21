import { DragDropContext, type DropResult } from "@hello-pangea/dnd";
import type { Issue, StatusDefinition } from "@/types";
import KanbanColumn from "./KanbanColumn";

interface Props {
  statuses: StatusDefinition[];
  issues: Issue[];
  onMoveIssue: (issueId: string, newStatusId: string | null) => void;
  onCardClick: (issue: Issue) => void;
  onAddClick: (statusId: string | null) => void;
}

const UNCATEGORIZED_ID = "__uncategorized__";

export default function KanbanBoard({
  statuses,
  issues,
  onMoveIssue,
  onCardClick,
  onAddClick,
}: Props) {
  const issuesByStatus = new Map<string, Issue[]>();

  issuesByStatus.set(UNCATEGORIZED_ID, []);
  for (const s of statuses) {
    issuesByStatus.set(s.id, []);
  }

  for (const issue of issues) {
    const key = issue.status_id ?? UNCATEGORIZED_ID;
    const list = issuesByStatus.get(key);
    if (list) {
      list.push(issue);
    } else {
      issuesByStatus.get(UNCATEGORIZED_ID)!.push(issue);
    }
  }

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return;

    const sourceId = result.source.droppableId;
    const destId = result.destination.droppableId;

    if (sourceId === destId && result.source.index === result.destination.index) {
      return;
    }

    const newStatusId = destId === UNCATEGORIZED_ID ? null : destId;
    onMoveIssue(result.draggableId, newStatusId);
  };

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4 h-full">
        {/* 未分類カラム */}
        {(issuesByStatus.get(UNCATEGORIZED_ID)?.length ?? 0) > 0 && (
          <KanbanColumn
            status={null}
            issues={issuesByStatus.get(UNCATEGORIZED_ID) ?? []}
            onCardClick={onCardClick}
            onAddClick={onAddClick}
          />
        )}

        {/* ステータスカラム */}
        {statuses.map((status) => (
          <KanbanColumn
            key={status.id}
            status={status}
            issues={issuesByStatus.get(status.id) ?? []}
            onCardClick={onCardClick}
            onAddClick={onAddClick}
          />
        ))}
      </div>
    </DragDropContext>
  );
}
