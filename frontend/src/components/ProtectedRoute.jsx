import { Navigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthContext";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isReady } = useAuth();

  if (!isReady) {
    return <div className="loading-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}
