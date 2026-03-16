import { useState, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
    ArrowUpRight,
    ChevronRight,
    ChevronDown,
    User as UserIcon,
    Filter,
    Download,
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    Info,
    Calculator,
    Zap,
    Scale
} from "lucide-react";
import api, { getAllRatings } from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";

type InvestorDetail = {
    name: string;
    interest: number;
    principal: number;
    tax: number;
    fds: {
        bank_name: string;
        fd_code: string;
        principal: number;
        interest_rate: number;
        start_date: string;
        maturity_date: string;
        interest_earned: number;
    }[];
};

type FDReport = {
    year: number;
    interest: number;
    principal: number;
    tax_expected: number;
    investor_breakdown: InvestorDetail[];
};

type BadPerformer = {
    symbol: string;
    operators: string;
    instrument_type: string;
    avg_buy_price: number;
    ltp: number;
    pnl_percentage: number;
    total_loss: number;
    total_qty: number;
    invested_amount: number;
    current_value: number;
    pf_units: number;
    daily_change?: number;
    daily_pnl_percentage?: number;
    daily_pnl?: number;
};

type DmaReport = {
    symbol: string;
    cmp: number;
    dma_50: number;
    dma_200: number;
    signal: string;
    dma_50_status: "Above" | "Below";
    dma_200_status: "Above" | "Below";
};

type TabType = "interest" | "pnl" | "projections" | "dma";

