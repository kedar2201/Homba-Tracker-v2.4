import React, { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";

// Lazy load components
const Dashboard = lazy(() => import("./pages/Dashboard"));
const FixedDeposits = lazy(() => import("./pages/FixedDeposits"));
const FDUpload = lazy(() => import("./pages/FDUpload"));
const EquityPage = lazy(() => import("./pages/Equity"));
const EquityUpload = lazy(() => import("./pages/EquityUpload"));
const MutualFundsPage = lazy(() => import("./pages/MutualFunds"));
const MutualFundUpload = lazy(() => import("./pages/MutualFundUpload"));
const BondsPage = lazy(() => import("./pages/Bonds"));
const OtherAssetsPage = lazy(() => import("./pages/OtherAssets"));
const ReportsPage = lazy(() => import("./pages/Reports"));
const ReconciliationReport = lazy(() => import("./pages/ReconciliationReport"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const ChangePassword = lazy(() => import("./pages/ChangePassword"));

// Loading fallback component
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50/50 dark:bg-gray-900/50 backdrop-blur-sm">
    <div className="relative">
      <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-900 rounded-full animate-spin border-t-blue-600"></div>
    </div>
  </div>
);

// Protected Route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" />;
  return <Layout>{children}</Layout>;
};

function App() {

  return (
    <ErrorBoundary>
      <Router>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/fixed-deposits" element={<ProtectedRoute><FixedDeposits /></ProtectedRoute>} />
            <Route path="/fixed-deposits/upload" element={<ProtectedRoute><FDUpload /></ProtectedRoute>} />
            <Route path="/equity" element={<ProtectedRoute><EquityPage /></ProtectedRoute>} />
            <Route path="/equity/upload" element={<ProtectedRoute><EquityUpload /></ProtectedRoute>} />
            <Route path="/mutual-funds" element={<ProtectedRoute><MutualFundsPage /></ProtectedRoute>} />
            <Route path="/mutual-funds/upload" element={<ProtectedRoute><MutualFundUpload /></ProtectedRoute>} />
            <Route path="/bonds" element={<ProtectedRoute><BondsPage /></ProtectedRoute>} />
            <Route path="/other-assets" element={<ProtectedRoute><OtherAssetsPage /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
            <Route path="/reconciliation" element={<ProtectedRoute><ReconciliationReport /></ProtectedRoute>} />
            <Route path="/liquidable-assets" element={<ProtectedRoute><OtherAssetsPage /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
            <Route path="/change-password" element={<ProtectedRoute><ChangePassword /></ProtectedRoute>} />
          </Routes>
        </Suspense>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
