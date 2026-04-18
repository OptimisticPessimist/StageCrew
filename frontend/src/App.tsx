import { Routes, Route } from "react-router-dom";
import DashboardPage from "@/features/dashboard/DashboardPage";
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
import HomePage from "@/features/home/HomePage";
import ScriptListPage from "@/features/scripts/ScriptListPage";
import ScriptDetailPage from "@/features/scripts/ScriptDetailPage";

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
          path="/organizations/:orgId/productions/:productionId/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
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
          path="/organizations/:orgId/productions/:productionId/scripts"
          element={
            <ProtectedRoute>
              <ScriptListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations/:orgId/productions/:productionId/scripts/:scriptId"
          element={
            <ProtectedRoute>
              <ScriptDetailPage />
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