export default function ReportsPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const activeTab = (searchParams.get("tab") as TabType) || "interest";

    const [fdData, setFdData] = useState<FDReport[]>([]);
    const [badStocks, setBadStocks] = useState<BadPerformer[]>([]);
    const [dmaData, setDmaData] = useState<{ results: DmaReport[], summary: any, total_value: number }>({ results: [], summary: {}, total_value: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedYear, setExpandedYear] = useState<number | null>(null);
    const [selectedYearProj, setSelectedYearProj] = useState<any | null>(null);
    const [summary, setSummary] = useState<any>(null);

    // Simulation Parameters
    const [equityReturn, setEquityReturn] = useState(12);
    const [mfReturn, setMfReturn] = useState(8);
    const [fdReturn, setFdReturn] = useState(7);
    const [initialWithdrawal, setInitialWithdrawal] = useState(5000000); // 50L
    const [withdrawalStepUp, setWithdrawalStepUp] = useState(8);

    // Filter controls
    const [lossThreshold, setLossThreshold] = useState<number>(15);
    const [showAllMerged, setShowAllMerged] = useState(true);
    const [sortConfig, setSortConfig] = useState<{ key: keyof BadPerformer; direction: 'asc' | 'desc' } | null>(null);
    const [selectedTaxDetails, setSelectedTaxDetails] = useState<any | null>(null);
    const [extraDividend, setExtraDividend] = useState(0);
    const [extraBusiness, setExtraBusiness] = useState(0);
    const [extraOther, setExtraOther] = useState(0);

    // DMA Filters
    const [dma50Filter, setDma50Filter] = useState<'all' | 'Above' | 'Below'>('all');
    const [dma200Filter, setDma200Filter] = useState<'all' | 'Above' | 'Below'>('all');

    // Portfolio Alerts search + star filter + star sort
    const [pnlSearch, setPnlSearch] = useState('');
    const [pnlStarFilter, setPnlStarFilter] = useState(0);
    const [pnlSortStars, setPnlSortStars] = useState<'asc' | 'desc' | null>(null);

    // Technical Signals search + star filter + star sort
    const [dmaSearch, setDmaSearch] = useState('');
    const [dmaStarFilter, setDmaStarFilter] = useState(0);
    const [dmaSortStars, setDmaSortStars] = useState<'asc' | 'desc' | null>(null);

    // Star ratings map: scrip_code -> rating object
    const [ratingMap, setRatingMap] = useState<Record<string, any>>({});

    // Helper to render star badges
    const renderStars = (symbol: string) => {
        const code = symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '');
        const rating = ratingMap[code];
        if (!rating) return null;

        if (rating.data_state && rating.data_state !== 'RATED') {
            return (
                <div className="ml-1.5 flex flex-col" title={`Computing Rating: ${rating.data_state}`}>
                    <div className="flex items-center gap-1 text-indigo-500">
                        <Zap className="w-2.5 h-2.5 animate-pulse" />
                        <span className="text-[8px] font-black uppercase tracking-tighter">Wait</span>
                    </div>
                </div>
            );
        }

        const { star_rating, label, final_score, confidence_label } = rating;
        const filledColor = star_rating >= 4 ? '#059669' : star_rating === 3 ? '#d97706' : '#dc2626';

        return (
            <div className="ml-1.5 flex flex-col">
                <div className="flex items-center" title={`${label} · ${final_score}/100`}>
                    <span className="inline-flex items-center text-sm leading-none">
                        <span style={{ color: filledColor, letterSpacing: '-1px' }} className="font-black">{'★'.repeat(star_rating)}</span>
                        <span style={{ color: '#e2e8f0', letterSpacing: '-1px' }} className="font-black">{'★'.repeat(5 - star_rating)}</span>
                    </span>
                    {confidence_label && (
                        <span
                            className={`ml-1 text-[7px] font-black uppercase px-0.5 rounded-sm h-3 flex items-center ${confidence_label === 'Full' ? 'bg-emerald-50 text-emerald-600' :
                                confidence_label === 'High' ? 'bg-indigo-50 text-indigo-600' :
                                    confidence_label === 'Medium' ? 'bg-amber-50 text-amber-600' :
                                        'bg-slate-50 text-slate-400'
                                }`}
                            title={`Confidence: ${rating.confidence_pts_have}/${rating.confidence_pts_max}`}
                        >
                            {confidence_label[0]}
                        </span>
                    )}
                </div>
            </div>
        );
    };

    const filteredStocks = useMemo(() => {
        let base = showAllMerged ? badStocks : badStocks.filter(s => s.pnl_percentage <= -lossThreshold);

        // Search filter
        if (pnlSearch.trim()) {
            const term = pnlSearch.toLowerCase();
            base = base.filter(s => s.symbol.toLowerCase().includes(term) || s.operators.toLowerCase().includes(term));
        }

        // Star filter
        if (pnlStarFilter > 0) {
            base = base.filter(s => {
                const code = s.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '');
                return (ratingMap[code]?.star_rating ?? 0) === pnlStarFilter;
            });
        }

        // Primary Sort: Manual Column Sort (Daily P&L, Total P&L, etc)
        if (sortConfig) {
            const { key, direction } = sortConfig;
            base = [...base].sort((a, b) => {
                const aVal = a[key] ?? 0;
                const bVal = b[key] ?? 0;

                if (typeof aVal === 'number' && typeof bVal === 'number') {
                    return direction === 'asc' ? aVal - bVal : bVal - aVal;
                }
                const aStr = String(aVal).toLowerCase();
                const bStr = String(bVal).toLowerCase();
                return direction === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
            });
        }
        // Secondary Sort: Star Rating (only if manual sort isn't active)
        else if (pnlSortStars) {
            base = [...base].sort((a, b) => {
                const aStars = ratingMap[a.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '')]?.star_rating ?? 0;
                const bStars = ratingMap[b.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '')]?.star_rating ?? 0;
                return pnlSortStars === 'desc' ? bStars - aStars : aStars - bStars;
            });
        }
        return base;
    }, [badStocks, lossThreshold, showAllMerged, sortConfig, pnlSearch, pnlStarFilter, pnlSortStars, ratingMap]);

    const filteredDmaStocks = useMemo(() => {
        let base = (dmaData.results || []).filter(stock => {
            const match50 = dma50Filter === 'all' || stock.dma_50_status === dma50Filter;
            const match200 = dma200Filter === 'all' || stock.dma_200_status === dma200Filter;
            return match50 && match200;
        });

        // Search filter
        if (dmaSearch.trim()) {
            const term = dmaSearch.toLowerCase();
            base = base.filter(s => s.symbol.toLowerCase().includes(term));
        }

        // Star filter
        if (dmaStarFilter > 0) {
            base = base.filter(s => {
                const code = s.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '');
                return (ratingMap[code]?.star_rating ?? 0) === dmaStarFilter;
            });
        }

        // Sort by stars
        if (dmaSortStars) {
            base = [...base].sort((a, b) => {
                const aStars = ratingMap[a.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '')]?.star_rating ?? 0;
                const bStars = ratingMap[b.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '')]?.star_rating ?? 0;
                return dmaSortStars === 'desc' ? bStars - aStars : aStars - bStars;
            });
        }

        return base;
    }, [dmaData.results, dma50Filter, dma200Filter, dmaSearch, dmaStarFilter, dmaSortStars, ratingMap]);

    const summaryMetrics = useMemo(() => {
        const stocks = showAllMerged ? badStocks : filteredStocks;
        const totalInvested = stocks.reduce((sum, s) => sum + (s.invested_amount || 0), 0);
        const totalCurrentValue = stocks.reduce((sum, s) => sum + (s.current_value || 0), 0);
        const totalDailyPnl = stocks.reduce((sum, s) => sum + (s.daily_pnl || 0), 0);
        return { totalInvested, totalCurrentValue, totalDailyPnl };
    }, [badStocks, filteredStocks, showAllMerged]);

    const handleSort = (key: keyof BadPerformer) => {
        setPnlSortStars(null); // Clear star sort when column header is clicked
        setSortConfig(current => {
            if (current?.key === key) {
                return current.direction === 'asc' ? { key, direction: 'desc' } : null;
            }
            return { key, direction: 'asc' };
        });
    };

    useEffect(() => {
        setLoading(true);
        setError(null);
        Promise.all([
            api.get("/reports/fd-interest"),
            api.get("/reports/non-performing-equities"),
            api.get("/dashboard/summary"),
            api.get("/reports/dma-signals")
        ]).then(([fd, bad, summ, dma]) => {
            setFdData(fd.data || []);
            setBadStocks(bad.data || []);
            setSummary(summ.data);
            setDmaData(dma.data || { results: [], summary: {}, total_value: 0 });
        }).catch(err => {
            console.error(err);
            setError("Failed to load report data.");
        }).finally(() => setLoading(false));

        // Load ratings silently
        getAllRatings().then(data => setRatingMap(data)).catch(() => { });
    }, []);

    const simulatedProjections = useMemo(() => {
        if (!summary) return [];

        let curr_eq = summary.equity;
        let curr_mf = summary.mf;
        let curr_fd = summary.fd;
        let withdrawal = initialWithdrawal;

        const results = [];
        for (let i = 1; i <= 10; i++) {
            const start_eq = curr_eq;
            const start_mf = curr_mf;
            const start_fd = curr_fd;

            const growth_eq = curr_eq * (equityReturn / 100);
            const growth_mf = curr_mf * (mfReturn / 100);
            const growth_fd = curr_fd * (fdReturn / 100);

            curr_eq += growth_eq;
            curr_mf += growth_mf;
            curr_fd += growth_fd;

            let rem = withdrawal;
            const take_fd = Math.min(curr_fd, rem); curr_fd -= take_fd; rem -= take_fd;
            const take_mf = Math.min(curr_mf, rem); curr_mf -= take_mf; rem -= take_mf;
            const take_eq = Math.min(curr_eq, rem); curr_eq -= take_eq; rem -= take_eq;

            results.push({
                year: new Date().getFullYear() + i,
                start_equity: start_eq,
                start_mf: start_mf,
                start_fd: start_fd,
                growth_equity: growth_eq,
                growth_mf: growth_mf,
                growth_fd: growth_fd,
                equity: curr_eq,
                mf: curr_mf,
                fd: curr_fd,
                total: curr_eq + curr_mf + curr_fd,
                growth_earned: growth_eq + growth_mf + growth_fd,
                withdrawn: withdrawal - rem,
                actual_withdrawal: withdrawal,
                shortfall: rem
            });

            withdrawal = withdrawal * (1 + withdrawalStepUp / 100);
            if (curr_eq + curr_mf + curr_fd <= 0) break;
        }
        return results;
    }, [summary, equityReturn, mfReturn, fdReturn, initialWithdrawal, withdrawalStepUp]);

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        let exportData: any[] = [];
        let columns: string[] = [];
        let title = "";

        if (activeTab === "interest") {
            title = "FD Tax Report";
            columns = ['Financial Year', 'Family Assets', 'Merged Interest', 'Net Family Tax'];
            exportData = fdData.map(row => ({
                'Financial Year': `FY ${row.year}`,
                'Family Assets': row.principal,
                'Merged Interest': row.interest,
                'Net Family Tax': row.tax_expected
            }));
        } else if (activeTab === "pnl") {
            title = "Equity Scrip Alerts";
            columns = ['Rating', 'Symbol', 'Instrument Type', 'Operators', 'Total Qty', 'Invested Amount', 'Current Value', 'Day Change', 'PnL %', 'Total Loss'];
            exportData = filteredStocks.map(stock => {
                const code = stock.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '');
                const rating = ratingMap[code]?.star_rating ?? 0;
                return {
                    'Rating': '*'.repeat(rating) + '-'.repeat(5 - rating),
                    'Symbol': stock.symbol,
                    'Instrument Type': stock.instrument_type,
                    'Operators': stock.operators,
                    'Total Qty': stock.total_qty,
                    'Invested Amount': stock.invested_amount,
                    'Current Value': stock.current_value,
                    'Daily Gain/Loss': `${stock.daily_pnl && stock.daily_pnl >= 0 ? '+' : '-'}₹${Math.abs(stock.daily_pnl || 0).toLocaleString('en-IN')} (${stock.daily_pnl_percentage && stock.daily_pnl_percentage >= 0 ? '+' : '-'}${Math.abs(stock.daily_pnl_percentage || 0)}%)`,
                    'PnL %': stock.pnl_percentage,
                    'Total Loss': stock.total_loss
                };
            });
        } else if (activeTab === "projections") {
            title = "Portfolio Projections";
            columns = ['Year', 'Total Value (Cr)', 'Growth Earned (L)'];
            exportData = simulatedProjections.map(proj => ({
                'Year': `Year ${proj.year}`,
                'Total Value (Cr)': (proj.total / 10000000).toFixed(2),
                'Growth Earned (L)': (proj.growth_earned / 100000).toFixed(2)
            }));
        } else if (activeTab === "dma") {
            title = "Technical Signals (DMA)";
            columns = ['Rating', 'Symbol', 'CMP', '50 DMA', '200 DMA', 'Signal', '50 DMA Status', '200 DMA Status'];
            exportData = filteredDmaStocks.map(stock => {
                const code = stock.symbol.toUpperCase().replace(/^(NSE:|BSE:|BOM:)/, '');
                const rating = ratingMap[code]?.star_rating ?? 0;
                return {
                    'Rating': '*'.repeat(rating) + '-'.repeat(5 - rating),
                    'Symbol': stock.symbol,
                    'CMP': stock.cmp,
                    '50 DMA': stock.dma_50,
                    '200 DMA': stock.dma_200,
                    'Signal': stock.signal,
                    '50 DMA Status': stock.dma_50_status,
                    '200 DMA Status': stock.dma_200_status
                };
            });
        }

        if (format === 'pdf') {
            exportToPDF(exportData, columns, title);
        } else if (format === 'excel') {
            exportToExcel(exportData, title.replace(/\s+/g, '_'));
        } else {
            exportToCSV(exportData, title.replace(/\s+/g, '_'));
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Computing Matrix...</p>
        </div>
    );

    return (
        <div className="space-y-6 pb-20">
            {/* Desktop Tab Navigation */}
            <div className="hidden lg:flex items-center gap-2 mb-8 bg-slate-100 p-1.5 rounded-2xl w-fit">
                {[
                    { id: 'interest', label: 'Tax Analysis' },
                    { id: 'pnl', label: 'Portfolio Alerts' },
                    { id: 'projections', label: 'Growth Simulation' },
                    { id: 'dma', label: 'Technical Signals' }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setSearchParams({ tab: tab.id })}
                        className={`px-6 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wide transition-all ${activeTab === tab.id
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/50'
                            }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Mobile Tab Navigation */}
            <div className="flex overflow-x-auto gap-2 pb-2 no-scrollbar lg:hidden">
                {[
                    { id: 'interest', label: 'Tax Analysis' },
                    { id: 'pnl', label: 'Portfolio Alerts' },
                    { id: 'projections', label: 'Growth Simulation' },
                    { id: 'dma', label: 'Technical Signals' }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setSearchParams({ tab: tab.id })}
                        className={`px-4 py-2 rounded-full font-bold text-xs uppercase tracking-wide whitespace-nowrap transition-all border ${activeTab === tab.id
                            ? 'bg-slate-900 text-white border-slate-900 shadow-md'
                            : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
                            }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div>
                    <h2 className="text-[10px] sm:text-xs lg:text-sm font-black tracking-tight text-slate-900 uppercase">
                        {activeTab === "interest" && "FD Tax Simulation"}
                        {activeTab === "pnl" && "My Portfolio Alerts"}
                        {activeTab === "projections" && "Strategic Growth Path"}
                        {activeTab === "dma" && "Technical DMA Signals"}
                    </h2>
                    <p className="text-slate-500 mt-1 text-sm lg:text-base">
                        {activeTab === "interest" && "Detailed investor-wise breakdown of interest and tax liabilities."}
                        {activeTab === "pnl" && "Monitor underperforming merged assets and portfolio drag."}
                        {activeTab === "projections" && "10-Year simulation of portfolio growth with step-up withdrawals."}
                        {activeTab === "dma" && "Momentum analysis using 50-day and 200-day Moving Averages."}
                    </p>
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

            {error && (
                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl text-amber-800 text-sm font-medium">
                    {error}
                </div>
            )}

            {/* Main Panel */}
            <div className="transition-all duration-300">
                {activeTab === "interest" && (
                    <div className="bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden animate-in fade-in slide-in-from-bottom-4">
                        <div className="p-8 border-b border-slate-100 bg-slate-50/30">
                            <h3 className="text-xs font-black text-slate-900 uppercase">Investor-Wise Tax Liability</h3>
                            <p className="text-sm text-slate-500 mt-1 leading-relaxed font-medium">Interest is grouped by <span className="text-slate-900 font-bold">Investor Name</span> to apply independent tax slabs and Rebate 87A logic (New Regime AY 25-26 + 4% Cess).</p>
                        </div>
                        <div className="p-0 overflow-x-auto">
                            <table className="w-full text-left whitespace-nowrap">
                                <thead className="bg-slate-50">
                                    <tr>
                                        <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Financial Year</th>
                                        <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Family Assets</th>
                                        <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Merged Interest</th>
                                        <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Net Family Tax</th>
                                        <th className="w-10"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {fdData.map(row => (
                                        <>
                                            <tr key={row.year} className="hover:bg-slate-50/50 cursor-pointer group" onClick={() => setExpandedYear(expandedYear === row.year ? null : row.year)}>
                                                <td className="px-8 py-6 font-black text-slate-900 text-[10px]">FY {row.year}</td>
                                                <td className="px-8 py-6 text-slate-600 font-medium tracking-tight">₹{row.principal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                <td className="px-8 py-6 text-indigo-700 font-black text-[10px]">₹{row.interest.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                <td className="px-8 py-6">
                                                    <span className={`px-4 py-2 rounded-full font-black text-xs ${row.tax_expected > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'} `}>
                                                        ₹{row.tax_expected.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TOTAL TAX
                                                    </span>
                                                </td>
                                                <td className="pr-4">
                                                    {expandedYear === row.year ? <ChevronDown className="w-5 h-5 text-slate-400" /> : <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-indigo-600" />}
                                                </td>
                                            </tr>
                                            {expandedYear === row.year && (
                                                <tr className="bg-slate-50/80">
                                                    <td colSpan={5} className="px-8 py-4 border-l-4 border-indigo-500">
                                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                                            {row.investor_breakdown.map(inv => (
                                                                <div
                                                                    key={inv.name}
                                                                    className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 cursor-pointer hover:border-indigo-500 hover:shadow-md transition-all group/card relative overflow-hidden"
                                                                    onClick={() => setSelectedTaxDetails({ ...inv, year: row.year })}
                                                                >
                                                                    <div className="absolute top-0 right-0 p-2 opacity-0 group-hover/card:opacity-100 transition-opacity">
                                                                        <Calculator className="w-3 h-3 text-indigo-400" />
                                                                    </div>
                                                                    <div className="flex items-center gap-2 mb-3">
                                                                        <UserIcon className="w-4 h-4 text-indigo-600" />
                                                                        <span className="font-black text-slate-900 text-sm uppercase truncate">{inv.name}</span>
                                                                    </div>
                                                                    <div className="space-y-1">
                                                                        <div className="flex justify-between text-xs font-bold text-slate-500 uppercase">
                                                                            <span>Interest</span>
                                                                            <span className="text-slate-900">₹{inv.interest.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                                                        </div>
                                                                        <div className="flex justify-between text-xs font-black text-slate-500 uppercase mt-1 pt-1 border-t border-slate-50">
                                                                            <span>Individual Tax</span>
                                                                            <span className={inv.tax > 0 ? "text-red-600" : "text-emerald-600"}>₹{inv.tax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {activeTab === "pnl" && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                        <div className="bg-white p-6 lg:p-8 rounded-3xl border border-slate-200 shadow-lg">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                                <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col justify-center">
                                    <span className="text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1">Total Merged Invested</span>
                                    <div className="text-2xl font-black text-slate-900">₹{summaryMetrics.totalInvested.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
                                </div>
                                <div className="bg-indigo-50/30 p-6 rounded-3xl border border-indigo-100 shadow-sm flex flex-col justify-center">
                                    <span className="text-[10px] font-black uppercase text-indigo-400 tracking-widest mb-1">Total Current Value</span>
                                    <div className="text-2xl font-black text-indigo-900">₹{summaryMetrics.totalCurrentValue.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
                                </div>
                                <div className={`p-6 rounded-3xl border shadow-sm flex flex-col justify-center ${summaryMetrics.totalDailyPnl >= 0 ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100'}`}>
                                    <span className="text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1">Total Daily Gain/Loss</span>
                                    <div className={`text-2xl font-black ${summaryMetrics.totalDailyPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                        {summaryMetrics.totalDailyPnl >= 0 ? '+' : '-'}₹{Math.abs(summaryMetrics.totalDailyPnl).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-col lg:flex-row justify-between lg:items-center gap-6">
                                <div>
                                    <h4 className="text-xs font-black text-slate-900 uppercase">Aggregated Scrip Alerts</h4>
                                    <p className="text-slate-500 mt-2 leading-relaxed font-medium max-w-2xl">Equities are merged across all user codes. Monitor performance based on your loss tolerance.</p>
                                </div>
                                <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 flex flex-col gap-4 w-full lg:max-w-xs">
                                    <div className="flex items-center justify-between">
                                        <div className="flex flex-col gap-1">
                                            <label className="text-[10px] font-black uppercase text-slate-400 flex items-center gap-1.5">
                                                <Filter className="w-3 h-3" />
                                                Aggregation Filter
                                            </label>
                                            <div className="flex items-center gap-2">
                                                <span className={`text-xs font-black uppercase ${showAllMerged ? 'text-indigo-600' : 'text-slate-500'}`}>
                                                    {showAllMerged ? 'Full Portfolio' : `Loss > ${lossThreshold}%`}
                                                </span>
                                                <span className="text-[10px] font-bold text-slate-400">
                                                    ({filteredStocks.length} of {badStocks.length} scrips)
                                                </span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setShowAllMerged(!showAllMerged)}
                                            className={`px-4 py-1.5 text-[10px] font-black uppercase rounded-xl transition-all border ${showAllMerged ? 'bg-indigo-600 text-white border-indigo-600 shadow-md ring-4 ring-indigo-50' : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'}`}
                                        >
                                            {showAllMerged ? "Showing Everything" : "Filter Underperformers"}
                                        </button>
                                    </div>
                                    {!showAllMerged && (
                                        <input
                                            type="range"
                                            min="5"
                                            max="50"
                                            step="5"
                                            value={lossThreshold}
                                            onChange={(e) => setLossThreshold(parseInt(e.target.value))}
                                            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                        />
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Portfolio Alerts – search + star filter bar */}
                        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 flex flex-wrap gap-3 items-end">
                            <div className="flex-1 min-w-[200px] relative">
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Search Scrip</label>
                                <input
                                    type="text"
                                    placeholder="Symbol or operator…"
                                    value={pnlSearch}
                                    onChange={e => setPnlSearch(e.target.value)}
                                    className="w-full pl-3 pr-8 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                                />
                                {pnlSearch && <button onClick={() => setPnlSearch('')} className="absolute right-2 top-7 text-slate-400 hover:text-slate-600 text-sm">✕</button>}
                            </div>
                            <div className="flex-1 min-w-[160px]">
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">★ Star Rating</label>
                                <select
                                    value={pnlStarFilter}
                                    onChange={e => setPnlStarFilter(Number(e.target.value))}
                                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                                >
                                    <option value={0}>All Ratings</option>
                                    <option value={5}>★★★★★ Strong Buy</option>
                                    <option value={4}>★★★★☆ Buy</option>
                                    <option value={3}>★★★☆☆ Hold</option>
                                    <option value={2}>★★☆☆☆ Underperform</option>
                                    <option value={1}>★☆☆☆☆ Sell</option>
                                </select>
                            </div>
                            <div className="flex-1 min-w-[140px]">
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Sort by Stars</label>
                                <button
                                    onClick={() => setPnlSortStars(s => s === 'desc' ? 'asc' : s === 'asc' ? null : 'desc')}
                                    className={`w-full px-3 py-2 rounded-lg border text-sm font-bold transition-all flex items-center justify-center gap-1 ${pnlSortStars ? 'bg-indigo-600 text-white border-indigo-600 shadow' : 'bg-white border-slate-200 text-slate-600 hover:border-indigo-400'
                                        }`}
                                >
                                    ★ {pnlSortStars === 'desc' ? 'High → Low' : pnlSortStars === 'asc' ? 'Low → High' : 'Stars'}
                                    {pnlSortStars ? (pnlSortStars === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-40" />}
                                </button>
                            </div>
                            {(pnlSearch || pnlStarFilter > 0 || pnlSortStars) && (
                                <div className="flex items-end gap-3">
                                    <button onClick={() => { setPnlSearch(''); setPnlStarFilter(0); setPnlSortStars(null); }} className="px-3 py-2 text-xs font-bold text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all">Clear</button>
                                    <span className="text-xs text-slate-400 font-medium py-2">{filteredStocks.length} results</span>
                                </div>
                            )}
                        </div>

                        <div className="bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th onClick={() => handleSort('symbol')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors min-w-[150px]">
                                                <div className="flex items-center gap-1">
                                                    Symbol / Combined Operators
                                                    {sortConfig?.key === 'symbol' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('daily_pnl')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    Daily Gain/Loss
                                                    {sortConfig?.key === 'daily_pnl' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('total_qty')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    Qty
                                                    {sortConfig?.key === 'total_qty' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('pf_units')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    PF Units
                                                    {sortConfig?.key === 'pf_units' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('avg_buy_price')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    Avg Price
                                                    {sortConfig?.key === 'avg_buy_price' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('ltp')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    LTP
                                                    {sortConfig?.key === 'ltp' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('current_value')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    Current Value
                                                    {sortConfig?.key === 'current_value' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                            <th onClick={() => handleSort('total_loss')} className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors">
                                                <div className="flex items-center gap-1 whitespace-nowrap">
                                                    Total P&L
                                                    {sortConfig?.key === 'total_loss' ? (sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-30" />}
                                                </div>
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 italic">
                                        {filteredStocks.length === 0 ? (
                                            <tr><td colSpan={8} className="p-10 text-center text-slate-400 font-bold uppercase italic tracking-widest text-xs">No Merged scrips matching filter.</td></tr>
                                        ) : filteredStocks.map(stock => (
                                            <tr key={stock.symbol} className="hover:bg-red-50/20 group">
                                                <td className="px-3 py-2 whitespace-normal min-w-[150px]">
                                                    <div className="flex flex-col gap-0.5">
                                                        <div className="flex items-center gap-1 flex-wrap">
                                                            <div className="font-black text-slate-900 text-xs flex items-center">
                                                                {stock.symbol}
                                                                {renderStars(stock.symbol)}
                                                            </div>
                                                            <span className="bg-slate-100 text-slate-500 text-[8px] font-black px-1.5 py-0.5 rounded uppercase">{stock.instrument_type}</span>
                                                        </div>
                                                        <div className="text-[9px] font-black text-indigo-500 uppercase tracking-tighter leading-tight">Merged: {stock.operators}</div>
                                                    </div>
                                                </td>
                                                <td className="px-3 py-2 whitespace-nowrap">
                                                    <div className={`font-black text-xs ${stock.daily_pnl && stock.daily_pnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                                        {stock.daily_pnl && stock.daily_pnl >= 0 ? '+' : '-'}₹{Math.abs(stock.daily_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                                    </div>
                                                    <div className={`text-[9px] font-bold ${stock.daily_pnl_percentage && stock.daily_pnl_percentage >= 0 ? 'text-emerald-500/60' : 'text-red-500/60'}`}>
                                                        {stock.daily_change && stock.daily_change >= 0 ? '+' : '-'}{Math.abs(stock.daily_change || 0).toFixed(2)} ({stock.daily_pnl_percentage && stock.daily_pnl_percentage >= 0 ? '+' : '-'}{Math.abs(stock.daily_pnl_percentage || 0).toFixed(2)}%)
                                                    </div>
                                                </td>
                                                <td className="px-3 py-2 text-slate-600 font-bold text-xs whitespace-nowrap">{stock.total_qty}</td>
                                                <td className="px-3 py-2 whitespace-nowrap">
                                                    <span className="text-rose-600 font-bold bg-rose-50 px-1.5 py-0.5 rounded text-[9px]">
                                                        {(stock.pf_units || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-slate-600 font-medium text-xs whitespace-nowrap">₹{stock.avg_buy_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                <td className="px-3 py-2 text-indigo-700 font-bold text-xs whitespace-nowrap">₹{stock.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                <td className="px-3 py-2 text-slate-600 font-black text-xs whitespace-nowrap">₹{stock.current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                <td className="px-3 py-2 whitespace-nowrap">
                                                    <div className={`font-black text-xs ${stock.total_loss < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                                                        {stock.total_loss >= 0 ? "+" : "-"}₹{Math.abs(stock.total_loss).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                                    </div>
                                                    <div className={`text-[9px] font-bold ${stock.pnl_percentage < 0 ? 'text-red-500/60' : 'text-emerald-500/60'}`}>
                                                        {stock.pnl_percentage >= 0 ? '+' : ''}{stock.pnl_percentage.toFixed(2)}%
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === "projections" && (
                    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
                        <div className="bg-slate-900 rounded-[3rem] p-8 md:p-12 text-white shadow-2xl relative overflow-hidden">
                            <div className="absolute -right-20 -top-20 w-96 h-96 bg-indigo-500/20 blur-[100px] rounded-full"></div>
                            <div className="relative z-10 grid lg:grid-cols-2 gap-12">
                                <div>
                                    <h3 className="text-[10px] sm:text-xs font-black uppercase tracking-tighter leading-none mb-4">Strategic Portfolio <br /><span className="text-indigo-400">Growth Simulation</span></h3>

                                    <div className="grid grid-cols-2 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Equity Return (%)</label>
                                            <input type="number" value={equityReturn} onChange={e => setEquityReturn(Number(e.target.value))}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xl font-black outline-none focus:border-indigo-500 transition-colors" />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">MF Return (%)</label>
                                            <input type="number" value={mfReturn} onChange={e => setMfReturn(Number(e.target.value))}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xl font-black outline-none focus:border-indigo-500 transition-colors" />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Initial Withdrawal (₹)</label>
                                            <input type="number" value={initialWithdrawal} onChange={e => setInitialWithdrawal(Number(e.target.value))}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xl font-black outline-none focus:border-indigo-500 transition-colors" />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">FD Return (%)</label>
                                            <input type="number" value={fdReturn} onChange={e => setFdReturn(Number(e.target.value))}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xl font-black outline-none focus:border-indigo-500 transition-colors" />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Annual Step-up (%)</label>
                                            <input type="number" value={withdrawalStepUp} onChange={e => setWithdrawalStepUp(Number(e.target.value))}
                                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xl font-black outline-none focus:border-indigo-500 transition-colors" />
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-8 border border-white/10 flex flex-col justify-center">
                                    <div className="space-y-6">
                                        <div className="flex items-center gap-4">
                                            <div className="w-1.5 h-10 bg-emerald-500 rounded-full"></div>
                                            <div>
                                                <p className="text-[10px] font-black text-slate-500 uppercase">Growth Calculation</p>
                                                <p className="text-sm font-medium text-slate-300">Compound interest is applied annually on year-opening balances.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="w-1.5 h-10 bg-red-500 rounded-full"></div>
                                            <div>
                                                <p className="text-[10px] font-black text-slate-500 uppercase">Drawdown Strategy</p>
                                                <p className="text-sm font-medium text-slate-300">FDs are exhausted first, then Mutual Funds, protecting Equity for as long as possible.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
                            {simulatedProjections.map(proj => (
                                <button
                                    key={proj.year}
                                    onClick={() => setSelectedYearProj(proj)}
                                    className="bg-white text-left rounded-3xl p-6 border border-slate-200 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all group"
                                >
                                    <div className="text-indigo-600 font-black text-xs uppercase tracking-widest mb-4">YEAR {proj.year}</div>
                                    <div className="space-y-4">
                                        <div>
                                            <p className="text-xs text-slate-400 uppercase font-black">Projected Total</p>
                                            <p className="text-sm font-black text-slate-900 tracking-tighter">₹{(proj.total / 10000000).toFixed(2)} Cr</p>
                                        </div>
                                        <div className="pt-4 border-t border-slate-50 flex items-center justify-between">
                                            <div className="text-emerald-600 font-black text-sm flex items-center gap-0.5">
                                                <ArrowUpRight className="w-3 h-3" /> ₹{(proj.growth_earned / 100000).toFixed(0)}L
                                            </div>
                                            <span className="text-[10px] font-bold text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity">DETAILS &rarr;</span>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>

                        {/* Year Details Modal */}
                        {selectedYearProj && (
                            <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 backdrop-blur-md">
                                <div className="bg-white rounded-t-[2.5rem] sm:rounded-[2.5rem] shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200 animate-in slide-in-from-bottom-20 sm:slide-in-from-bottom-0 sm:zoom-in-95 duration-300">
                                    <div className="p-6 sm:p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                                        <div>
                                            <h3 className="text-[10px] font-black text-slate-900 tracking-tighter uppercase">Year {selectedYearProj.year} Breakdown</h3>
                                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">detailed calculation matrix</p>
                                        </div>
                                        <button onClick={() => setSelectedYearProj(null)} className="p-3 bg-white border border-slate-200 rounded-2xl hover:bg-slate-50 transition-colors shadow-sm font-black text-slate-400">X</button>
                                    </div>

                                    <div className="p-6 sm:p-8 space-y-6 sm:space-y-8 max-h-[80vh] overflow-y-auto">
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                            <div className="bg-indigo-50 p-5 sm:p-6 rounded-3xl border border-indigo-100">
                                                <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">Year Opening</p>
                                                <p className="text-sm sm:text-base font-black text-indigo-900">₹{((selectedYearProj.start_equity + selectedYearProj.start_mf + selectedYearProj.start_fd) / 10000000).toFixed(2)} Cr</p>
                                            </div>
                                            <div className="bg-emerald-50 p-5 sm:p-6 rounded-3xl border border-emerald-100">
                                                <p className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1">Yield Earned</p>
                                                <p className="text-sm sm:text-base font-black text-emerald-900">+ ₹{(selectedYearProj.growth_earned / 100000).toFixed(2)} L</p>
                                            </div>
                                        </div>

                                        <div className="space-y-4">
                                            <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest px-1">Asset Performance</h4>
                                            <div className="space-y-2">
                                                {[
                                                    { label: 'Equity', start: selectedYearProj.start_equity, growth: selectedYearProj.growth_equity, color: 'emerald' },
                                                    { label: 'Mutual Funds', start: selectedYearProj.start_mf, growth: selectedYearProj.growth_mf, color: 'indigo' },
                                                    { label: 'Fixed Deposits', start: selectedYearProj.start_fd, growth: selectedYearProj.growth_fd, color: 'blue' }
                                                ].map(asset => (
                                                    <div key={asset.label} className="flex items-center justify-between p-4 rounded-2xl border border-slate-100 hover:bg-slate-50 transition-colors">
                                                        <div className="flex items-center gap-3">
                                                            <div className={`w-2 h-2 rounded-full bg-${asset.color}-500`}></div>
                                                            <span className="font-bold text-slate-700">{asset.label}</span>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className="text-sm font-black text-slate-900">₹{(asset.start / 10000000).toFixed(2)} Cr</p>
                                                            <p className="text-[10px] font-bold text-emerald-600">+₹{(asset.growth / 100000).toFixed(2)} L Yield</p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="pt-6 border-t border-slate-100">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-[10px] font-black text-red-400 uppercase tracking-widest">Withdrawal Managed</p>
                                                    <p className="text-sm font-black text-red-900">- ₹{(selectedYearProj.withdrawn / 100000).toFixed(2)} L</p>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Year Closing</p>
                                                    <p className="text-base font-black text-slate-900 tracking-tighter">₹{(selectedYearProj.total / 10000000).toFixed(2)} Cr</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "dma" && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                        {/* DMA Summary Cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                            {Object.entries(dmaData.summary || {}).map(([trend, data]: [string, any]) => (
                                <div key={trend} className={`bg-white p-6 rounded-3xl border border-slate-200 shadow-sm transition-all hover:shadow-md ${data.count > 0 ? 'opacity-100' : 'opacity-50'}`}>
                                    <div className="flex justify-between items-start mb-4">
                                        <span className={`px-2 py-1 rounded-full text-[9px] font-black uppercase tracking-wider 
                                            ${trend === 'bullish' ? 'bg-emerald-100 text-emerald-700' :
                                                trend === 'bearish' ? 'bg-red-100 text-red-700' :
                                                    trend === 'long term bullish, near term bearish' ? 'bg-indigo-100 text-indigo-700' :
                                                        trend === 'near term bullish, long term bearish' ? 'bg-amber-100 text-amber-700' :
                                                            'bg-slate-100 text-slate-700'}`}>
                                            {trend}
                                        </span>
                                        <div className="text-[10px] font-black text-slate-400">{data.percentage}%</div>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="text-2xl font-black text-slate-900 leading-none">{data.count} <span className="text-[10px] text-slate-400 font-bold uppercase">Stocks</span></div>
                                        <div className="text-sm font-bold text-slate-600">
                                            ₹{data.value >= 10000000
                                                ? `${(data.value / 10000000).toFixed(2)} Cr`
                                                : `${(data.value / 100000).toFixed(2)} L`}
                                        </div>
                                    </div>
                                    <div className="mt-4 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${trend === 'bullish' ? 'bg-emerald-500' : trend === 'bearish' ? 'bg-red-500' : trend === 'near term bullish, long term bearish' ? 'bg-amber-500' : 'bg-indigo-500'}`}
                                            style={{ width: `${data.percentage}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="bg-white p-6 lg:p-8 rounded-3xl border border-slate-200 shadow-lg">
                            <div className="flex flex-col lg:flex-row justify-between lg:items-center gap-6">
                                <div>
                                    <h4 className="text-xs font-black text-slate-900 uppercase">Technical Indicators</h4>
                                    <p className="text-slate-500 mt-2 leading-relaxed font-medium max-w-2xl">
                                        Stocks trading above 50-day and 200-day Moving Averages often indicate bullish momentum.
                                    </p>
                                </div>
                                <div className="flex flex-col sm:flex-row gap-4">
                                    <div className="bg-slate-50 px-4 py-2 rounded-2xl border border-slate-200 flex items-center gap-2">
                                        <label className="text-[10px] font-black uppercase text-slate-500 whitespace-nowrap">50-DMA</label>
                                        <select
                                            value={dma50Filter}
                                            onChange={(e) => setDma50Filter(e.target.value as any)}
                                            className="bg-transparent text-xs font-bold text-slate-900 outline-none"
                                        >
                                            <option value="all">Every Status</option>
                                            <option value="Above">Above</option>
                                            <option value="Below">Below</option>
                                        </select>
                                    </div>
                                    <div className="bg-slate-50 px-4 py-2 rounded-2xl border border-slate-200 flex items-center gap-2">
                                        <label className="text-[10px] font-black uppercase text-slate-500 whitespace-nowrap">200-DMA</label>
                                        <select
                                            value={dma200Filter}
                                            onChange={(e) => setDma200Filter(e.target.value as any)}
                                            className="bg-transparent text-xs font-bold text-slate-900 outline-none"
                                        >
                                            <option value="all">Every Status</option>
                                            <option value="Above">Above</option>
                                            <option value="Below">Below</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Technical Signals – search + star filter bar */}
                        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 flex flex-wrap gap-3 items-end">
                            <div className="flex-1 min-w-[200px] relative">
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Search Symbol</label>
                                <input
                                    type="text"
                                    placeholder="Type a symbol…"
                                    value={dmaSearch}
                                    onChange={e => setDmaSearch(e.target.value)}
                                    className="w-full pl-3 pr-8 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                                />
                                {dmaSearch && <button onClick={() => setDmaSearch('')} className="absolute right-2 top-7 text-slate-400 hover:text-slate-600 text-sm">✕</button>}
                            </div>
                            <div className="flex-1 min-w-[160px]">
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">★ Star Rating</label>
                                <select
                                    value={dmaStarFilter}
                                    onChange={e => setDmaStarFilter(Number(e.target.value))}
                                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                                >
                                    <option value={0}>All Ratings</option>
                                    <option value={5}>★★★★★ Strong Buy</option>
                                    <option value={4}>★★★★☆ Buy</option>
                                    <option value={3}>★★★☆☆ Hold</option>
                                    <option value={2}>★★☆☆☆ Underperform</option>
                                    <option value={1}>★☆☆☆☆ Sell</option>
                                </select>
                            </div>
                            <div className="flex-1 min-w-[140px]">
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Sort by Stars</label>
                                <button
                                    onClick={() => setDmaSortStars(s => s === 'desc' ? 'asc' : s === 'asc' ? null : 'desc')}
                                    className={`w-full px-3 py-2 rounded-lg border text-sm font-bold transition-all flex items-center justify-center gap-1 ${dmaSortStars ? 'bg-indigo-600 text-white border-indigo-600 shadow' : 'bg-white border-slate-200 text-slate-600 hover:border-indigo-400'
                                        }`}
                                >
                                    ★ {dmaSortStars === 'desc' ? 'High → Low' : dmaSortStars === 'asc' ? 'Low → High' : 'Stars'}
                                    {dmaSortStars ? (dmaSortStars === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />) : <ArrowUpDown className="w-3 h-3 opacity-40" />}
                                </button>
                            </div>
                            {(dmaSearch || dmaStarFilter > 0 || dmaSortStars) && (
                                <div className="flex items-end gap-3">
                                    <button onClick={() => { setDmaSearch(''); setDmaStarFilter(0); setDmaSortStars(null); }} className="px-3 py-2 text-xs font-bold text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all">Clear</button>
                                    <span className="text-xs text-slate-400 font-medium py-2">{filteredDmaStocks.length} results</span>
                                </div>
                            )}
                        </div>

                        <div className="bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left whitespace-nowrap">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Symbol</th>
                                            <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Current Price</th>
                                            <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">50 DMA</th>
                                            <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">200 DMA</th>
                                            <th className="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Signal</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100">
                                        {filteredDmaStocks.length === 0 ? (
                                            <tr><td colSpan={5} className="p-20 text-center text-slate-400 font-bold uppercase italic tracking-widest">No stocks match parameters.</td></tr>
                                        ) : filteredDmaStocks.map(stock => (
                                            <tr key={stock.symbol} className="hover:bg-slate-50/50 group">
                                                <td className="px-8 py-6">
                                                    <div className="font-black text-slate-900 text-xs flex items-center">
                                                        {stock.symbol}
                                                        {renderStars(stock.symbol)}
                                                    </div>
                                                </td>
                                                <td className="px-8 py-6 text-slate-900 font-bold">₹{stock.cmp.toLocaleString('en-IN')}</td>
                                                <td className="px-8 py-6">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-slate-600 font-medium">₹{stock.dma_50.toLocaleString('en-IN')}</span>
                                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase ${stock.dma_50_status === 'Above' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                                                            {stock.dma_50_status}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-8 py-6">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-slate-600 font-medium">₹{stock.dma_200.toLocaleString('en-IN')}</span>
                                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase ${stock.dma_200_status === 'Above' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                                                            {stock.dma_200_status}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-8 py-6">
                                                    <span className={`px-3 py-1 rounded-full text-[9px] font-black tracking-wide
                                                        ${stock.signal === 'bullish' ? 'bg-emerald-100 text-emerald-700' :
                                                            stock.signal === 'bearish' ? 'bg-red-100 text-red-700' :
                                                                stock.signal === 'long term bullish, near term bearish' ? 'bg-indigo-100 text-indigo-700' :
                                                                    stock.signal === 'near term bullish, long term bearish' ? 'bg-amber-100 text-amber-700' :
                                                                        'bg-slate-100 text-slate-700'}`}>
                                                        {stock.signal}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Tax Computation Modal */}
            {
                selectedTaxDetails && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md">
                        <div className="bg-white rounded-[2.5rem] shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-300">
                            <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                                        <Scale className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <h3 className="text-[10px] font-black text-slate-900 tracking-tighter uppercase">{selectedTaxDetails.name}</h3>
                                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">FY {selectedTaxDetails.year} Tax Computation (Budget 2025)</p>
                                    </div>
                                </div>
                                <button onClick={() => {
                                    setSelectedTaxDetails(null);
                                    setExtraDividend(0);
                                    setExtraBusiness(0);
                                    setExtraOther(0);
                                }} className="p-3 bg-white border border-slate-200 rounded-2xl hover:bg-slate-50 transition-colors shadow-sm font-black text-slate-400">X</button>
                            </div>

                            <div className="p-8 overflow-y-auto max-h-[85vh]">
                                {/* Combined Total Income Section */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                    <div className="bg-slate-900 rounded-3xl p-6 text-white relative overflow-hidden flex flex-col justify-center">
                                        <div className="absolute right-0 top-0 p-4 opacity-5">
                                            <Calculator className="w-20 h-20" />
                                        </div>
                                        <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">Total combined Income</p>
                                        <p className="text-base font-black mb-4">₹{(selectedTaxDetails.interest + extraDividend + extraBusiness + extraOther).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                        <div className="pt-4 border-t border-white/10 flex justify-between">
                                            <div>
                                                <p className="text-[10px] font-black text-slate-500 uppercase">Interest</p>
                                                <p className="text-xs font-bold">₹{selectedTaxDetails.interest.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-[10px] font-black text-slate-500 uppercase">Other</p>
                                                <p className="text-xs font-bold">₹{(extraDividend + extraBusiness + extraOther).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Other Income Simulation</h4>
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="space-y-1">
                                                <label className="text-[10px] font-bold text-slate-500 uppercase px-1">Dividend</label>
                                                <input type="number" value={extraDividend || ""} onChange={e => setExtraDividend(Number(e.target.value))}
                                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="0" />
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-[10px] font-bold text-slate-500 uppercase px-1">Business</label>
                                                <input type="number" value={extraBusiness || ""} onChange={e => setExtraBusiness(Number(e.target.value))}
                                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="0" />
                                            </div>
                                            <div className="col-span-2 space-y-1">
                                                <label className="text-[10px] font-bold text-slate-500 uppercase px-1">Capital Gain / Others (Slab Taxed)</label>
                                                <input type="number" value={extraOther || ""} onChange={e => setExtraOther(Number(e.target.value))}
                                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="0" />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                                    <div className="bg-indigo-50 p-5 rounded-3xl border border-indigo-100">
                                        <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">Est. Tax Liability</p>
                                        {(() => {
                                            const totalInc = selectedTaxDetails.interest + extraDividend + extraBusiness + extraOther;
                                            let tax = 0;
                                            if (totalInc > 1200000) {
                                                const runTax = (minV: number, maxV: number, rate: number) => {
                                                    if (totalInc > minV) return Math.min(totalInc - minV, maxV - minV) * (rate / 100);
                                                    return 0;
                                                };
                                                tax += runTax(400000, 800000, 5);
                                                tax += runTax(800000, 1200000, 10);
                                                tax += runTax(1200000, 1600000, 15);
                                                tax += runTax(1600000, 2000000, 20);
                                                tax += runTax(2000000, 2400000, 25);
                                                if (totalInc > 2400000) tax += (totalInc - 2400000) * 0.30;
                                                tax = tax * 1.04;
                                            }
                                            return (
                                                <>
                                                    <p className={`text-sm sm:text-base font-black ${tax > 0 ? 'text-red-900' : 'text-emerald-900'} break-all`}>₹{tax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                                    <p className="text-[10px] font-bold text-slate-400 mt-1 uppercase">Incl. 4% Cess</p>
                                                </>
                                            );
                                        })()}
                                    </div>
                                    <div className="bg-emerald-50 p-5 rounded-3xl border border-emerald-100">
                                        <p className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1">Effective Rate</p>
                                        {(() => {
                                            const totalInc = selectedTaxDetails.interest + extraDividend + extraBusiness + extraOther;
                                            let baseTax = 0;
                                            if (totalInc > 1200000) {
                                                const runTax = (minV: number, maxV: number, rate: number) => {
                                                    if (totalInc > minV) return Math.min(totalInc - minV, maxV - minV) * (rate / 100);
                                                    return 0;
                                                };
                                                baseTax += runTax(400000, 800000, 5);
                                                baseTax += runTax(800000, 1200000, 10);
                                                baseTax += runTax(1200000, 1600000, 15);
                                                baseTax += runTax(1600000, 2000000, 20);
                                                baseTax += runTax(2000000, 2400000, 25);
                                                if (totalInc > 2400000) baseTax += (totalInc - 2400000) * 0.30;
                                            }
                                            const finalTax = baseTax * 1.04;
                                            return (
                                                <>
                                                    <p className="text-sm sm:text-base font-black text-slate-900">{totalInc > 0 ? ((finalTax / totalInc) * 100).toFixed(2) : "0.00"}%</p>
                                                    <p className="text-[10px] font-bold text-slate-400 mt-1 uppercase">Avg. Tax per Rupee</p>
                                                </>
                                            );
                                        })()}
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest px-1 flex items-center gap-2">
                                        <Zap className="w-3 h-3 text-amber-500" /> Computation Working
                                    </h4>
                                    <div className="border border-slate-100 rounded-3xl overflow-hidden font-medium">
                                        <table className="w-full text-sm">
                                            <thead className="bg-slate-50">
                                                <tr>
                                                    <th className="px-6 py-3 text-left text-[10px] font-black text-slate-400 uppercase">Income slab</th>
                                                    <th className="px-6 py-3 text-left text-[10px] font-black text-slate-400 uppercase text-right">Amount</th>
                                                    <th className="px-6 py-3 text-left text-[10px] font-black text-slate-400 uppercase text-center">Rate</th>
                                                    <th className="px-6 py-3 text-left text-[10px] font-black text-slate-400 uppercase text-right">Tax</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-50">
                                                {(() => {
                                                    const inc = selectedTaxDetails.interest + extraDividend + extraBusiness + extraOther;
                                                    if (inc <= 1200000) {
                                                        return (
                                                            <tr>
                                                                <td className="px-6 py-4 text-slate-600 font-bold italic">Up to 12,00,000 (Section 87A)</td>
                                                                <td className="px-6 py-4 text-right text-slate-900 font-black">₹{inc.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                <td className="px-6 py-4 text-center text-emerald-600 font-black">0%</td>
                                                                <td className="px-6 py-4 text-right text-emerald-600 font-black">₹0.00</td>
                                                            </tr>
                                                        );
                                                    }
                                                    const rows = [];
                                                    // Slab calculation logic identical to backend
                                                    const runSlab = (minVal: number, maxVal: number, rate: number, label: string) => {
                                                        if (inc > minVal) {
                                                            const slabInc = Math.min(inc - minVal, maxVal - minVal);
                                                            const slabTax = slabInc * (rate / 100);
                                                            rows.push(
                                                                <tr key={label}>
                                                                    <td className="px-6 py-4 text-slate-600">{label}</td>
                                                                    <td className="px-6 py-4 text-right text-slate-900 font-bold">₹{slabInc.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                    <td className="px-6 py-4 text-center text-slate-400 font-bold">{rate}%</td>
                                                                    <td className="px-6 py-4 text-right text-slate-900 font-black">₹{slabTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                </tr>
                                                            );
                                                            return slabTax;
                                                        }
                                                        return 0;
                                                    };

                                                    let baseTax = 0;
                                                    baseTax += runSlab(0, 400000, 0, "0 - 4,00,000");
                                                    baseTax += runSlab(400000, 800000, 5, "4,00,001 - 8,00,000");
                                                    baseTax += runSlab(800000, 1200000, 10, "8,00,001 - 12,00,000");
                                                    baseTax += runSlab(1200000, 1600000, 15, "12,00,001 - 16,00,000");
                                                    baseTax += runSlab(1600000, 2000000, 20, "16,00,001 - 20,00,000");
                                                    baseTax += runSlab(2000000, 2400000, 25, "20,00,001 - 24,00,000");

                                                    if (inc > 2400000) {
                                                        const slabInc = inc - 2400000;
                                                        const slabTax = slabInc * 0.30;
                                                        baseTax += slabTax;
                                                        rows.push(
                                                            <tr key="above24">
                                                                <td className="px-6 py-4 text-slate-600">Above 24,00,000</td>
                                                                <td className="px-6 py-4 text-right text-slate-900 font-bold">₹{slabInc.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                <td className="px-6 py-4 text-center text-slate-400 font-bold">30%</td>
                                                                <td className="px-6 py-4 text-right text-slate-900 font-black">₹{slabTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                            </tr>
                                                        );
                                                    }

                                                    rows.push(
                                                        <tr key="subtotal" className="bg-slate-50/50">
                                                            <td colSpan={3} className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase">Sub-Total Tax</td>
                                                            <td className="px-6 py-4 text-right text-slate-900 font-black">₹{baseTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                        </tr>
                                                    );
                                                    rows.push(
                                                        <tr key="cess" className="bg-slate-50/50 border-t border-slate-100">
                                                            <td colSpan={3} className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase">Health & Education Cess (4%)</td>
                                                            <td className="px-6 py-4 text-right text-slate-900 font-black">₹{(baseTax * 0.04).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                        </tr>
                                                    );
                                                    return rows;
                                                })()}
                                            </tbody>
                                        </table>
                                    </div>
                                    <div className="flex items-center gap-3 p-4 bg-amber-50 rounded-2xl border border-amber-100 mb-8">
                                        <div className="p-2 bg-amber-200 rounded-lg text-amber-700">
                                            <Info className="w-4 h-4" />
                                        </div>
                                        <p className="text-xs text-amber-800 leading-relaxed font-medium">
                                            This calculation assumes the Individual has no other income for the year. Tax is computed based on the <span className="font-bold">Latest Budget 2025 Slabs</span> (AY 2026-27).
                                        </p>
                                    </div>

                                    {/* Detailed FD List for this Investor/Year */}
                                    <div className="space-y-4">
                                        <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest px-1">Source Deposits ({selectedTaxDetails.fds.length})</h4>
                                        <div className="border border-slate-100 rounded-3xl overflow-hidden shadow-sm">
                                            <table className="w-full text-left text-xs">
                                                <thead className="bg-slate-50 text-slate-400 font-black uppercase tracking-widest">
                                                    <tr>
                                                        <th className="px-6 py-4">Bank / Code</th>
                                                        <th className="px-6 py-4 text-right">Principal</th>
                                                        <th className="px-6 py-4 text-center">Rate (%)</th>
                                                        <th className="px-6 py-4 text-center">Start Date</th>
                                                        <th className="px-6 py-4 text-right">FY Interest</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-50">
                                                    {selectedTaxDetails.fds.map((fd: any, i: number) => (
                                                        <tr key={i} className="hover:bg-slate-50 transition-colors">
                                                            <td className="px-6 py-4">
                                                                <div className="font-black text-slate-900">{fd.bank_name}</div>
                                                                <div className="text-[10px] text-indigo-500 font-bold">{fd.fd_code}</div>
                                                            </td>
                                                            <td className="px-6 py-4 text-right font-medium">₹{fd.principal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                            <td className="px-6 py-4 text-center font-bold text-slate-600">{Number(fd.interest_rate).toFixed(2)}%</td>
                                                            <td className="px-6 py-4 text-center text-slate-500 font-medium">{fd.start_date}</td>
                                                            <td className="px-6 py-4 text-right font-black text-indigo-600">₹{fd.interest_earned.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
}
