import { Routes, Route } from "react-router-dom";
import KanbanPage from "@/features/kanban/KanbanPage";
import DepartmentsPage from "@/features/departments/DepartmentsPage";
import OrgMembersPage from "@/features/members/OrgMembersPage";
import ProductionMembersPage from "@/features/members/ProductionMembersPage";
import InvitationAcceptPage from "@/features/members/InvitationAcceptPage";

function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">StageCrew</h1>
        <p className="text-lg text-gray-600">
          演劇団体向けタスク管理SaaS
        </p>
        <p className="text-sm text-gray-400 mt-2">
          リアル演劇 / VR演劇 対応
        </p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/organizations/:orgId/productions/:productionId/board"
        element={<KanbanPage />}
      />
      <Route
        path="/organizations/:orgId/productions/:productionId/departments"
        element={<DepartmentsPage />}
      />
      <Route
        path="/organizations/:orgId/members"
        element={<OrgMembersPage />}
      />
      <Route
        path="/organizations/:orgId/productions/:productionId/members"
        element={<ProductionMembersPage />}
      />
      <Route
        path="/invitations/:token"
        element={<InvitationAcceptPage />}
      />
    </Routes>
  );
}
