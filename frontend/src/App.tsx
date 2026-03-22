import { Routes, Route } from "react-router-dom";
import KanbanPage from "@/features/kanban/KanbanPage";
import GanttPage from "@/features/gantt/GanttPage";
import DepartmentsPage from "@/features/departments/DepartmentsPage";
import OrgMembersPage from "@/features/members/OrgMembersPage";
import ProductionMembersPage from "@/features/members/ProductionMembersPage";
import InvitationAcceptPage from "@/features/members/InvitationAcceptPage";
import AuthProvider from "@/features/auth/AuthProvider";
import LoginPage from "@/features/auth/LoginPage";
import AuthCallbackPage from "@/features/auth/AuthCallbackPage";
import ProtectedRoute from "@/features/auth/ProtectedRoute";

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
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/invitations/:token" element={<InvitationAcceptPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations/:orgId/productions/:productionId/board"
          element={
            <ProtectedRoute>
              <KanbanPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations/:orgId/productions/:productionId/gantt"
          element={
            <ProtectedRoute>
              <GanttPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations/:orgId/productions/:productionId/departments"
          element={
            <ProtectedRoute>
              <DepartmentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations/:orgId/members"
          element={
            <ProtectedRoute>
              <OrgMembersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations/:orgId/productions/:productionId/members"
          element={
            <ProtectedRoute>
              <ProductionMembersPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
