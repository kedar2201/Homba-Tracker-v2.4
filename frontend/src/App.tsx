import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import FixedDeposits from "./pages/FixedDeposits";
import FDUpload from "./pages/FDUpload";
import EquityPage from "./pages/Equity";
import EquityUpload from "./pages/EquityUpload";
import MutualFundsPage from "./pages/MutualFunds";
import MutualFundUpload from "./pages/MutualFundUpload";
import BondsPage from "./pages/Bonds";
import OtherAssetsPage from "./pages/OtherAssets";
import ReportsPage from "./pages/Reports";
import ReconciliationReport from "./pages/ReconciliationReport";
import Analytics from "./pages/Analytics";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ChangePassword from "./pages/ChangePassword";

function App() {
  const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    const token = localStorage.getItem("token");
    if (!token) return <Navigate to="/login" />;
    return <Layout>{children}</Layout>;
  };

  return (
    <Router>
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
    </Router>
  );
}

export default App;
