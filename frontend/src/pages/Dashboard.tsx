import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts";
import { Loader2, TrendingUp, Wallet, DollarSign, LandPlot, Download, Lock, Coins, Star } from "lucide-react";
import api from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const d = new Date(label);
        const dateStr = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });

        return (
            <div className="bg-white/95 backdrop-blur-sm p-6 rounded-[2rem] border border-slate-100 shadow-2xl shadow-slate-200 min-w-[280px] animate-in fade-in zoom-in duration-200">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-3">{dateStr}</p>

                <div className="space-y-4">
                    {payload.map((entry: any, index: number) => {
                        const isPortfolio = entry.dataKey === "portfolio";
                        const isSensex = entry.dataKey === "sensex";
                        const actual = isPortfolio ? entry.payload.portfolio_actual : (isSensex ? entry.payload.sensex_actual : entry.payload.nifty_actual);
                        const nav = isPortfolio ? entry.payload.portfolio_nav : null;

                        let labelText = isPortfolio ? "My Portfolio" : (isSensex ? "Sensex" : "Nifty 50");
                        let colorClass = isPortfolio ? "text-emerald-600" : (isSensex ? "text-amber-500" : "text-blue-500");

                        return (
                            <div key={index} className="flex flex-col gap-1.5 p-3 rounded-2xl bg-slate-50/50 border border-slate-100/50">
                                <div className="flex items-center justify-between">
                                    <span className={`text-[10px] font-bold uppercase tracking-wide ${colorClass}`}>{labelText}</span>
                                    <span className={`text-[10px] font-black ${colorClass}`}>
                                        {entry.value > 0 ? '+' : ''}{entry.value.toFixed(2)}%
                                    </span>
                                </div>
                                <div className="flex items-baseline justify-between gap-3">
                                    <span className="text-sm font-black text-slate-900 leading-none">
                                        {isPortfolio ? `₹${actual?.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : actual?.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                    </span>
                                    {isPortfolio && (
                                        <div className="flex items-center gap-1 opacity-70">
                                            <span className="text-[8px] font-bold text-slate-400 uppercase">NAV</span>
                                            <span className="text-xs font-black text-slate-600">₹{nav?.toFixed(2)}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }
    return null;
};

export default function Dashboard() {

    const [loading, setLoading] = useState(true);
    const [data, setData] = useState({
        fd: 0,
        equity: 0,
        mf: 0,
        bonds: 0,
        other: 0,
        liquidable_assets: 0,
        total: 0,
        equity_nav: 0,
        equity_pnl_pct: 0,
        portfolio_nav: 100, // Default
        portfolio_units: 0,
        // New Split Fields
        equity_portfolio_nav: 100,
        equity_portfolio_units: 0,
        mf_nav_price: 100,
        mf_units: 0,

        count: {
            fd: 0,
            equity: 0,
            mf: 0,
            bonds: 0,
            other: 0,
            liquidable: 0
        },
        star_breakdown: [] as { stars: number, count: number, value: number }[]
    });

    const [growthData, setGrowthData] = useState([]);
    const [navHistory, setNavHistory] = useState<any[]>([]);
    const [navPeriod, setNavPeriod] = useState("month");
    const [growthPeriod, setGrowthPeriod] = useState("1year");
    const [loadingGrowth, setLoadingGrowth] = useState(true);
    const [loadingNAV, setLoadingNAV] = useState(true);
    const [error, setError] = useState(false);
    const [showMFNAV, setShowMFNAV] = useState(false);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const res = await api.get(`/dashboard/summary?_t=${Date.now()}`);
                setData(prev => ({ ...prev, ...res.data }));
            } catch (err) {
                console.error("Failed to fetch dashboard summary", err);
                setError(true);
            } finally {
                setLoading(false);
            }
        };

        const safetyTimer = setTimeout(() => {
            setLoading(false);
        }, 10000);



        fetchSummary();

        return () => clearTimeout(safetyTimer);
    }, []);

    // Re-fetch growth when period changes
    useEffect(() => {
        const fetchGrowth = async () => {
            setLoadingGrowth(true);
            try {
                const res = await api.get(`/dashboard/growth?period=${growthPeriod}&_t=${Date.now()}`);
                setGrowthData(res.data);
            } catch (err) {
                console.error("Failed to fetch growth analysis", err);
            } finally {
                setLoadingGrowth(false);
            }
        };
        fetchGrowth();
    }, [growthPeriod]);

    useEffect(() => {
        const fetchNAVHistory = async () => {
            setLoadingNAV(true);
            try {
                const res = await api.get(`/analytics/nav-history?period=${navPeriod}&_t=${Date.now()}`);
                setNavHistory(res.data);
            } catch (err) {
                console.error("Failed to fetch NAV history", err);
            } finally {
                setLoadingNAV(false);
            }
        };
        fetchNAVHistory();
    }, [navPeriod]);

    // Normalize NAV history to % change from first point (so both start at 0%)
    const normalizedNavHistory = (() => {
        if (!navHistory.length) return [];
        const validEquity = navHistory.filter(r => r.nav_per_share > 0);
        const validMF = navHistory.filter(r => r.mf_nav > 0);
        const validValue = navHistory.filter(r => r.total_value > 0);
        const baseEquity = validEquity.length ? validEquity[0].nav_per_share : 1;
        const baseMF = validMF.length ? validMF[0].mf_nav : 1;
        const baseValue = validValue.length ? validValue[0].total_value : 1;
        return navHistory.map(r => ({
            ...r,
            nav_pct: r.nav_per_share > 0 ? parseFloat((((r.nav_per_share - baseEquity) / baseEquity) * 100).toFixed(2)) : null,
            mf_pct: r.mf_nav > 0 ? parseFloat((((r.mf_nav - baseMF) / baseMF) * 100).toFixed(2)) : null,
            value_pct: r.total_value > 0 ? parseFloat((((r.total_value - baseValue) / baseValue) * 100).toFixed(2)) : null,
        }));
    })();

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        const exportData = [
            { Category: 'Equity', Value: data.equity },
            { Category: 'Mutual Funds', Value: data.mf },
            { Category: 'Bonds', Value: data.bonds },
            { Category: 'Fixed Deposits', Value: data.fd },
            { Category: 'Liquidable Assets', Value: data.liquidable_assets },
            { Category: 'Other Assets (Illiquid)', Value: data.other },
            { Category: 'Total Net Worth', Value: data.total }
        ];

        if (format === 'pdf') {
            exportToPDF(exportData, ['Category', 'Value'], 'Portfolio Summary');
        } else if (format === 'excel') {
            exportToExcel(exportData, 'Portfolio_Summary');
        } else {
            exportToCSV(exportData, 'Portfolio_Summary');
        }
    };

    if (error) {
        return (
            <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
                <div className="text-red-500 font-bold text-xl">Connection Error</div>
                <p className="text-slate-500 max-w-sm">We couldn't reach the calculation engine. Please check if your backend is running or refresh the page.</p>
                <button onClick={() => window.location.reload()} className="bg-indigo-600 text-white px-6 py-2 rounded-lg">Retry</button>
            </div>
        );
    }

    const chartData = [
        { name: "Fixed Deposits", value: data.fd, color: "#0ea5e9" }, // Sky Blue
        { name: "Equity", value: data.equity, color: "#10b981" }, // Emerald
        { name: "Mutual Funds", value: data.mf, color: "#f97316" }, // Orange
        { name: "Bonds", value: data.bonds, color: "#f43f5e" }, // Rose
        { name: "Liquidable Assets", value: data.liquidable_assets, color: "#eab308" }, // Yellow
    ].filter(d => d.value > 0);

    if (loading) {
        return (
            <div className="flex h-[60vh] flex-col items-center justify-center gap-4">
                <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
                <p className="text-slate-500 font-medium">Calculating your net worth...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 lg:space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div>
                    <h2 className="text-xl sm:text-2xl lg:text-3xl font-black tracking-tight text-slate-900 uppercase">Executive Dashboard</h2>
                    <p className="text-slate-500 text-xs sm:text-sm lg:text-base">Real-time overview of your global wealth.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <button onClick={() => handleExport('pdf')} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-red-600 text-white px-4 py-2.5 rounded-xl hover:bg-red-700 transition-all font-bold text-xs shadow-sm uppercase">
                        <Download className="w-4 h-4" />
                        PDF
                    </button>
                    <button onClick={() => handleExport('excel')} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-2.5 rounded-xl hover:bg-green-700 transition-all font-bold text-xs shadow-sm uppercase">
                        <Download className="w-4 h-4" />
                        Excel
                    </button>
                    <button onClick={() => handleExport('csv')} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2.5 rounded-xl hover:bg-blue-700 transition-all font-bold text-xs shadow-sm uppercase">
                        <Download className="w-4 h-4" />
                        CSV
                    </button>
                </div>
            </div>

            {/* Main Net Worth Card */}
            <div className="relative overflow-hidden rounded-[1.5rem] sm:rounded-[2rem] bg-indigo-600 p-4 sm:p-6 lg:p-8 text-white shadow-2xl shadow-indigo-200">
                <div className="relative z-10 flex flex-col md:flex-row justify-between items-center gap-4 sm:gap-8">
                    <div className="flex-1 text-center md:text-left">
                        <p className="text-indigo-100 text-xs sm:text-sm lg:text-base font-semibold uppercase tracking-wide mb-1 sm:mb-2 opacity-90">Consolidated Net Worth</p>
                        <div className="text-2xl sm:text-4xl lg:text-5xl font-bold flex items-baseline justify-center md:justify-start gap-1.5 sm:gap-2">
                            <span className="text-xs sm:text-2xl font-bold opacity-60">₹</span>
                            {data.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <p className="text-indigo-100 text-[10px] sm:text-xs lg:text-sm mt-2 sm:mt-3 font-semibold uppercase tracking-wide opacity-80 leading-tight">
                            Includes: FD + Equity + MF + Bonds + Liquids
                        </p>
                    </div>

                    <div className="w-full md:w-auto flex flex-row gap-3 sm:gap-4">
                        {/* Equity NAV Box */}
                        <div className="flex-1 bg-white/10 backdrop-blur-md rounded-xl p-3 sm:p-4 border border-white/10 shadow-lg min-w-[120px] lg:min-w-[180px]">
                            <div className="mb-2">
                                <p className="text-indigo-50 text-[10px] lg:text-xs font-bold uppercase tracking-wide opacity-90 mb-1">Equity NAV</p>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-xs lg:text-sm font-semibold opacity-60">₹</span>
                                    <span className="text-lg sm:text-xl font-bold">{(data.equity_portfolio_nav || 100).toLocaleString('en-IN', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[9px] sm:text-[10px] font-bold text-white bg-rose-500 px-1.5 py-0.5 rounded shadow-sm">
                                    Units: {(data.equity_portfolio_units || 0).toFixed(4)}
                                </span>
                                {data.equity_pnl_pct !== 0 && (
                                    <span className={`text-[9px] font-bold ${data.equity_pnl_pct >= 0 ? "text-emerald-300" : "text-red-300"}`}>
                                        {data.equity_pnl_pct > 0 ? '+' : ''}{data.equity_pnl_pct}%
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* MF NAV Box */}
                        <div className="flex-1 bg-white/10 backdrop-blur-md rounded-xl p-3 sm:p-4 border border-white/10 shadow-lg min-w-[120px] lg:min-w-[180px]">
                            <div className="mb-2">
                                <p className="text-orange-50 text-[10px] lg:text-xs font-bold uppercase tracking-wide opacity-90 mb-1">MF NAV</p>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-xs lg:text-sm font-semibold opacity-60">₹</span>
                                    <span className="text-lg sm:text-xl font-bold">{(data.mf_nav_price || 100).toLocaleString('en-IN', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[9px] sm:text-[10px] font-bold text-white bg-rose-500 px-1.5 py-0.5 rounded shadow-sm">
                                    Units: {(data.mf_units || 0).toFixed(4)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
                {/* Decorative background shape */}
                <div className="absolute -right-20 -top-20 w-80 h-80 bg-indigo-400 rounded-full opacity-30 blur-[100px]"></div>
            </div>

            {/* Asset Break-up Cards */}
            < div className="grid gap-2 sm:gap-3 grid-cols-2 lg:grid-cols-5 whitespace-nowrap overflow-x-auto sm:overflow-visible pb-4 sm:pb-0" >
                <div className="group rounded-xl border bg-white p-2.5 sm:p-4 transition-all hover:shadow-lg hover:-translate-y-1">
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="p-1 bg-sky-50 rounded-lg text-sky-600 group-hover:bg-sky-600 group-hover:text-white transition-colors">
                            <Wallet className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </div>
                        <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-tight text-sky-600 bg-sky-50 px-2 py-0.5 rounded-full whitespace-nowrap">Low Risk</span>
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700 uppercase tracking-wide mb-0.5">Fixed Deposits ({data.count.fd})</p>
                        <p className="text-base sm:text-xl font-bold text-slate-900 break-all">₹{data.fd.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                    </div>
                </div>

                <div className="group rounded-xl border bg-white p-2.5 sm:p-4 transition-all hover:shadow-lg hover:-translate-y-1">
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="p-1 bg-emerald-50 rounded-lg text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                            <TrendingUp className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </div>
                        <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-tight text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full whitespace-nowrap">Growth</span>
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700 uppercase tracking-wide mb-0.5">Equity ({data.count.equity})</p>
                        <div className="flex items-baseline gap-2">
                            <p className="text-base sm:text-xl font-bold text-slate-900 break-all">₹{data.equity.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                            <span className="text-xs sm:text-sm font-semibold text-emerald-600">+1.2%</span>
                        </div>
                    </div>
                </div>

                <div className="group rounded-xl border bg-white p-2.5 sm:p-4 transition-all hover:shadow-lg hover:-translate-y-1">
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="p-1 bg-orange-50 rounded-lg text-orange-600 group-hover:bg-orange-600 group-hover:text-white transition-colors">
                            <DollarSign className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </div>
                        <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-tight text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full whitespace-nowrap">Diversified</span>
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700 uppercase tracking-wide mb-0.5">Mutual Funds ({data.count.mf})</p>
                        <div className="flex flex-col">
                            <div className="flex items-baseline gap-2">
                                <p className="text-base sm:text-xl font-bold text-slate-900 break-all">₹{data.mf.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                            </div>
                            <div className="flex items-center gap-1 mt-0.5 opacity-80">
                                <span className="text-[10px] sm:text-xs font-semibold text-slate-400 uppercase bg-slate-100 px-1 py-0.5 rounded">NAV</span>
                                <span className="text-xs sm:text-sm font-bold text-slate-700">
                                    {(data as any).mf_nav ? (data as any).mf_nav.toFixed(4) : "0.0000"}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="group rounded-xl border bg-white p-2.5 sm:p-4 transition-all hover:shadow-lg hover:-translate-y-1">
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="p-1 bg-rose-50 rounded-lg text-rose-600 group-hover:bg-rose-600 group-hover:text-white transition-colors">
                            <Lock className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </div>
                        <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-tight text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full whitespace-nowrap">Secure</span>
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700 uppercase tracking-wide mb-0.5">Bonds ({data.count.bonds})</p>
                        <p className="text-base sm:text-xl font-bold text-slate-900 break-all">₹{data.bonds.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                    </div>
                </div>

                <div className="group rounded-xl border bg-white p-2.5 sm:p-4 transition-all hover:shadow-lg hover:-translate-y-1">
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="p-1 bg-yellow-50 rounded-lg text-yellow-600 group-hover:bg-yellow-600 group-hover:text-white transition-colors">
                            <Coins className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </div>
                        <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-tight text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded-full whitespace-nowrap">Liquidable</span>
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700 uppercase tracking-wide mb-0.5">Liquidable ({data.count.liquidable})</p>
                        <p className="text-base sm:text-xl font-bold text-slate-900 break-all">₹{data.liquidable_assets.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                    </div>
                </div>

                <div className="group rounded-xl border bg-slate-50 p-2.5 sm:p-4 transition-all opacity-75 hover:opacity-100">
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="p-1 bg-purple-50 rounded-lg text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                            <LandPlot className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </div>
                        <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-tight text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full whitespace-nowrap">Tracked Only</span>
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700 uppercase tracking-wide mb-0.5">Real Estate/Misc ({data.count.other})</p>
                        <p className="text-base sm:text-xl font-bold text-slate-900 break-all">₹{data.other.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                    </div>
                </div>
            </div >

            {/* Charts Section */}
            < div className="grid gap-6 md:grid-cols-2" >
                <div className="rounded-xl border bg-white p-3 sm:p-6 h-[400px] sm:h-[400px] shadow-sm overflow-hidden flex flex-col">
                    <h3 className="text-lg sm:text-2xl lg:text-3xl font-bold text-slate-800 mb-2 sm:mb-6 uppercase tracking-wide px-1">Asset Allocation</h3>
                    {chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={chartData}
                                    cx="50%"
                                    cy="40%"
                                    innerRadius={60}
                                    outerRadius={90}
                                    paddingAngle={10}
                                    dataKey="value"
                                    stroke="none"
                                >
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)', padding: '12px' }}
                                    formatter={(val: any) => `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                                />
                                <Legend
                                    verticalAlign="bottom"
                                    align="center"
                                    iconType="circle"
                                    layout="horizontal"
                                    wrapperStyle={{
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        textTransform: 'uppercase',
                                        paddingTop: '5px',
                                        width: '100%',
                                        display: 'flex',
                                        flexWrap: 'wrap',
                                        justifyContent: 'center',
                                        gap: '8px'
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="h-full flex items-center justify-center text-slate-400 italic font-medium">No assets tracked yet</div>
                    )}
                </div>

                {/* Growth Performance chart */}
                <div className="rounded-xl border bg-white p-3 sm:p-4 min-h-[400px] shadow-sm flex flex-col">
                    <div className="mb-2 sm:mb-3">
                        <div className="flex items-baseline gap-2 px-1">
                            <h3 className="text-xs sm:text-sm font-bold text-slate-800 uppercase tracking-wide">Growth Performance</h3>
                            <p className="text-[9px] font-normal text-slate-400 uppercase tracking-wide opacity-80">% Change from baseline</p>
                        </div>
                        {/* Period Filter Buttons */}
                        <div className="flex flex-wrap gap-0.5 mt-2 px-1">
                            {[
                                { label: "1W", val: "1week" },
                                { label: "QTR", val: "qtr" },
                                { label: "HALF", val: "half" },
                                { label: "1Y", val: "1year" },
                                { label: "2Y", val: "2year" },
                                { label: "3Y", val: "3year" },
                                { label: "5Y", val: "5year" },
                            ].map((p) => (
                                <button
                                    key={p.val}
                                    onClick={() => setGrowthPeriod(p.val)}
                                    className={`px-1.5 py-0.5 text-[8px] font-bold rounded-md transition-all uppercase ${growthPeriod === p.val
                                        ? "bg-emerald-600 text-white shadow-md"
                                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                                        }`}
                                >
                                    {p.label}
                                </button>
                            ))}
                        </div>
                    </div>
                    {loadingGrowth ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-slate-50/50 rounded-xl border border-dashed">
                            <Loader2 className="w-8 h-8 animate-spin text-slate-300 mb-4" />
                            <p className="text-slate-400 text-sm font-medium italic">Analyzing market performance...</p>
                        </div>
                    ) : growthData.length > 0 ? (
                        <div className="flex-1 min-h-0">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={growthData} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 9, fontWeight: 700, fill: '#64748b' }}
                                        tickFormatter={(str) => {
                                            const d = new Date(str);
                                            return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                        }}
                                        axisLine={false}
                                        tickLine={false}
                                        minTickGap={20}
                                        height={40}
                                    />
                                    <YAxis
                                        domain={[-10, 15]}
                                        ticks={[-10, -5, 0, 5, 10, 15]}
                                        tick={{ fontSize: 9, fontWeight: 700, fill: '#64748b' }}
                                        tickFormatter={(val) => `${val > 0 ? '+' : ''}${val}%`}
                                        axisLine={false}
                                        tickLine={false}
                                        width={55}
                                    />
                                    <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" strokeWidth={1.5} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend verticalAlign="top" height={30} iconType="circle" wrapperStyle={{ fontSize: '8px', fontWeight: 700, textTransform: 'uppercase' }} />
                                    <Line
                                        type="monotone"
                                        dataKey="portfolio"
                                        stroke="#10b981"
                                        strokeWidth={4}
                                        dot={{ r: 4, fill: '#10b981', strokeWidth: 2, stroke: '#fff' }}
                                        activeDot={{ r: 8, strokeWidth: 0, fill: '#10b981' }}
                                        name="MY PORTFOLIO"
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="nifty"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        strokeDasharray="5 5"
                                        dot={false}
                                        name="NIFTY 50"
                                        connectNulls={true}
                                        activeDot={{ r: 6, strokeWidth: 0, fill: '#3b82f6' }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="sensex"
                                        stroke="#f59e0b"
                                        strokeWidth={2}
                                        strokeDasharray="5 5"
                                        dot={false}
                                        name="SENSEX BENCHMARK"
                                        connectNulls={true}
                                        activeDot={{ r: 6, strokeWidth: 0, fill: '#f59e0b' }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-slate-400 italic font-medium">No historical data available</div>
                    )}
                </div>
            </div >

            {/* Bottom Row: NAV Trend + New Box */}
            <div className="grid gap-6 lg:grid-cols-5">
                {/* NAV History Section */}
                <div className="lg:col-span-3 rounded-xl border bg-white p-3 sm:p-4 min-h-[400px] shadow-sm flex flex-col">
                    <div className="mb-3 flex flex-col sm:flex-row sm:items-center justify-start gap-3 flex-wrap">
                        <div className="flex items-baseline gap-2">
                            <h3 className="text-xs sm:text-sm font-bold text-slate-800 uppercase tracking-wide">Net Worth / NAV Trend</h3>
                            <p className="hidden md:block text-[9px] font-normal text-slate-400 uppercase tracking-wide opacity-80">Historical snapshot of valuations</p>
                        </div>

                        <div className="flex items-center gap-3">
                            {/* NAV Toggle */}
                            <div className="flex bg-slate-100 p-0.5 rounded-lg">
                                <button
                                    onClick={() => setShowMFNAV(false)}
                                    className={`px-1.5 py-0.5 text-[9px] font-bold rounded-md transition-all ${!showMFNAV ? "bg-white text-indigo-600 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
                                >
                                    Equity
                                </button>
                                <button
                                    onClick={() => setShowMFNAV(true)}
                                    className={`px-1.5 py-0.5 text-[9px] font-bold rounded-md transition-all ${showMFNAV ? "bg-white text-orange-500 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
                                >
                                    MF
                                </button>
                            </div>

                            <div className="flex gap-0.5 overflow-x-auto">
                                {[
                                    { label: "1D", val: "day" },
                                    { label: "1W", val: "week" },
                                    { label: "1M", val: "month" },
                                    { label: "3M", val: "qtr" },
                                    { label: "6M", val: "half_year" },
                                    { label: "1Y", val: "year" },
                                    { label: "3Y", val: "3year" },
                                    { label: "MAX", val: "all" },
                                ].map((p) => (
                                    <button
                                        key={p.val}
                                        onClick={() => setNavPeriod(p.val)}
                                        className={`px-1 py-0.5 text-[8px] font-bold rounded-md transition-all ${navPeriod === p.val
                                            ? "bg-indigo-600 text-white shadow-md"
                                            : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                                            }`}
                                    >
                                        {p.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {navHistory.length > 0 && (
                            <div className="flex gap-2">
                                <div className={`px-1.5 py-0.5 rounded-lg text-center border ${showMFNAV ? "bg-orange-50 border-orange-100" : "bg-indigo-50 border-indigo-100"}`}>
                                    <span className={`text-[8px] font-bold uppercase block ${showMFNAV ? "text-orange-400" : "text-indigo-400"}`}>
                                        {showMFNAV ? "MF" : "Equity"} NAV
                                    </span>
                                    <span className={`text-base font-black ${showMFNAV ? "text-orange-600" : "text-indigo-700"}`}>
                                        {(showMFNAV
                                            ? (navHistory[navHistory.length - 1].mf_nav || 0)
                                            : navHistory[navHistory.length - 1].nav_per_share
                                        ).toFixed(2)}
                                    </span>
                                </div>
                                <div className="bg-emerald-50 px-1.5 py-0.5 rounded-lg text-center border border-emerald-100">
                                    <span className="text-[8px] font-bold text-emerald-500 uppercase block">Net Worth</span>
                                    <span className="text-base font-black text-emerald-700">₹{Number(navHistory[navHistory.length - 1].total_value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                                </div>
                                <div className="bg-slate-50 px-1.5 py-0.5 rounded-lg text-center border border-dashed border-slate-200 min-w-[70px]">
                                    <span className="text-[8px] font-bold text-slate-400 uppercase block">Strategic Plan</span>
                                    <span className="text-[10px] font-bold text-slate-300 italic">—</span>
                                </div>
                            </div>
                        )}
                    </div>
                    {
                        loadingNAV ? (
                            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-slate-50/50 rounded-xl border border-dashed">
                                <Loader2 className="w-8 h-8 animate-spin text-slate-300 mb-4" />
                                <p className="text-slate-400 text-sm font-medium italic">Tracing historical valuations...</p>
                            </div>
                        ) : navHistory.length > 0 ? (
                            <div className="h-[400px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={normalizedNavHistory} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                        <XAxis
                                            dataKey="timestamp"
                                            tick={{ fontSize: 8, fontWeight: 700, fill: '#64748b' }}
                                            tickFormatter={(str) => {
                                                const d = new Date(str);
                                                return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                            }}
                                            angle={-30}
                                            textAnchor="end"
                                            axisLine={false}
                                            tickLine={false}
                                            minTickGap={5}
                                            height={50}
                                        />
                                        <YAxis
                                            hide={false}
                                            domain={[-10, 15]}
                                            ticks={[-10, -5, 0, 5, 10, 15]}
                                            tick={{ fontSize: 9, fontWeight: 800, fill: showMFNAV ? '#f97316' : '#6366f1' }}
                                            axisLine={false}
                                            tickLine={false}
                                            tickFormatter={(val) => `${val > 0 ? '+' : ''}${Number(val).toFixed(0)}%`}
                                            width={50}
                                        />
                                        <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" strokeWidth={1.5} />
                                        <Tooltip
                                            content={({ active, payload, label }: any) => {
                                                if (active && payload && payload.length) {
                                                    const d = new Date(label);
                                                    const pctEntry = payload.find((p: any) => p.dataKey === (showMFNAV ? "mf_pct" : "nav_pct"));
                                                    const rawEntry = pctEntry?.payload;
                                                    const rawNav = showMFNAV ? rawEntry?.mf_nav : rawEntry?.nav_per_share;
                                                    const pctVal = pctEntry?.value ?? null;
                                                    return (
                                                        <div className="bg-slate-900 text-white p-2 sm:p-3 rounded-xl shadow-xl border border-slate-700 min-w-[150px]">
                                                            <p className="text-[8px] font-black uppercase text-slate-400 mb-2 border-b border-slate-700 pb-1">
                                                                {d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                                            </p>
                                                            <p className={`text-[10px] font-bold uppercase mb-0.5 ${showMFNAV ? 'text-orange-300' : 'text-indigo-300'}`}>
                                                                {showMFNAV ? 'MF NAV' : 'Equity NAV'}
                                                            </p>
                                                            <p className="text-lg font-black text-white">
                                                                {pctVal !== null ? `${pctVal >= 0 ? '+' : ''}${pctVal.toFixed(2)}%` : '—'}
                                                            </p>
                                                            {rawNav != null && (
                                                                <p className="text-[10px] text-slate-400 mt-0.5 mb-1.5 border-b border-slate-700/50 pb-1">NAV: {Number(rawNav).toFixed(4)}</p>
                                                            )}
                                                            {rawEntry?.total_value != null && (
                                                                <>
                                                                    <p className="text-[10px] font-bold text-emerald-300 uppercase mb-0.5">Net Worth</p>
                                                                    <p className="text-sm font-black text-white">₹{Number(rawEntry.total_value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
                                                                </>
                                                            )}
                                                        </div>
                                                    );
                                                }
                                                return null;
                                            }}
                                        />
                                        <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '8px', fontWeight: 800, textTransform: 'uppercase' }} />
                                        <Line
                                            type="monotone"
                                            dataKey={showMFNAV ? "mf_pct" : "nav_pct"}
                                            name={showMFNAV ? "MF NAV %" : "Equity NAV %"}
                                            stroke={showMFNAV ? "#f97316" : "#6366f1"}
                                            strokeWidth={3}
                                            dot={false}
                                            activeDot={{ r: 4, strokeWidth: 0, fill: showMFNAV ? "#ea580c" : "#4f46e5" }}
                                            connectNulls={true}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="value_pct"
                                            name="NET WORTH growth"
                                            stroke="#10b981"
                                            strokeWidth={2}
                                            strokeDasharray="4 4"
                                            dot={false}
                                            activeDot={{ r: 4, strokeWidth: 0, fill: "#10b981" }}
                                            connectNulls={true}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-slate-50/50 rounded-xl border border-dashed">
                                <p className="text-slate-400 text-sm font-medium italic">NAV history tracking initialized. Data will appear after the first scheduled snapshot.</p>
                            </div>
                        )
                    }
                </div>

                {/* Star Ratings Widget */}
                <div className="lg:col-span-2 rounded-xl border bg-white shadow-sm flex flex-col p-4 sm:p-6 lg:p-8 min-h-[400px] relative overflow-hidden group">
                    <div className="flex items-center justify-between mb-6 sm:mb-8 relative z-10">
                        <div>
                            <h3 className="text-lg sm:text-2xl font-bold text-slate-900 uppercase tracking-tight">Star Ratings</h3>
                            <p className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Portfolio Quality Mix</p>
                        </div>
                        <div className="p-2.5 bg-amber-50 rounded-2xl border border-amber-100/50">
                            <Star className="w-5 h-5 sm:w-6 sm:h-6 text-amber-500 fill-amber-500" />
                        </div>
                    </div>

                    <div className="space-y-4 sm:space-y-5 relative z-10">
                        {data.star_breakdown && data.star_breakdown.length > 0 ? (
                            data.star_breakdown.map((item) => (
                                <div key={item.stars} className="flex items-center justify-between group/row p-2.5 sm:p-3 rounded-2xl hover:bg-slate-50 transition-all duration-300 border border-transparent hover:border-slate-100">
                                    <div className="flex items-center gap-3 sm:gap-4">
                                        <div className="flex items-center gap-0.5">
                                            {item.stars > 0 ? (
                                                [...Array(5)].map((_, i) => (
                                                    <Star
                                                        key={i}
                                                        className={`w-3 h-3 sm:w-4 sm:h-4 ${i < item.stars ? 'text-amber-400 fill-amber-400' : 'text-slate-200 fill-slate-100'}`}
                                                    />
                                                ))
                                            ) : (
                                                <div className="flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded-md">
                                                    <Star className="w-3 h-3 text-slate-400 fill-slate-300" />
                                                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">Unrated</span>
                                                </div>
                                            )}
                                        </div>
                                        <div className="flex items-baseline gap-1.5 ml-1">
                                            <span className="text-sm sm:text-lg font-black text-slate-700 tracking-tight">{item.count}</span>
                                            <span className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wide">Scrips</span>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="flex items-baseline justify-end gap-1">
                                            <span className="text-[10px] sm:text-xs font-bold text-slate-400">₹</span>
                                            <span className="text-sm sm:text-xl font-black text-slate-900 tracking-tight">
                                                {item.value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                            </span>
                                        </div>
                                        <div className="w-full h-1.5 bg-slate-100 rounded-full mt-2 overflow-hidden">
                                            <div
                                                className={`h-full rounded-full transition-all duration-1000 ease-out ${item.stars >= 4 ? 'bg-emerald-500' :
                                                    item.stars === 3 ? 'bg-blue-500' :
                                                        item.stars > 0 ? 'bg-amber-500' :
                                                            'bg-slate-300'
                                                    }`}
                                                style={{ width: `${Math.min(100, (item.value / data.equity) * 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 px-4 border-2 border-dashed border-slate-100 rounded-3xl bg-slate-50/50">
                                <Star className="w-8 h-8 text-slate-200 mb-3" />
                                <p className="text-slate-400 font-bold text-xs uppercase tracking-widest text-center">Awaiting Rating Compute</p>
                            </div>
                        )}
                    </div>

                    {/* Background Decorative Accents */}
                    <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50 rounded-full -mr-16 -mt-16 blur-3xl opacity-60"></div>
                    <div className="absolute bottom-0 left-0 w-24 h-24 bg-indigo-50 rounded-full -ml-12 -mb-12 blur-2xl opacity-40"></div>
                </div>
            </div>
        </div >
    );
}
