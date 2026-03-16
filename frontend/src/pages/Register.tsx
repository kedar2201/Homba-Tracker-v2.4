import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ShieldCheck, User, Mail, Lock, Loader2, ArrowRight } from "lucide-react";
import api from "../lib/api";

export default function Register() {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const navigate = useNavigate();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            await api.post("/auth/register", { username, email, password });
            // After successful registration, redirect to login
            navigate("/login", { state: { message: "Account created successfully! Please login." } });
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "Registration failed. Username might already exist.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-100 rounded-full blur-[120px] opacity-50"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-100 rounded-full blur-[120px] opacity-50"></div>
            </div>

            <div className="bg-white w-full max-w-md rounded-[2.5rem] shadow-2xl p-10 z-10 border border-slate-100 relative">
                <div className="flex flex-col items-center mb-10 text-center">
                    <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-indigo-100 mb-6 rotate-3 hover:rotate-0 transition-transform duration-300">
                        <ShieldCheck className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-900 uppercase tracking-tight">Create Account</h1>
                    <p className="text-slate-500 mt-2 font-medium">Start your fresh financial engine.</p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-100 text-red-600 text-sm font-bold rounded-2xl animate-in fade-in duration-300">
                        {error}
                    </div>
                )}

                <form onSubmit={handleRegister} className="space-y-5">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Username</label>
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-indigo-600 transition-colors">
                                <User className="w-4 h-4" />
                            </div>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full pl-12 pr-6 py-4 bg-slate-50 border-transparent border-2 focus:border-indigo-600 focus:bg-white rounded-2xl outline-none font-bold text-slate-700 transition-all"
                                placeholder="Choose a username"
                                required
                                autoCapitalize="none"
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Email Address</label>
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-indigo-600 transition-colors">
                                <Mail className="w-4 h-4" />
                            </div>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full pl-12 pr-6 py-4 bg-slate-50 border-transparent border-2 focus:border-indigo-600 focus:bg-white rounded-2xl outline-none font-bold text-slate-700 transition-all"
                                placeholder="name@example.com"
                                required
                                autoCapitalize="none"
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Password</label>
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-indigo-600 transition-colors">
                                <Lock className="w-4 h-4" />
                            </div>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full pl-12 pr-6 py-4 bg-slate-50 border-transparent border-2 focus:border-indigo-600 focus:bg-white rounded-2xl outline-none font-bold text-slate-700 transition-all"
                                placeholder="••••••••"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-slate-900 text-white py-5 rounded-2xl font-black uppercase tracking-widest text-sm shadow-xl shadow-slate-200 hover:bg-slate-800 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:scale-100 flex items-center justify-center gap-2 group"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                            <>
                                Initialize New Identity
                                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </button>

                    <div className="pt-4 text-center">
                        <p className="text-slate-500 text-sm font-medium">
                            Already have testing data? {" "}
                            <Link to="/login" className="text-indigo-600 font-black uppercase tracking-tighter hover:underline">Sign In Instead</Link>
                        </p>
                    </div>
                </form>
            </div>

            <div className="absolute bottom-8 text-slate-400 text-xs font-bold uppercase tracking-[0.2em]">
                Secure Financial Infrastructure v2.0
            </div>
        </div>
    );
}
