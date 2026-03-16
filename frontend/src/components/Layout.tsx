import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Wallet, TrendingUp, DollarSign, LogOut, LandPlot, FileText, Database, Menu, X as CloseIcon, Lock, BarChart3, Coins } from "lucide-react";
import api, { getCurrentUser } from "../lib/api";
import { useEffect } from "react";

import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

export default function Layout({ children }: { children: React.ReactNode }) {
    const location = useLocation();
    const [isBackingUp, setIsBackingUp] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        getCurrentUser().then(setUser).catch(console.error);
    }, []);

    const isGuest = user?.username === 'guest';


    const handleBackup = async () => {
        setIsBackingUp(true);
        try {
            // Fetch all data
            const [equity, mf, fd, otherAssets] = await Promise.all([
                api.get('/equity/'),
                api.get('/mutual-funds/'),
                api.get('/fixed-deposits/'),
                api.get('/other-assets/')
            ]);

            // Create workbook
            const wb = XLSX.utils.book_new();

            // Add sheets
            const equitySheet = XLSX.utils.json_to_sheet(equity.data);
            const mfSheet = XLSX.utils.json_to_sheet(mf.data);
            const fdSheet = XLSX.utils.json_to_sheet(fd.data);
            const otherSheet = XLSX.utils.json_to_sheet(otherAssets.data);

            XLSX.utils.book_append_sheet(wb, equitySheet, 'Equity');
            XLSX.utils.book_append_sheet(wb, mfSheet, 'Mutual Funds');
            XLSX.utils.book_append_sheet(wb, fdSheet, 'Fixed Deposits');
            XLSX.utils.book_append_sheet(wb, otherSheet, 'Other Assets');

            // Save file
            const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
            const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
            saveAs(blob, `Portfolio_Backup_${new Date().toISOString().split('T')[0]}.xlsx`);

            alert('Backup completed successfully!');
        } catch (err) {
            console.error('Backup failed:', err);
            alert('Backup failed. Please try again.');
        } finally {
            setIsBackingUp(false);
        }
    };

    const links = [
        { to: "/", icon: LayoutDashboard, label: "Dashboard" },
        {
            to: "/fixed-deposits",
            icon: Wallet,
            label: "Fixed Deposits",
            subItems: [
                { label: "All FDs", query: "" },
                { label: "By Bank", query: "group=bank" },
                { label: "By Depositor", query: "group=depositor" },
            ]
        },
        {
            to: "/equity",
            icon: TrendingUp,
            label: "My Portfolio",
            subItems: [
                { label: "Bought Shares", query: "status=ACTIVE" },
                { label: "Sold Shares", query: "status=SOLD" },
                { label: "By Holder", query: "group=holder" },
            ]
        },
        {
            to: "/mutual-funds",
            icon: DollarSign,
            label: "Mutual Funds",
            subItems: [
                { label: "Bought Funds", query: "status=ACTIVE" },
                { label: "Sold Funds", query: "status=SOLD" },
                { label: "By Depositor", query: "group=depositor" },
                { label: "By Holder", query: "group=holder" },
            ]
        },
        {
            to: "/bonds",
            icon: Lock,
            label: "Bonds",
            subItems: [
                { label: "All Bonds", query: "" },
                { label: "Gold Bonds", query: "type=gold" },
            ]
        },
        {
            to: "/liquidable-assets",
            icon: Coins,
            label: "Liquidable Assets",
            subItems: [
                { label: "Insurance", query: "cat=INSURANCE" },
                { label: "Retirement (PPF/EPF)", query: "cat=RETIREMENT" },
                { label: "Gold", query: "cat=GOLD" },
                { label: "Savings/Bonds", query: "cat=SAVINGS" },
            ]
        },
        {
            to: "/other-assets",
            icon: LandPlot,
            label: "Other Assets",
            subItems: [
                { label: "Real Estate", query: "cat=REAL_ESTATE" },
                { label: "Misc", query: "cat=MISC" },
            ]
        },
        {
            to: "/reports",
            icon: FileText,
            label: "Reports",
            subItems: [
                { label: "FD Tax Analysis", query: "tab=interest" },
                { label: "Portfolio Alerts", query: "tab=pnl" },
                { label: "Growth Simulation", query: "tab=projections" },
                { label: "Technical Signals", query: "tab=dma" },
            ]
        },
        {
            to: "/reconciliation",
            icon: FileText,
            label: "Reconciliation",
            subItems: [
                { label: "By Broker", query: "" },
                { label: "By AMC", query: "" },
            ]
        },
        {
            to: "/analytics",
            icon: BarChart3,
            label: "Analytics",
            subItems: [
                { label: "Dashboard", query: "" },
                { label: "Top Gainers", query: "" },
                { label: "Top Losers", query: "" },
            ]
        },
    ];

    const filteredLinks = links.filter(link => {
        if (!isGuest) return true;
        // Guest allowed paths: Dashboard, Equity, Mutual Funds
        return ['/', '/equity', '/mutual-funds', '/analytics'].includes(link.to);
    });


    return (
        <div className="flex h-screen bg-slate-50 overflow-hidden">
            {/* Mobile Header */}
            <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-slate-900 flex items-center justify-between px-6 z-40">
                <h1 className="text-xl font-bold text-white tracking-tight">HOMBA TRACKER</h1>
                <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="text-white p-2">
                    {isMobileMenuOpen ? <CloseIcon className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
            </header>

            {/* Sidebar Overlay */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-40 lg:hidden"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`fixed lg:static inset-y-0 left-0 w-64 bg-slate-900 text-slate-300 flex flex-col overflow-y-auto z-50 transition-transform duration-300 lg:translate-x-0 ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
                }`}>
                <div className="p-6 hidden lg:block">
                    <h1 className="text-xl font-bold text-white tracking-tight">HOMBA TRACKER</h1>
                </div>

                <nav className="flex-1 px-3 space-y-1 lg:mt-0 mt-20">
                    {filteredLinks.map((link) => {
                        const Icon = link.icon;

                        const active = location.pathname === link.to;
                        const hasSubItems = link.subItems && link.subItems.length > 0;

                        return (
                            <div key={link.to} className="space-y-1">
                                <Link
                                    to={link.to}
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${active ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20" : "hover:bg-slate-800 hover:text-white"
                                        }`}
                                >
                                    <Icon className="w-5 h-5 flex-shrink-0" />
                                    <span className="font-medium">{link.label}</span>
                                </Link>

                                {hasSubItems && (active || location.pathname.startsWith(link.to)) && (
                                    <div className="ml-9 border-l border-slate-800 space-y-1">
                                        {link.subItems?.map((sub) => {
                                            const isSubActive = sub.query
                                                ? location.search.includes(sub.query)
                                                : location.search === "" || location.search === "?";

                                            return (
                                                <Link
                                                    key={sub.label}
                                                    to={`${link.to}${sub.query ? `?${sub.query}` : ''}`}
                                                    onClick={() => setIsMobileMenuOpen(false)}
                                                    className={`block px-4 py-2 text-sm rounded-md transition-all ${isSubActive
                                                        ? "text-indigo-400 font-semibold"
                                                        : "hover:text-white"
                                                        }`}
                                                >
                                                    {sub.label}
                                                </Link>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </nav>

                <div className="p-4 mt-auto border-t border-slate-800 space-y-2">
                    {!isGuest && (
                        <button
                            onClick={handleBackup}
                            disabled={isBackingUp}
                            className="flex items-center gap-3 w-full px-4 py-3 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors disabled:opacity-50"
                        >
                            <Database className="w-5 h-5" />
                            <span className="font-medium">{isBackingUp ? 'Backing up...' : 'Backup Data'}</span>
                        </button>
                    )}

                    {!isGuest && (
                        <Link
                            to="/change-password"
                            onClick={() => setIsMobileMenuOpen(false)}
                            className="flex items-center gap-3 w-full px-4 py-3 text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors"
                        >
                            <Lock className="w-5 h-5" />
                            <span className="font-medium">Change Password</span>
                        </Link>
                    )}

                    <button
                        onClick={() => { localStorage.removeItem("token"); window.location.href = "/login"; }}
                        className="flex items-center gap-3 w-full px-4 py-3 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                        <LogOut className="w-5 h-5" />
                        <span className="font-medium">Logout</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto p-4 lg:p-8 mt-16 lg:mt-0">
                <div className="max-w-7xl mx-auto">
                    {children}
                </div>
            </main>
        </div>
    );
}
