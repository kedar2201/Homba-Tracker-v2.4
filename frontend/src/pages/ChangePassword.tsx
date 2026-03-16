import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, Loader2, ArrowLeft } from "lucide-react";
import api from "../lib/api";

export default function ChangePassword() {
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");

        if (newPassword !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        setLoading(true);
        try {
            await api.post("/change-password", {
                current_password: currentPassword,
                new_password: newPassword
            });
            setSuccess("Password updated successfully!");
            setTimeout(() => navigate("/"), 2000);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "Failed to update password. Current password may be incorrect.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden">
            <div className="bg-white w-full max-w-md rounded-[2.5rem] shadow-2xl p-10 z-10 border border-slate-100">
                <button onClick={() => navigate(-1)} className="mb-6 flex items-center gap-2 text-slate-400 hover:text-indigo-600 transition-colors font-bold uppercase text-[10px] tracking-widest">
                    <ArrowLeft className="w-4 h-4" /> Go Back
                </button>

                <div className="flex flex-col items-center mb-10 text-center">
                    <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center text-white shadow-xl mb-6">
                        <Lock className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-900 uppercase tracking-tight">Security Update</h1>
                    <p className="text-slate-500 mt-2 font-medium text-sm">Update your access credentials.</p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-100 text-red-600 text-sm font-bold rounded-2xl">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="mb-6 p-4 bg-emerald-50 border border-emerald-100 text-emerald-600 text-sm font-bold rounded-2xl">
                        {success}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Current Password</label>
                        <input
                            type="password"
                            required
                            className="w-full px-6 py-4 bg-slate-50 border-transparent border-2 focus:border-indigo-600 focus:bg-white rounded-2xl outline-none font-bold text-slate-700 transition-all"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">New Password</label>
                        <input
                            type="password"
                            required
                            className="w-full px-6 py-4 bg-slate-50 border-transparent border-2 focus:border-indigo-600 focus:bg-white rounded-2xl outline-none font-bold text-slate-700 transition-all"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Confirm New Password</label>
                        <input
                            type="password"
                            required
                            className="w-full px-6 py-4 bg-slate-50 border-transparent border-2 focus:border-indigo-600 focus:bg-white rounded-2xl outline-none font-bold text-slate-700 transition-all"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-indigo-600 text-white py-5 rounded-2xl font-black uppercase tracking-widest text-sm shadow-xl shadow-indigo-100 hover:bg-indigo-700 hover:scale-[1.02] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Update Password"}
                    </button>
                </form>
            </div>
        </div>
    );
}
