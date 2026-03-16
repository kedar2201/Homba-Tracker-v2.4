import { useState, useEffect, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { Plus, ChevronDown, Trash2, X, Edit, Download, RefreshCw, Search, TrendingUp } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../components/ui/data-table";
import api from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";

type MutualFund = {
    id: number;
    scheme_name: string;
    depositor_name?: string;
    depositor_code?: string;
    isin?: string;
    units: number;
    invested_amount: number;
    transaction_date: string;
    current_nav?: number;
    current_value?: number;
    pnl?: number;
    pnl_percentage?: number;
    holder?: string;
    amc_name?: string;
    amfi_code?: string;
    interest_rate?: number;
    p_buy_units?: number;
    p_sell_units?: number;
};

const HOLDER_DISPLAY_MAP: Record<string, string> = {
    "K": "Kedar",
    "M": "Manisha",
    "S": "Saloni",
    "H": "HUF",
    "KEDAR": "Kedar",
    "MANISHA": "Manisha",
    "SALONI": "Saloni",
    "HUF": "HUF"
};

const getDisplayName = (name: string) => HOLDER_DISPLAY_MAP[name.toUpperCase()] || name;

export default function MutualFundsPage() {
    const location = useLocation();
    const query = new URLSearchParams(location.search);
    const groupBy = query.get("group"); // 'depositor' or 'holder'

    const status = query.get("status") || "ACTIVE";

    const [data, setData] = useState<MutualFund[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedHolder, setSelectedHolder] = useState<string>("All");
    const [selectedDepositor, setSelectedDepositor] = useState<string>("All");

    // Modal State
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isSellModalOpen, setIsSellModalOpen] = useState(false);
    const [sellingMF, setSellingMF] = useState<MutualFund | null>(null);
    const [sellForm, setSellForm] = useState({
        sell_nav: "",
        sell_date: new Date().toISOString().split('T')[0],
        units: ""
    });

    const [editingMF, setEditingMF] = useState<MutualFund | null>(null);
    const [newMF, setNewMF] = useState({
        scheme_name: "",
        units: "",
        invested_amount: "",
        transaction_date: new Date().toISOString().split('T')[0],
        holder: "Portfolio",
        depositor_name: "",
        depositor_code: "",
        isin: "",
        amc_name: "",
        amfi_code: ""
    });

    const refreshData = () => {
        setLoading(true);
        api.get(`/mutual-funds/?status=${status}`)
            .then(res => {
                // Filter out SGBs / Bonds
                const filteredData = res.data.filter((m: any) =>
                    !(m.interest_rate > 0 || m.scheme_name.toLowerCase().includes("sgb"))
                );
                setData(filteredData);
                setLastUpdated(new Date());
            })
            .catch(err => console.error(err))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        refreshData();
    }, [status]);

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to PERMANENTLY delete this record? Use 'Sell' to mark it as redeemed instead.")) return;
        try {
            await api.delete(`/mutual-funds/${id}`);
            setData(prev => prev.filter(item => item.id !== id));
        } catch (err) {
            console.error(err);
            alert("Failed to delete fund");
        }
    };

    const handleSellInitiate = (mf: MutualFund) => {
        setSellingMF(mf);
        setSellForm({
            sell_nav: (mf.current_nav || 0).toString(),
            sell_date: new Date().toISOString().split('T')[0],
            units: mf.units.toString()
        });
        setIsSellModalOpen(true);
    };

    const handleSellSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!sellingMF) return;
        try {
            await api.post(`/mutual-funds/${sellingMF.id}/sell`, null, {
                params: {
                    sell_nav: Number(sellForm.sell_nav),
                    sell_date: sellForm.sell_date,
                    units: Number(sellForm.units)
                }
            });
            setIsSellModalOpen(false);
            setSellingMF(null);
            refreshData();
        } catch (err) {
            console.error(err);
            alert("Failed to mark as sold");
        }
    };

    const handleReactivate = async (id: number) => {
        if (!confirm("Reactivate this sold fund?")) return;
        try {
            await api.post(`/mutual-funds/${id}/reactivate`);
            refreshData();
        } catch (err) {
            console.error(err);
            alert("Failed to reactivate");
        }
    };

    const handleEdit = (mf: MutualFund) => {
        // Ensure date is in YYYY-MM-DD format for the HTML5 date input
        const cleanMF = { ...mf };
        if (cleanMF.transaction_date) {
            cleanMF.transaction_date = cleanMF.transaction_date.split('T')[0];
        }
        setEditingMF(cleanMF);
        setIsEditModalOpen(true);
    };

    const handleEditSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingMF) return;
        try {
            await api.put(`/mutual-funds/${editingMF.id}`, {
                scheme_name: editingMF.scheme_name,
                units: editingMF.units,
                invested_amount: editingMF.invested_amount,
                transaction_date: editingMF.transaction_date,
                holder: editingMF.holder,
                depositor_name: editingMF.depositor_name,
                depositor_code: editingMF.depositor_code,
                isin: editingMF.isin,
                amc_name: editingMF.amc_name,
                amfi_code: editingMF.amfi_code
            });
            setIsEditModalOpen(false);
            setEditingMF(null);
            refreshData();
        } catch (err) {
            console.error(err);
            alert("Failed to update fund");
        }
    };

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        const exportData = data.map(item => ({
            'Scheme Name': item.scheme_name,
            'Depositor': item.depositor_name || '-',
            'Units': item.units,
            'Invested Amount': item.invested_amount,
            'Current Value': item.current_value,
            'P&L': item.pnl,
            'P&L %': item.pnl_percentage,
            'PF Units': item.p_buy_units,
            'Holder': item.holder || '-'
        }));

        if (format === 'pdf') {
            exportToPDF(exportData, ['Scheme Name', 'Depositor', 'Units', 'PF Units', 'Invested Amount', 'Current Value', 'P&L', 'P&L %', 'Holder'], 'Mutual Funds Portfolio');
        } else if (format === 'excel') {
            exportToExcel(exportData, 'Mutual_Funds_Portfolio');
        } else {
            exportToCSV(exportData, 'Mutual_Funds_Portfolio');
        }
    };

    const handleAddSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post("/mutual-funds/", {
                ...newMF,
                units: Number(newMF.units),
                invested_amount: Number(newMF.invested_amount),
            });
            setIsAddModalOpen(false);
            refreshData();
            setNewMF({
                scheme_name: "",
                units: "",
                invested_amount: "",
                transaction_date: new Date().toISOString().split('T')[0],
                holder: "Portfolio",
                depositor_name: "",
                depositor_code: "",
                isin: "",
                amc_name: "",
                amfi_code: ""
            });
        } catch (err) {
            console.error(err);
            alert("Failed to create entry");
        }
    };

    // Extract unique holders and depositors for filter dropdowns
    const uniqueHolders = useMemo(() => {
        const holders = new Set<string>();
        data.forEach(item => {
            if (item.holder) holders.add(getDisplayName(item.holder));
        });
        return Array.from(holders).sort();
    }, [data]);

    const uniqueDepositors = useMemo(() => {
        const depositors = new Set<string>();
        data.forEach(item => {
            if (item.depositor_name) depositors.add(item.depositor_name);
        });
        return Array.from(depositors).sort();
    }, [data]);

    // Filter data based on search term, holder, and depositor
    const filteredData = useMemo(() => {
        let filtered = data;

        // Apply search filter
        if (searchTerm.trim()) {
            const term = searchTerm.toLowerCase();
            filtered = filtered.filter(item =>
                item.scheme_name.toLowerCase().includes(term) ||
                (item.depositor_name && item.depositor_name.toLowerCase().includes(term)) ||
                (item.holder && item.holder.toLowerCase().includes(term)) ||
                (item.amc_name && item.amc_name.toLowerCase().includes(term))
            );
        }

        // Apply holder filter
        if (selectedHolder !== "All") {
            filtered = filtered.filter(item =>
                getDisplayName(item.holder || "") === selectedHolder
            );
        }

        // Apply depositor filter
        if (selectedDepositor !== "All") {
            filtered = filtered.filter(item => item.depositor_name === selectedDepositor);
        }

        return filtered;
    }, [data, searchTerm, selectedHolder, selectedDepositor]);

    // Totals Calculation (Same as before)
    const mfTotals = useMemo(() => {
        let current = 0; let invested = 0; let accruedInterest = 0;
        filteredData.forEach(item => {
            current += (item.current_value || 0);
            invested += (item.invested_amount || 0);
            if (item.interest_rate && item.interest_rate > 0) {
                const years = (new Date().getTime() - new Date(item.transaction_date).getTime()) / (1000 * 60 * 60 * 24 * 365.25);
                accruedInterest += item.invested_amount * (item.interest_rate / 100) * (years > 0 ? years : 0);
            }
        });
        const pnl = current - invested;
        const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;

        let units = 0;
        let portfolioUnits = 0;
        filteredData.forEach(item => {
            units += (item.units || 0);
            // Defensive check for portfolio units
            const buyUnits = item.p_buy_units !== undefined && item.p_buy_units !== null ? item.p_buy_units : 0;
            const sellUnits = item.p_sell_units !== undefined && item.p_sell_units !== null ? item.p_sell_units : 0;
            portfolioUnits += (buyUnits - sellUnits);
        });

        return { current, invested, pnl, pnlPct, accruedInterest, units, portfolioUnits };
    }, [filteredData]);

    // Grouping Logic (Same as before)
    const groupedData = useMemo(() => {
        if (!groupBy) return null;
        const groups: Record<string, { total: number, pnl: number, invested: number, items: MutualFund[] }> = {};
        filteredData.forEach(item => {
            let rawKey = groupBy === 'holder' ? (item.holder || item.depositor_code || "UNKNOWN") : (item.depositor_name || item.depositor_code || "Unknown");
            const key = getDisplayName(rawKey);
            if (!groups[key]) groups[key] = { total: 0, pnl: 0, invested: 0, items: [] };
            groups[key].items.push(item);
            groups[key].total += item.current_value || 0;
            groups[key].pnl += item.pnl || 0;
            groups[key].invested += item.invested_amount || 0;
        });
        return Object.entries(groups).sort((a, b) => b[1].total - a[1].total);
    }, [filteredData, groupBy]);

    const columns: ColumnDef<MutualFund>[] = [
        {
            accessorKey: "depositor_code",
            header: "Dep.",
            cell: ({ row }) => (
                <span className="font-extrabold text-slate-700">
                    {row.original.depositor_code && row.original.depositor_code !== "0" ? row.original.depositor_code : "-"}
                </span>
            )
        },
        {
            accessorKey: "scheme_name",
            header: "Scheme Name",
            cell: ({ row }) => {
                const sName = row.original.scheme_name;
                const isGold = row.original.interest_rate && row.original.interest_rate > 0;
                const displayName = (!sName || sName === "0") ? (isGold ? "Sovereign Gold Bond" : "Investment Portfolio Fund") : sName;
                return (
                    <div className="flex flex-col">
                        <span className="font-bold text-slate-900 leading-tight">
                            {displayName}
                        </span>
                        {status === "SOLD" && (row.original as any).sell_date && (
                            <span className="text-[10px] font-black text-rose-500 uppercase mt-0.5">
                                Redeemed on {(row.original as any).sell_date}
                            </span>
                        )}
                    </div>
                );
            }
        },
        {
            accessorKey: "units",
            header: "Units/Qty",
            cell: ({ row }) => <span className="font-semibold text-slate-800">{row.original.units.toLocaleString('en-IN', { maximumFractionDigits: 4 })}</span>
        },
        {
            accessorKey: "p_buy_units",
            header: "PF Units",
            cell: ({ row }) => (
                <span className="text-rose-600 font-bold bg-rose-50 px-2 py-0.5 rounded text-[10px]">
                    {(row.original.p_buy_units || 0).toLocaleString('en-IN', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}
                </span>
            )
        },
        {
            accessorKey: "invested_amount",
            header: "Invested Amount",
            cell: ({ row }) => <span className="font-semibold text-slate-800">₹{row.original.invested_amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        },
        {
            accessorKey: "current_nav",
            header: status === "SOLD" ? "Exit NAV" : "Current NAV",
            cell: ({ row }) => {
                const nav = status === "SOLD" ? (row.original as any).sell_nav : row.original.current_nav;
                return <span className={`font-bold ${status === "SOLD" ? "text-indigo-600" : "text-slate-900"}`}>
                    ₹{(nav || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                </span>
            }
        },
        {
            accessorKey: "current_value",
            header: status === "SOLD" ? "Redeemed Value" : "Current Value",
            cell: ({ row }) => {
                const val = status === "SOLD"
                    ? ((row.original as any).sell_nav * row.original.units)
                    : (row.original.current_value || 0);
                return <span className="font-black text-slate-900">₹{val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            }
        },
        {
            accessorKey: "pnl",
            header: "P&L",
            cell: ({ row }) => {
                let pnl = row.original.pnl || 0;
                let pnl_pct = row.original.pnl_percentage || 0;

                if (status === "SOLD") {
                    const sellVal = (row.original as any).sell_nav * row.original.units;
                    const buyVal = row.original.invested_amount;
                    pnl = sellVal - buyVal;
                    pnl_pct = buyVal > 0 ? (pnl / buyVal) * 100 : 0;
                }

                return (
                    <div className={`font-bold ${pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {pnl >= 0 ? '+' : ''}₹{Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        <div className="text-[10px] opacity-80">{pnl_pct.toFixed(2)}%</div>
                    </div>
                );
            }
        },
        {
            id: "actions",
            cell: ({ row }) => (
                <div className="flex gap-2">
                    {status === "ACTIVE" ? (
                        <>
                            <button
                                onClick={() => handleEdit(row.original)}
                                className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"
                                title="Edit Record"
                            >
                                <Edit className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => handleSellInitiate(row.original)}
                                className="p-2 hover:bg-red-50 transition-colors rounded-lg flex items-center justify-center min-w-[32px]"
                                title="Redeem Fund"
                            >
                                <span className="text-red-600 font-black text-sm">S</span>
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={() => handleReactivate(row.original.id)}
                            className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"
                            title="Undo Redemption"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    )}
                    <button
                        onClick={() => handleDelete(row.original.id)}
                        className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                        title="Permanently Delete"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            )
        }
    ];

    if (loading) return (
        <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div>
                    <h2 className="text-base sm:text-3xl lg:text-4xl font-black tracking-tight text-slate-900 uppercase">
                        {status === "SOLD" ? "Sold Funds" : "Mutual Funds"}
                    </h2>
                    <p className="text-slate-500 text-[10px] sm:text-sm lg:text-base">
                        {groupBy ? `Drill down by ${groupBy}` : "Detailed list of all mutual fund holdings"}
                    </p>
                    {lastUpdated && (
                        <p className="text-slate-400 text-xs mt-2">
                            Last updated: {lastUpdated.toLocaleTimeString('en-IN')} on {lastUpdated.toLocaleDateString('en-IN')}
                        </p>
                    )}
                </div>
                <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                    <button
                        onClick={refreshData}
                        disabled={loading}
                        className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-amber-500 text-white px-4 py-2 rounded-xl hover:bg-amber-600 transition-all font-bold text-xs shadow-sm uppercase disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        <span>Refresh</span>
                    </button>
                    <div className="flex w-full sm:w-auto gap-2">
                        <button onClick={() => handleExport('pdf')} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-red-600 text-white px-3 py-2 rounded-xl hover:bg-red-700 transition-all font-bold text-[10px] shadow-sm uppercase">
                            <Download className="w-3 h-3" /> PDF
                        </button>
                        <button onClick={() => handleExport('excel')} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-green-600 text-white px-3 py-2 rounded-xl hover:bg-green-700 transition-all font-bold text-[10px] shadow-sm uppercase">
                            <Download className="w-3 h-3" /> Excel
                        </button>
                        <button onClick={() => handleExport('csv')} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-blue-600 text-white px-3 py-2 rounded-xl hover:bg-blue-700 transition-all font-bold text-[10px] shadow-sm uppercase">
                            <Download className="w-3 h-3" /> CSV
                        </button>
                    </div>
                    <div className="flex w-full sm:w-auto gap-2">
                        <button
                            onClick={() => setIsAddModalOpen(true)}
                            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-white text-indigo-600 border border-indigo-200 px-4 py-2 rounded-xl hover:bg-indigo-50 transition-all font-bold text-xs shadow-sm uppercase"
                        >
                            <Plus className="w-4 h-4" />
                            <span>Add</span>
                        </button>
                        <Link
                            to="/mutual-funds/upload"
                            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl hover:bg-indigo-700 transition-all font-bold text-xs shadow-sm uppercase"
                        >
                            <span>Import</span>
                        </Link>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-sm border border-slate-200 flex flex-col justify-center">
                    <p className="text-slate-400 text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-0.5">Total Value</p>
                    <h3 className="text-sm sm:text-lg lg:text-xl font-black text-indigo-600">₹{mfTotals.current.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
                <div className="bg-white rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-sm border border-slate-200 flex flex-col justify-center">
                    <p className="text-slate-400 text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-0.5">Total Invested</p>
                    <h3 className="text-sm sm:text-lg lg:text-xl font-black text-slate-900">₹{mfTotals.invested.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
                <div className="bg-white rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-sm border border-slate-200 flex flex-col justify-center">
                    <p className="text-slate-400 text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-0.5">Capital P&L</p>
                    <div className="flex items-center gap-2">
                        <h3 className={`text-sm sm:text-lg lg:text-xl font-black ${mfTotals.pnl >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                            {mfTotals.pnl >= 0 ? '+' : ''}₹{Math.abs(mfTotals.pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </h3>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${mfTotals.pnl >= 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                            {mfTotals.pnlPct.toFixed(2)}%
                        </span>
                    </div>
                </div>
                <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-lg text-white border border-indigo-500/20 flex flex-col justify-between">
                    <div className="flex justify-between items-start mb-0.5">
                        <p className="text-indigo-100 text-[8px] sm:text-[9px] font-bold uppercase tracking-widest">Portfolio MF NAV</p>
                        <TrendingUp className="text-indigo-300 w-3 h-3" />
                    </div>
                    <div className="flex items-baseline gap-1.5">
                        <h3 className="text-sm sm:text-lg lg:text-xl font-black">
                            {mfTotals.current > 0 && mfTotals.portfolioUnits > 0
                                ? (mfTotals.current / mfTotals.portfolioUnits).toFixed(4)
                                : "0.0000"}
                        </h3>
                    </div>
                    <div className="flex justify-between items-center mt-1 pt-1 border-t border-indigo-500/30">
                        <span className="text-indigo-200 text-[8px] font-bold uppercase tracking-wider">Total Units</span>
                        <span className="text-[9px] font-black text-white bg-rose-500 px-1.5 py-0.5 rounded-md shadow-sm">
                            {mfTotals.portfolioUnits?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "0.00"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Search Bar and Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search by scheme name, depositor, holder, or AMC..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all text-sm font-medium text-slate-900 placeholder:text-slate-400"
                    />
                    {searchTerm && (
                        <button
                            onClick={() => setSearchTerm("")}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                </div>

                {/* Filter Dropdowns */}
                <div className="flex flex-wrap gap-3 mt-3">
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Holder</label>
                        <select
                            value={selectedHolder}
                            onChange={(e) => setSelectedHolder(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                        >
                            <option value="All">All Holders</option>
                            {uniqueHolders.map(holder => (
                                <option key={holder} value={holder}>{holder}</option>
                            ))}
                        </select>
                    </div>

                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Depositor</label>
                        <select
                            value={selectedDepositor}
                            onChange={(e) => setSelectedDepositor(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                        >
                            <option value="All">All Depositors</option>
                            {uniqueDepositors.map(depositor => (
                                <option key={depositor} value={depositor}>{depositor}</option>
                            ))}
                        </select>
                    </div>

                    {(searchTerm || selectedHolder !== "All" || selectedDepositor !== "All") && (
                        <div className="flex items-end">
                            <button
                                onClick={() => {
                                    setSearchTerm("");
                                    setSelectedHolder("All");
                                    setSelectedDepositor("All");
                                }}
                                className="px-4 py-2 text-sm font-bold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-all"
                            >
                                Clear All Filters
                            </button>
                        </div>
                    )}
                </div>

                {(searchTerm || selectedHolder !== "All" || selectedDepositor !== "All") && (
                    <p className="mt-2 text-xs text-slate-500">
                        Showing {filteredData.length} of {data.length} results
                    </p>
                )}
            </div>

            {!groupBy ? (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                    <DataTable columns={columns} data={filteredData} />
                </div>
            ) : (
                <div className="space-y-4">
                    {groupedData?.map(([name, group]) => {
                        const pnl = group.total - group.invested;

                        return (
                            <div key={name} className="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden group transition-all hover:border-indigo-300">
                                <button
                                    onClick={() => setExpandedGroup(expandedGroup === name ? null : name)}
                                    className={`w-full flex items-center justify-between p-6 transition-colors ${expandedGroup === name ? "bg-indigo-50/50" : "hover:bg-slate-50"}`}
                                >
                                    <div className="flex items-center gap-3 sm:gap-4">
                                        <div className="bg-indigo-600 p-1.5 sm:p-2 rounded-xl text-white group-hover:scale-110 transition-transform font-black w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center text-lg sm:text-xl uppercase shadow-lg shadow-indigo-100">
                                            {name.charAt(0)}
                                        </div>
                                        <div className="text-left">
                                            <span className="font-black text-xs sm:text-xl text-slate-900 uppercase tracking-tight">{name} ({group.items.length})</span>
                                        </div>
                                    </div>

                                    <div className="flex gap-4 sm:gap-12 text-right items-center">
                                        <div className="hidden sm:block">
                                            <p className="text-[9px] text-slate-400 uppercase font-black tracking-widest mb-0.5 sm:mb-1">Total P&L</p>
                                            <p className={`text-xs sm:text-base lg:text-lg font-black ${pnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                                {pnl >= 0 ? '+' : ''}₹{Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[9px] text-slate-400 uppercase font-black tracking-widest mb-0.5 sm:mb-1">Total Value</p>
                                            <p className="text-sm sm:text-xl lg:text-2xl font-black text-indigo-700">₹{group.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                        </div>
                                        <div className={`p-2 rounded-full transition-all ${expandedGroup === name ? 'bg-indigo-600 text-white rotate-180 shadow-lg' : 'bg-slate-100 text-slate-400 group-hover:text-indigo-600'}`}>
                                            <ChevronDown className="w-6 h-6" />
                                        </div>
                                    </div>
                                </button>

                                {expandedGroup === name && (
                                    <div className="p-4 bg-slate-50/30 border-t border-slate-100 animate-in fade-in slide-in-from-top-2">
                                        <DataTable columns={columns} data={group.items} />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Sell MF Modal */}
            {isSellModalOpen && sellingMF && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-900 uppercase">Redeem Fund</h3>
                            <button onClick={() => { setIsSellModalOpen(false); setSellingMF(null); }} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <div className="mb-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Redeeming Holding</p>
                            <p className="text-lg font-black text-slate-900">{sellingMF.scheme_name}</p>
                            <p className="text-sm font-bold text-slate-500">{sellingMF.units} Units</p>
                        </div>
                        <form onSubmit={handleSellSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Units to Redeem (Max: {sellingMF.units})</label>
                                <input required type="number" step="0.0001" min="0.0001" max={sellingMF.units} className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                    value={sellForm.units} onChange={e => setSellForm({ ...sellForm, units: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Exit NAV</label>
                                <input required type="number" step="0.0001" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                    value={sellForm.sell_nav} onChange={e => setSellForm({ ...sellForm, sell_nav: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Redemption Date</label>
                                <input required type="date" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                    value={sellForm.sell_date} onChange={e => setSellForm({ ...sellForm, sell_date: e.target.value })} />
                            </div>
                            <button type="submit" className="w-full bg-amber-600 text-white font-bold py-3 rounded-xl hover:bg-amber-700 transition-colors mt-2 uppercase text-sm tracking-wider">
                                Confirm Redemption
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Add MF Modal */}
            {isAddModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-900 uppercase">Add New Fund</h3>
                            <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <form onSubmit={handleAddSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Scheme Name</label>
                                    <input required type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. SBI Bluechip Fund"
                                        value={newMF.scheme_name} onChange={e => setNewMF({ ...newMF, scheme_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Units</label>
                                    <input required type="number" step="0.0001" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newMF.units} onChange={e => setNewMF({ ...newMF, units: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Invested Amount</label>
                                    <input required type="number" step="1" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newMF.invested_amount} onChange={e => setNewMF({ ...newMF, invested_amount: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Transaction Date</label>
                                    <input type="date" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newMF.transaction_date} onChange={e => setNewMF({ ...newMF, transaction_date: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">ISIN</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={newMF.isin} onChange={e => setNewMF({ ...newMF, isin: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">AMC Name</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={newMF.amc_name} onChange={e => setNewMF({ ...newMF, amc_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">AMFI Code</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={newMF.amfi_code} onChange={e => setNewMF({ ...newMF, amfi_code: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Portfolio Holder</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Self, Family"
                                        value={newMF.holder} onChange={e => setNewMF({ ...newMF, holder: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Depositor Name</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={newMF.depositor_name} onChange={e => setNewMF({ ...newMF, depositor_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Depositor Code</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={newMF.depositor_code} onChange={e => setNewMF({ ...newMF, depositor_code: e.target.value })} />
                                </div>
                            </div>
                            <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 transition-colors mt-2 uppercase text-sm tracking-wider">
                                Add Fund
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit MF Modal */}
            {isEditModalOpen && editingMF && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-900 uppercase">Edit Fund</h3>
                            <button onClick={() => { setIsEditModalOpen(false); setEditingMF(null); }} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <form onSubmit={handleEditSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Scheme Name</label>
                                    <input required type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. SBI Bluechip Fund"
                                        value={editingMF.scheme_name} onChange={e => setEditingMF({ ...editingMF, scheme_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Units</label>
                                    <input required type="number" step="0.0001" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingMF.units} onChange={e => setEditingMF({ ...editingMF, units: Number(e.target.value) })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Invested Amount</label>
                                    <input required type="number" step="1" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingMF.invested_amount} onChange={e => setEditingMF({ ...editingMF, invested_amount: Number(e.target.value) })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Transaction Date</label>
                                    <input type="date" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingMF.transaction_date} onChange={e => setEditingMF({ ...editingMF, transaction_date: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">ISIN</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={editingMF.isin || ""} onChange={e => setEditingMF({ ...editingMF, isin: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">AMC Name</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={editingMF.amc_name || ""} onChange={e => setEditingMF({ ...editingMF, amc_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">AMFI Code</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={editingMF.amfi_code || ""} onChange={e => setEditingMF({ ...editingMF, amfi_code: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Portfolio Holder</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Self, Family"
                                        value={editingMF.holder || ""} onChange={e => setEditingMF({ ...editingMF, holder: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Depositor Name</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={editingMF.depositor_name || ""} onChange={e => setEditingMF({ ...editingMF, depositor_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Depositor Code</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={editingMF.depositor_code || ""} onChange={e => setEditingMF({ ...editingMF, depositor_code: e.target.value })} />
                                </div>
                            </div>
                            <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 transition-colors mt-2 uppercase text-sm tracking-wider">
                                Save Changes
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

