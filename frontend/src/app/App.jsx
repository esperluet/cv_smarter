import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "../components/ProtectedRoute";
import AuthPage from "../features/auth/AuthPage";
import WorkspacePage from "../features/account/WorkspacePage";
import { useAuth } from "../features/auth/AuthContext";

function HomeRedirect() {
  const { isAuthenticated, isReady } = useAuth();

  if (!isReady) {
    return <div className="loading-screen">Loading...</div>;
  }

  return <Navigate to={isAuthenticated ? "/app" : "/auth"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <WorkspacePage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
