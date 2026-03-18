import { useState, useEffect, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { Plus, Trash2, X, Edit, Download, RefreshCw, TrendingUp, Search } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../components/ui/data-table";
import api, { getAnalytics, refreshAnalytics, updateGrowthRate, getAllRatings, computeRating } from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";
import { Info } from "lucide-react";

type Equity = {
    id: number;
    exchange: "NSE" | "BSE";
    symbol: string;
    scrip_name?: string;
    instrument_type?: string;
    holder: string;
    quantity: number;
    buy_price: number;
    buy_date: string;
    isin?: string;
    broker?: string;
    current_price?: number;
    current_value?: number;
    invested_value?: number;
    pnl?: number;
    pnl_percentage?: number;
    daily_change?: number;
    daily_pnl?: number;
    daily_pnl_percentage?: number;
    buy_units?: number;
    sell_units?: number;
    yahoo_symbol?: string;
    yahoo_symbol_locked?: boolean;
};

type MarketIndex = {
    name: string;
    value: number;
    change: number;
    changePercent: number;
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

export default function EquityPage() {
    const location = useLocation();
    const query = new URLSearchParams(location.search);
    const groupField = query.get("group"); // 'holder'

    const status = query.get("status") || "ACTIVE";

    const [data, setData] = useState<Equity[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
    const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([]);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedHolder, setSelectedHolder] = useState<string>("All");
    const [selectedBroker, setSelectedBroker] = useState<string>("All");
    const [starFilter, setStarFilter] = useState<number>(0); // 0 = all

    // ROE / ROCE profitability data
    const [profitabilityMap, setProfitabilityMap] = useState<Record<string, any>>({});
    const [profLoading, setProfLoading] = useState<string | null>(null); // scrip being computed

    // Rating data
    const [ratingMap, setRatingMap] = useState<Record<string, any>>({});
    const [ratingLoading, setRatingLoading] = useState<string | null>(null);

    // Modal State
    const [isaddModalOpen, setIsAddModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isSellModalOpen, setIsSellModalOpen] = useState(false);
    const [sellingEquity, setSellingEquity] = useState<Equity | null>(null);
    const [sellForm, setSellForm] = useState({
        sell_price: "",
        sell_date: new Date().toISOString().split('T')[0],
        quantity: ""
    });

    const [editingEquity, setEditingEquity] = useState<Equity | null>(null);
    const [newEquity, setNewEquity] = useState({
        exchange: "NSE",
        symbol: "",
        scrip_name: "",
        instrument_type: "Stock",
        quantity: "",
        buy_price: "",
        buy_date: new Date().toISOString().split('T')[0],
        holder: "Portfolio",
        isin: "",
        broker: "Zerodha"
    });

    // Analytics Modal State
    const [isAnalyticsModalOpen, setIsAnalyticsModalOpen] = useState(false);
    const [selectedAnalyticsEquity, setSelectedAnalyticsEquity] = useState<Equity | null>(null);
    const [analyticsData, setAnalyticsData] = useState<any>(null);
    const [analyticsLoading, setAnalyticsLoading] = useState(false);
    const [, setEditingEps] = useState<string>("");
    const [editingGrowth, setEditingGrowth] = useState<string>("10");
    const [editingYahooSymbol, setEditingYahooSymbol] = useState<string>("");
    const [isYahooSymbolLocked, setIsYahooSymbolLocked] = useState<boolean>(false);

    const handleStockClick = async (equity: Equity) => {
        setSelectedAnalyticsEquity(equity);
        setIsAnalyticsModalOpen(true);
        setAnalyticsLoading(true);
        setAnalyticsData(null);
        setEditingEps("");
        setEditingGrowth("10");
        setEditingYahooSymbol("");
        setIsYahooSymbolLocked(false);

        try {
            const data = await getAnalytics(equity.symbol);
            setAnalyticsData(data);
            if (data.eps) setEditingEps(data.eps.toString());
            setEditingYahooSymbol(data.yahoo_symbol || "");
            setIsYahooSymbolLocked(!!data.yahoo_symbol_locked);
            if (data.eps) setEditingEps(data.eps.toString());

            // Growth Rate Logic: User Saved > Yahoo Estimate > Default 10
            if (data.eps_growth !== undefined && data.eps_growth !== null && data.eps_growth !== 10) {
                setEditingGrowth(data.eps_growth.toString());
            } else if (data.earnings_growth !== undefined && data.earnings_growth !== null) {
                // Yahoo returns decimal (e.g. 0.15), convert to %
                setEditingGrowth((data.earnings_growth * 100).toFixed(1));
            } else if (data.eps_growth !== undefined && data.eps_growth !== null) {
                setEditingGrowth(data.eps_growth.toString());
            } else {
                setEditingGrowth("10");
            }
        } catch (err) {
            console.error("Failed to fetch analytics", err);
        } finally {
            setAnalyticsLoading(false);
        }
    };

    const handleRefreshAnalytics = async () => {
        if (!selectedAnalyticsEquity) return;
        setAnalyticsLoading(true);
        try {
            const data = await refreshAnalytics(selectedAnalyticsEquity.symbol);
            setAnalyticsData((prev: any) => ({ ...prev, ...data }));
            if (data.eps_growth !== undefined && data.eps_growth !== null && data.eps_growth !== 10) {
                setEditingGrowth(data.eps_growth.toString());
            } else if (data.earnings_growth !== undefined && data.earnings_growth !== null) {
                setEditingGrowth((data.earnings_growth * 100).toFixed(1));
            } else if (data.eps_growth !== undefined && data.eps_growth !== null) {
                setEditingGrowth(data.eps_growth.toString());
            }
            if (data.yahoo_symbol !== undefined) setEditingYahooSymbol(data.yahoo_symbol || "");
            if (data.yahoo_symbol_locked !== undefined) setIsYahooSymbolLocked(!!data.yahoo_symbol_locked);
        } catch (err) {
            console.error("Failed to refresh analytics", err);
        } finally {
            setAnalyticsLoading(false);
        }
    };



    const handleUpdateGrowth = async () => {
        if (!selectedAnalyticsEquity || !editingGrowth) return;
        try {
            const data = await updateGrowthRate(selectedAnalyticsEquity.symbol, parseFloat(editingGrowth));
            setAnalyticsData((prev: any) => ({ ...prev, eps_growth: data.eps_growth }));
            alert("Growth Rate Updated!");
        } catch (err) {
            console.error("Failed to update growth rate", err);
            alert("Failed to update growth rate");
        }
    };

    const handleUpdateYahooSymbol = async () => {
        if (!selectedAnalyticsEquity) return;
        try {
            const data = await api.post('/analytics/yahoo-symbol', {
                symbol: selectedAnalyticsEquity.symbol,
                yahoo_symbol: editingYahooSymbol.toUpperCase(),
                locked: isYahooSymbolLocked
            });
            setAnalyticsData((prev: any) => ({
                ...prev,
                yahoo_symbol: data.data.yahoo_symbol,
                yahoo_symbol_locked: data.data.yahoo_symbol_locked
            }));
            alert("Yahoo Symbol Mapping Updated!");
        } catch (err) {
            console.error("Failed to update Yahoo symbol mapping", err);
            alert("Failed to update mapping");
        }
    };

    const refreshData = () => {
        setLoading(true);
        // 1. Initial Load: Get stored data FAST with status filter
        api.get(`/equity/?status=${status}`)
            .then((res: any) => {
                // Filter out SGBs
                const filteredData = res.data.filter((e: any) => !e.symbol.startsWith("SGB"));
                setData(filteredData);
                setLastUpdated(new Date());
                setLoading(false);

                // 2. Background Sync
                if (status === "ACTIVE") {
                    api.get("/equity/sync-prices")
                        .then(() => {
                            api.get(`/equity/?status=${status}`).then((updatedRes: any) => {
                                const refiltered = updatedRes.data.filter((e: any) => !e.symbol.startsWith("SGB"));
                                setData(refiltered);
                                setLastUpdated(new Date());
                            });
                        })
                        .catch((e: any) => console.error("Background sync error:", e));
                }
            })
            .catch((err: any) => {
                console.error(err);
                setError("Failed to load portfolio.");
                setLoading(false);
            });
    };

    useEffect(() => {
        refreshData();
    }, [status]); // Reload when status changes

    // Load all profitability summaries once
    useEffect(() => {
        api.get("/profitability/summary")
            .then((res: any) => setProfitabilityMap(res.data))
            .catch(() => { }); // Silently ignore if not yet seeded
    }, []);

    // Load all ratings once
    useEffect(() => {
        getAllRatings()
            .then((data: any) => setRatingMap(data))
            .catch(() => { }); // Silently ignore if none computed yet
    }, []);

    const handleComputeProfitability = async (equity: Equity) => {
        const code = equity.symbol.toUpperCase();
        setProfLoading(code);
        try {
            const exchange = equity.exchange || "NSE";
            const suffix = exchange === "BSE" ? ".BO" : ".NS";
            const ticker = `${code}${suffix}`;
            const res = await api.post(`/profitability/compute/${code}`, null, {
                params: { ticker }
            });
            setProfitabilityMap(prev => ({ ...prev, [code]: res.data }));
        } catch (err) {
            console.error("Failed to compute profitability", err);
        } finally {
            setProfLoading(null);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to PERMANENTLY delete this record? Use 'Sell' to mark it as sold instead.")) return;
        try {
            await api.delete(`/equity/${id}`);
            setData(prev => prev.filter(item => item.id !== id));
        } catch (err) {
            console.error("Failed to delete equity", err);
            alert("Failed to delete equity");
        }
    };

    const handleSellInitiate = (equity: Equity) => {
        setSellingEquity(equity);
        setSellForm({
            sell_price: (equity.current_price || equity.buy_price || 0).toString(),
            sell_date: new Date().toISOString().split('T')[0],
            quantity: equity.quantity.toString()
        });
        setIsSellModalOpen(true);
    };

    const handleSellSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!sellingEquity) return;
        try {
            await api.post(`/equity/${sellingEquity.id}/sell`, null, {
                params: {
                    sell_price: Number(sellForm.sell_price),
                    sell_date: sellForm.sell_date,
                    quantity: Number(sellForm.quantity)
                }
            });
            setIsSellModalOpen(false);
            setSellingEquity(null);
            refreshData();
        } catch (err) {
            console.error("Failed to sell equity", err);
            alert("Failed to mark as sold");
        }
    };

    const handleReactivate = async (id: number) => {
        if (!confirm("Reactivate this sold holding?")) return;
        try {
            await api.post(`/equity/${id}/reactivate`);
            refreshData();
        } catch (err) {
            console.error("Failed to reactivate equity", err);
            alert("Failed to reactivate");
        }
    };

    const handleEdit = (equity: Equity) => {
        const cleanEquity = { ...equity };
        if (cleanEquity.buy_date) {
            cleanEquity.buy_date = cleanEquity.buy_date.split('T')[0];
        }
        setEditingEquity(cleanEquity);
        setIsEditModalOpen(true);
    };

    const handleEditSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingEquity) return;
        try {
            await api.put(`/equity/${editingEquity.id}`, {
                exchange: editingEquity.exchange,
                symbol: editingEquity.symbol,
                scrip_name: editingEquity.scrip_name,
                instrument_type: editingEquity.instrument_type,
                quantity: editingEquity.quantity,
                buy_price: editingEquity.buy_price,
                buy_date: editingEquity.buy_date,
                holder: editingEquity.holder,
                isin: editingEquity.isin,
                broker: editingEquity.broker
            });
            setIsEditModalOpen(false);
            setEditingEquity(null);
            refreshData();
        } catch (err) {
            console.error("Failed to update equity", err);
            alert("Failed to update equity");
        }
    };

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        const exportData = data.map(item => {
            // Ensure Scrip Name is text (not numeric code like '532331')
            const scripName = (!item.scrip_name || !isNaN(Number(item.scrip_name)))
                ? item.symbol
                : item.scrip_name;

            return {
                'Scrip Name': scripName,
                Symbol: item.symbol,
                Exchange: item.exchange,
                'Instrument Type': item.instrument_type || 'Stock',
                Quantity: item.quantity,
                'Buy Price': Number((item.buy_price || 0).toFixed(2)),
                'Current Price': Number((item.current_price || 0).toFixed(2)),
                'Current Value': Number((item.current_value || 0).toFixed(2)),
                'P&L': Number((item.pnl || 0).toFixed(2)),
                'P&L %': Number((item.pnl_percentage || 0).toFixed(2)),
                'PF Units': Number((item.buy_units || 0).toFixed(2)),
                Holder: getDisplayName(item.holder || '-')
            };
        });

        if (format === 'pdf') {
            exportToPDF(exportData, ['Scrip Name', 'Symbol', 'Exchange', 'Instrument Type', 'Quantity', 'PF Units', 'Buy Price', 'Current Price', 'Current Value', 'P&L', 'P&L %', 'Holder'], 'Equity Portfolio');
        } else if (format === 'excel') {
            exportToExcel(exportData, 'Equity_Portfolio');
        } else {
            exportToCSV(exportData, 'Equity_Portfolio');
        }
    };

    const handleAddSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post("/equity/", {
                ...newEquity,
                quantity: Number(newEquity.quantity),
                buy_price: Number(newEquity.buy_price)
            });
            setIsAddModalOpen(false);
            refreshData();
            // Reset form
            setNewEquity({
                exchange: "NSE",
                symbol: "",
                scrip_name: "",
                instrument_type: "Stock",
                quantity: "",
                buy_price: "",
                buy_date: new Date().toISOString().split('T')[0],
                holder: "Portfolio",
                isin: "",
                broker: "Zerodha"
            });
        } catch (err: any) {
            console.error("Failed to add equity", err);
            const msg = err.response?.data?.detail
                ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail))
                : (err.message || "Unknown error");
            alert(`Failed to create entry: ${msg}`);
        }
    };

    // ... (market indices useEffect remains same)

    const fetchMarketIndices = async () => {
        // ... same implementation ...
        try {
            const response = await api.get("/market/indices");
            setMarketIndices(response.data);
        } catch (err) { console.error(err); }
    }

    useEffect(() => { fetchMarketIndices(); }, []);

    // Extract unique holders and brokers for filter dropdowns
    const uniqueHolders = useMemo(() => {
        const holders = new Set<string>();
        data.forEach(item => {
            if (item.holder) holders.add(getDisplayName(item.holder));
        });
        return Array.from(holders).sort();
    }, [data]);

    const uniqueBrokers = useMemo(() => {
        const brokers = new Set<string>();
        data.forEach(item => {
            if (item.broker) brokers.add(item.broker);
        });
        return Array.from(brokers).sort();
    }, [data]);

    // Filter data based on search term, holder, and broker
    const filteredData = useMemo(() => {
        let filtered = data;

        // Apply search filter
        if (searchTerm.trim()) {
            const term = searchTerm.toLowerCase();
            filtered = filtered.filter(item =>
                item.symbol.toLowerCase().includes(term) ||
                (item.scrip_name && item.scrip_name.toLowerCase().includes(term)) ||
                (item.holder && item.holder.toLowerCase().includes(term)) ||
                (item.broker && item.broker.toLowerCase().includes(term))
            );
        }

        // Apply holder filter
        if (selectedHolder !== "All") {
            filtered = filtered.filter(item =>
                getDisplayName(item.holder || "") === selectedHolder
            );
        }

        // Apply broker filter
        if (selectedBroker !== "All") {
            filtered = filtered.filter(item => item.broker === selectedBroker);
        }

        // Apply star rating filter
        if (starFilter > 0) {
            filtered = filtered.filter(item => {
                const code = item.symbol.toUpperCase();
                return (ratingMap[code]?.star_rating ?? 0) === starFilter;
            });
        }

        return filtered;
    }, [data, searchTerm, selectedHolder, selectedBroker, starFilter, ratingMap]);

    // ... (Grouping Logic and Totals Calculation remain same)

    // Grouping Logic Re-implementation for context
    const groupedData = useMemo(() => {
        if (!groupField) return null;
        const groups: Record<string, { totalValue: number, totalInvested: number, totalDailyPnl: number, items: Equity[] }> = {};
        filteredData.forEach(item => {
            const rawKey = item.holder || "Unknown";
            const key = getDisplayName(rawKey);
            if (!groups[key]) groups[key] = { totalValue: 0, totalInvested: 0, totalDailyPnl: 0, items: [] };
            groups[key].items.push(item);
            groups[key].totalValue += (item.current_value || 0);
            groups[key].totalInvested += (item.invested_value || 0);
            groups[key].totalDailyPnl += (item.daily_pnl || 0);
        });
        return Object.entries(groups).sort((a, b) => b[1].totalValue - a[1].totalValue);
    }, [filteredData, groupField]);

    const portfolioTotals = useMemo(() => {
        let current = 0; let invested = 0; let dailyPnl = 0; let prevTotalValue = 0;
        let totalQty = 0;
        let totalBuyUnits = 0;
        let totalSellUnits = 0;
        filteredData.forEach(item => {
            const currentVal = item.current_value || 0;
            const investedVal = item.invested_value || 0;
            const dpnl = item.daily_pnl || 0;
            current += currentVal; invested += investedVal; dailyPnl += dpnl;
            prevTotalValue += (currentVal - dpnl);
            totalQty += item.quantity;
            totalBuyUnits += (item.buy_units || 0);
            totalSellUnits += (item.sell_units || 0);
        });

        const portfolioUnits = totalBuyUnits - totalSellUnits;
        const pnl = current - invested;
        const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;
        const dailyPnlPct = prevTotalValue > 0 ? (dailyPnl / prevTotalValue) * 100 : 0;

        // Correct NAV Calculation: Value / Portfolio Units
        // Fallback to 100 if units are 0 to avoid Infinity/NaN on empty portfolio
        const nav = portfolioUnits > 0 ? current / portfolioUnits : 0;
        const dailyNavChange = portfolioUnits > 0 ? dailyPnl / portfolioUnits : 0;

        return { current, invested, pnl, pnlPct, dailyPnl, dailyPnlPct, nav, dailyNavChange, portfolioUnits };
    }, [filteredData]);


    const columns: ColumnDef<Equity>[] = [
        {
            id: "symbol",
            accessorFn: (row) => row.symbol,
            header: "Symbol",
            cell: ({ row }) => {
                const code = row.original.symbol.toUpperCase();
                const rating = ratingMap[code];
                const starCount = rating?.star_rating ?? 0;
                const label = rating?.label ?? '';
                const score = rating?.final_score ?? null;


                return (
                    <div className="flex flex-col">
                        <button
                            onClick={() => handleStockClick(row.original)}
                            className="font-black text-slate-900 truncate max-w-[200px] uppercase hover:text-indigo-600 text-left flex items-center gap-1"
                            title="Click for Analytics"
                        >
                            {row.original.symbol}
                            <Info className="w-3 h-3 text-slate-400" />
                        </button>
                        <div className="flex items-center gap-1 mt-0.5">
                            <span className="text-[10px] text-slate-500 font-bold uppercase">{row.original.exchange}</span>
                            {starCount > 0 && (
                                <span className="inline-flex items-center text-sm leading-none" title={`${label} · ${score}/100`}>
                                    <span style={{ color: starCount >= 4 ? '#059669' : starCount === 3 ? '#d97706' : '#dc2626', letterSpacing: '-1px' }} className="font-black">{'★'.repeat(starCount)}</span>
                                    <span style={{ color: '#94a3b8', letterSpacing: '-1px' }} className="font-black">{'★'.repeat(5 - starCount)}</span>
                                </span>
                            )}
                        </div>
                    </div>
                );
            }
        },
        {
            accessorKey: "quantity",
            header: "Qty",
            cell: ({ row }) => <span className="text-slate-700 font-medium">{row.original.quantity}</span>
        },
        {
            accessorKey: "buy_units",
            header: "PF Units",
            cell: ({ row }) => (
                <span className="text-rose-600 font-bold bg-rose-50 px-2 py-0.5 rounded text-[10px]">
                    {(row.original.buy_units || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
            )
        },
        {
            accessorKey: "buy_price",
            header: status === "SOLD" ? "Buy/Sell Price" : "Avg Price",
            cell: ({ row }) => (
                <div className="flex flex-col">
                    <span className="text-slate-700">₹{row.original.buy_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    {status === "SOLD" && (row.original as any).sell_price && (
                        <span className="text-indigo-600 font-bold">₹{(row.original as any).sell_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    )}
                </div>
            )
        },
        {
            accessorKey: "current_price",
            header: status === "SOLD" ? "Sell Date" : "LTP",
            cell: ({ row }) => {
                if (status === "SOLD" && (row.original as any).sell_date) {
                    return <span className="text-slate-500 text-xs font-bold uppercase">{(row.original as any).sell_date}</span>
                }
                return row.original.current_price ? (
                    <span className="text-indigo-700 font-bold">₹{row.original.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                ) : <span className="text-slate-400">-</span>
            }
        },
        {
            accessorKey: "current_value",
            header: status === "SOLD" ? "Sold Value" : "Current Value",
            cell: ({ row }) => {
                const val = status === "SOLD"
                    ? ((row.original as any).sell_price * row.original.quantity)
                    : (row.original.current_value || 0);
                return (
                    <span className="font-black text-slate-900">
                        ₹{val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                )
            }
        },
        {
            accessorKey: "daily_pnl",
            header: "Daily Gain/Loss",
            cell: ({ row }) => {
                const dailyPnl = row.original.daily_pnl || 0;
                const dailyPct = row.original.daily_pnl_percentage || 0;
                const dailyChange = row.original.daily_change || 0;

                if (status === "SOLD") return <span className="text-slate-400">-</span>;

                return (
                    <div className={`font-bold ${dailyPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        <div className="text-xs">{dailyPnl >= 0 ? '+' : '-'}₹{Math.abs(dailyPnl).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
                        <div className="text-[10px] opacity-80">{dailyChange >= 0 ? '+' : '-'}{Math.abs(dailyChange).toFixed(2)} ({dailyPct >= 0 ? '+' : '-'}{Math.abs(dailyPct).toFixed(2)}%)</div>
                    </div>
                );
            }
        },
        {
            accessorKey: "pnl",
            header: "Total P&L",
            cell: ({ row }) => {
                let pnl = row.original.pnl || 0;
                let pnl_pct = row.original.pnl_percentage || 0;

                if (status === "SOLD") {
                    const sellVal = (row.original as any).sell_price * row.original.quantity;
                    const buyVal = row.original.buy_price * row.original.quantity;
                    pnl = sellVal - buyVal;
                    pnl_pct = buyVal > 0 ? (pnl / buyVal) * 100 : 0;
                }

                return (
                    <div className={`font-black ${pnl >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                        {pnl >= 0 ? '+' : ''}₹{pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({pnl_pct.toFixed(2)}%)
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
                                title="Mark as Sold"
                            >
                                <span className="text-red-600 font-black text-sm">S</span>
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={() => handleReactivate(row.original.id)}
                            className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"
                            title="Reactivate / Buy Back"
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
                        {status === "SOLD" ? "Sold Shares" : "Bought Shares"}
                    </h2>
                    <p className="text-slate-500 text-[10px] sm:text-sm lg:text-base">Real-time tracking of your stocks and market indices.</p>
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
                            to="/equity/upload"
                            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl hover:bg-indigo-700 transition-all font-bold text-xs shadow-sm uppercase"
                        >
                            <span>Import</span>
                        </Link>
                    </div>
                </div>
            </div>

            {/* ... (Market Indices & Summary - keeping existing structure) ... */}
            {/* Market Indices - Compact Bar */}
            <div className="flex flex-wrap gap-4 items-center bg-slate-900 text-white p-4 rounded-xl shadow-lg border border-slate-700">
                <div className="flex items-center gap-2 border-r border-slate-700 pr-4 mr-2">
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Market Status</span>
                    <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span className="text-xs font-bold text-emerald-400">LIVE</span>
                    </div>
                </div>

                {marketIndices.length > 0 ? (
                    marketIndices.map((index) => (
                        <div key={index.name} className="flex items-center gap-3 pr-4 border-r border-slate-700/50 last:border-0">
                            <div>
                                <p className="text-[10px] font-black uppercase text-slate-400 leading-none mb-0.5">{index.name}</p>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-lg font-black">{index.value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                    <span className={`text-xs font-bold ${index.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {index.change >= 0 ? '+' : ''}{index.change.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({index.changePercent.toFixed(2)}%)
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="text-sm text-slate-400 italic">Loading Market Data...</div>
                )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* ... Totals Cards ... */}
                {/* ... Totals Cards ... */}
                {/* ... Totals Cards ... */}
                <div className="bg-white rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-sm border border-slate-200 flex flex-col justify-center">
                    <p className="text-slate-400 text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-0.5">Total Value</p>
                    <h3 className="text-sm sm:text-lg lg:text-xl font-black text-indigo-600">₹{portfolioTotals.current.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
                <div className="bg-white rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-sm border border-slate-200 flex flex-col justify-center">
                    <p className="text-slate-400 text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-0.5">Overall P&L</p>
                    <h3 className={`text-sm sm:text-lg lg:text-xl font-black ${portfolioTotals.pnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {portfolioTotals.pnl >= 0 ? '+' : ''}₹{Math.abs(portfolioTotals.pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </h3>
                </div>
                <div className="bg-white rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-sm border border-slate-200 flex flex-col justify-center">
                    <p className="text-slate-400 text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-0.5">Day's G/L</p>
                    <h3 className={`text-sm sm:text-lg lg:text-xl font-black ${portfolioTotals.dailyPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {portfolioTotals.dailyPnl >= 0 ? '+' : ''}₹{Math.abs(portfolioTotals.dailyPnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </h3>
                </div>
                <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 shadow-lg text-white border border-indigo-500/20 flex flex-col justify-between">
                    <div className="flex justify-between items-start mb-0.5">
                        <p className="text-indigo-100 text-[8px] sm:text-[9px] font-bold uppercase tracking-widest">Portfolio NAV</p>
                        <TrendingUp className="text-indigo-300 w-3 h-3" />
                    </div>
                    <div className="flex items-baseline gap-1.5">
                        <h3 className="text-lg sm:text-xl font-black">₹{portfolioTotals.nav.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                        <div className={`flex items-center text-[10px] font-bold ${portfolioTotals.dailyNavChange >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                            ({portfolioTotals.dailyNavChange >= 0 ? '+' : ''}{portfolioTotals.dailyNavChange.toFixed(2)})
                        </div>
                    </div>
                    <div className="flex justify-between items-center mt-1 pt-1 border-t border-indigo-500/30">
                        <span className="text-indigo-200 text-[8px] font-bold uppercase tracking-wider">Total Units</span>
                        <span className="text-[9px] font-black text-white bg-rose-500 px-1.5 py-0.5 rounded-md shadow-sm">
                            {portfolioTotals.portfolioUnits?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "0.00"}
                        </span>
                    </div>
                </div>
            </div>

            {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">{error}</div>}

            {/* Search Bar and Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search by symbol, scrip name, holder, or broker..."
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
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Broker</label>
                        <select
                            value={selectedBroker}
                            onChange={(e) => setSelectedBroker(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
                        >
                            <option value="All">All Brokers</option>
                            {uniqueBrokers.map(broker => (
                                <option key={broker} value={broker}>{broker}</option>
                            ))}
                        </select>
                    </div>

                    <div className="flex-1 min-w-[160px]">
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">⭐ Star Rating</label>
                        <select
                            value={starFilter}
                            onChange={(e) => setStarFilter(Number(e.target.value))}
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

                    {(searchTerm || selectedHolder !== "All" || selectedBroker !== "All" || starFilter > 0) && (
                        <div className="flex items-end">
                            <button
                                onClick={() => {
                                    setSearchTerm("");
                                    setSelectedHolder("All");
                                    setSelectedBroker("All");
                                    setStarFilter(0);
                                }}
                                className="px-4 py-2 text-sm font-bold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-all"
                            >
                                Clear All Filters
                            </button>
                        </div>
                    )}
                </div>

                {(searchTerm || selectedHolder !== "All" || selectedBroker !== "All" || starFilter > 0) && (
                    <p className="mt-2 text-xs text-slate-500">
                        Showing {filteredData.length} of {data.length} results
                    </p>
                )}
            </div>

            {!groupField ? (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                    <DataTable columns={columns} data={filteredData} />
                </div>
            ) : (
                <div className="space-y-4">
                    {/* ... Grouped Data Logic ... */}
                    {groupedData?.map(([name, group]) => (
                        <div key={name} className="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden transition-all hover:border-indigo-300">
                            <button
                                onClick={() => setExpandedGroup(expandedGroup === name ? null : name)}
                                className={`w-full flex justify-between items-center p-4 sm:p-6 transition-colors ${expandedGroup === name ? 'bg-indigo-50/50' : 'hover:bg-slate-50'}`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-1.5 sm:w-2 h-6 sm:h-8 rounded-full ${expandedGroup === name ? 'bg-indigo-600' : 'bg-slate-300'}`}></div>
                                    <span className="font-black text-xs sm:text-xl text-slate-900 uppercase tracking-tight">{getDisplayName(name)} ({group.items.length})</span>
                                </div>
                                <div className="text-right">
                                    <span className="block font-black text-sm sm:text-lg lg:text-xl text-indigo-700">₹{group.totalValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                    <span className={`text-[9px] sm:text-[10px] font-bold uppercase ${group.totalDailyPnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                        {group.totalDailyPnl >= 0 ? '+' : ''}₹{group.totalDailyPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TODAY
                                    </span>
                                </div>
                            </button>
                            {expandedGroup === name && (
                                <div className="p-4 border-t border-slate-100 bg-slate-50/30 animate-in fade-in slide-in-from-top-2">
                                    <DataTable columns={columns} data={group.items} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Analytics Modal */}
            {isAnalyticsModalOpen && selectedAnalyticsEquity && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-lg p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
                        <button
                            onClick={() => setIsAnalyticsModalOpen(false)}
                            className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 bg-slate-100 rounded-full"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        {/* Modal Header with Rating */}
                        {(() => {
                            const code = selectedAnalyticsEquity.symbol.toUpperCase();
                            const rating = ratingMap[code];
                            const isRecomputing = ratingLoading === code;

                            const handleRecomputeRating = async () => {
                                setRatingLoading(code);
                                try {
                                    const result = await computeRating(code);
                                    setRatingMap(prev => ({ ...prev, [code]: result }));
                                } catch (e) {
                                    console.error('Rating compute failed', e);
                                } finally {
                                    setRatingLoading(null);
                                }
                            };

                            const starColor = (rating?.star_rating ?? 0) >= 4 ? '#10b981'  // emerald
                                : (rating?.star_rating ?? 0) === 3 ? '#f59e0b'              // amber
                                    : (rating?.star_rating ?? 0) > 0 ? '#f87171'               // red
                                        : '#cbd5e1';                                                // slate

                            return (
                                <div className="mb-5">
                                    <div className="flex items-start justify-between pr-8">
                                        <div>
                                            <h3 className="text-2xl font-black text-slate-900 uppercase flex items-center gap-2">
                                                {selectedAnalyticsEquity.symbol}
                                                <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded font-bold">{selectedAnalyticsEquity.exchange}</span>
                                            </h3>
                                            <p className="text-slate-500 text-sm font-medium truncate">{selectedAnalyticsEquity.scrip_name}</p>
                                        </div>

                                        {/* Star Rating Badge */}
                                        {rating ? (
                                            <div className="flex flex-col items-end ml-2">
                                                {rating.data_state === 'RATED' ? (
                                                    <div className="flex items-center gap-1.5">
                                                        <span
                                                            className="text-xl leading-none inline-flex"
                                                            title={`${rating.final_score}/100`}
                                                        >
                                                            <span style={{ color: starColor, letterSpacing: '-1px' }} className="font-black">{'★'.repeat(rating.star_rating)}</span>
                                                            <span style={{ color: '#94a3b8', letterSpacing: '-1px' }} className="font-black">{'★'.repeat(5 - rating.star_rating)}</span>
                                                        </span>
                                                        <div className="flex flex-col items-end">
                                                            <span className="text-[10px] font-black text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                                                                {rating.final_score}/100
                                                            </span>
                                                            {rating.confidence_label && (
                                                                <span
                                                                    className={`text-[8px] font-black uppercase mt-0.5 px-1 rounded-sm ${rating.confidence_label === 'Full' ? 'bg-emerald-50 text-emerald-600' :
                                                                        rating.confidence_label === 'High' ? 'bg-indigo-50 text-indigo-600' :
                                                                            rating.confidence_label === 'Medium' ? 'bg-amber-50 text-amber-600' :
                                                                                'bg-slate-50 text-slate-400'
                                                                        }`}
                                                                    title={`Confidence: ${rating.confidence_pts_have}/${rating.confidence_pts_max} data points`}
                                                                >
                                                                    {rating.confidence_label} ({rating.confidence_pts_have}/{rating.confidence_pts_max})
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="flex flex-col items-end">
                                                        <div className="flex items-center gap-2 text-indigo-600">
                                                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                                            <span className="text-[10px] font-black uppercase tracking-tighter">
                                                                {rating.data_state === 'FETCHING' ? 'Fetching Data...' :
                                                                    rating.data_state === 'DERIVING' ? 'Deriving Metrics...' :
                                                                        rating.data_state === 'READY' ? 'Queued for Rating...' :
                                                                            rating.data_state === 'INVALID_CLASSIFICATION' ? 'Invalid Sector' :
                                                                                'Computing...'}
                                                            </span>
                                                        </div>
                                                        {rating.missing_fields && rating.missing_fields.length > 0 && (
                                                            <span className="text-[8px] text-slate-400 font-bold mt-0.5">
                                                                Missing: {rating.missing_fields.slice(0, 2).join(', ')}...
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <button
                                                onClick={handleRecomputeRating}
                                                disabled={isRecomputing}
                                                className="text-[10px] font-bold text-indigo-600 hover:underline flex items-center gap-1 disabled:opacity-50 ml-2"
                                            >
                                                <RefreshCw className={`w-3 h-3 ${isRecomputing ? 'animate-spin' : ''}`} />
                                                {isRecomputing ? 'Rating...' : 'Compute Rating'}
                                            </button>
                                        )}
                                    </div>

                                    {/* Rating Score Breakdown */}
                                    {rating && rating.data_state === 'RATED' && (
                                        <div className="mt-3 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3">
                                            <div className="flex justify-between items-center mb-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Score Breakdown</span>
                                                    {rating.trend_confidence === 'LOW' && (
                                                        <span className="text-[8px] bg-amber-100 text-amber-700 px-1 rounded font-bold uppercase">Trend: Low Conf</span>
                                                    )}
                                                </div>
                                                <button
                                                    onClick={handleRecomputeRating}
                                                    disabled={isRecomputing}
                                                    className="text-[10px] font-bold text-indigo-500 hover:underline flex items-center gap-1 disabled:opacity-50"
                                                >
                                                    <RefreshCw className={`w-2.5 h-2.5 ${isRecomputing ? 'animate-spin' : ''}`} />
                                                    {isRecomputing ? 'Recomputing...' : 'Recompute'}
                                                </button>
                                            </div>
                                            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                                                {[
                                                    { label: 'Trend', score: rating.trend_score, max: 20 },
                                                    { label: 'Valuation', score: rating.valuation_score, max: 25 },
                                                    { label: 'Profitability', score: rating.profitability_score, max: 35 },
                                                    { label: 'Growth', score: rating.growth_score, max: 20 },
                                                ].map(({ label, score, max }) => (
                                                    <div key={label}>
                                                        <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-0.5">
                                                            <span>{label}</span>
                                                            <span>{score ?? '—'}/{max}</span>
                                                        </div>
                                                        <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                                            <div
                                                                className="h-full rounded-full transition-all duration-500"
                                                                style={{
                                                                    width: `${((score ?? 0) / max) * 100}%`,
                                                                    backgroundColor: ((score ?? 0) / max) >= 0.7 ? '#10b981'
                                                                        : ((score ?? 0) / max) >= 0.4 ? '#f59e0b'
                                                                            : '#f87171'
                                                                }}
                                                            />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>

                                            {/* Fallback Audit */}
                                            {rating.fallbacks_applied && rating.fallbacks_applied.length > 0 && (
                                                <div className="mt-3 pt-2 border-t border-slate-200/50">
                                                    <span className="text-[8px] font-black text-slate-400 uppercase mb-1 block">Assumptions Made</span>
                                                    <div className="flex flex-wrap gap-1">
                                                        {rating.fallbacks_applied.map((fb: string, idx: number) => (
                                                            <span key={idx} className="text-[8px] bg-indigo-50 text-indigo-500 px-1.5 py-0.5 rounded font-medium border border-indigo-100/50">
                                                                {fb.split(' → ')[0]}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            <p className="text-[9px] text-slate-300 mt-2 text-right" title="Rating derived from trend, valuation, profitability & growth expectations using fallback assumptions for missing data.">
                                                Data-First Engine · {rating.sector_type} Path
                                            </p>
                                        </div>
                                    )}
                                </div>
                            );
                        })()}

                        {analyticsLoading ? (
                            <div className="flex justify-center p-8">
                                <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {/* Yahoo Symbol Mapping Section - NEW */}
                                <div className="bg-amber-50 rounded-xl border border-amber-200 overflow-hidden">
                                    <div className="bg-amber-100/50 px-4 py-2 border-b border-amber-200 flex justify-between items-center">
                                        <h4 className="text-[10px] font-black text-amber-700 uppercase tracking-widest flex items-center gap-1.5">
                                            Yahoo Finance Mapping
                                            {isYahooSymbolLocked && <span className="text-[8px] bg-amber-200 text-amber-800 px-1 rounded">LOCKED</span>}
                                        </h4>
                                        <div className="flex items-center gap-2">
                                            <label className="flex items-center gap-1.5 cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    checked={isYahooSymbolLocked}
                                                    onChange={(e) => setIsYahooSymbolLocked(e.target.checked)}
                                                    className="w-3 h-3 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                                                />
                                                <span className="text-[9px] font-bold text-amber-600 uppercase">Lock</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div className="p-4 flex gap-3 items-end">
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-amber-600 uppercase mb-1.5">Yahoo Symbol (e.g. RELIANCE.NS)</p>
                                            <input
                                                type="text"
                                                value={editingYahooSymbol}
                                                onChange={(e) => setEditingYahooSymbol(e.target.value.toUpperCase())}
                                                className="w-full rounded-lg border-2 border-amber-200 bg-white text-slate-900 text-sm font-black px-3 py-1.5 focus:border-amber-400 outline-none uppercase"
                                                placeholder="SYMBOL.NS"
                                            />
                                        </div>
                                        <button
                                            onClick={handleUpdateYahooSymbol}
                                            className="bg-amber-600 text-white px-4 py-2 rounded-lg text-[10px] font-black uppercase hover:bg-amber-700 transition-colors shadow-sm"
                                        >
                                            Save Mapping
                                        </button>
                                    </div>
                                    {(!analyticsData?.yahoo_symbol) && (
                                        <div className="px-4 pb-3">
                                            <div className="text-[9px] text-red-600 font-bold bg-red-50 p-2 rounded border border-red-100">
                                                ⚠ No mapping found. Price and analytics data fetching is DISABLED for this scrip until mapped.
                                            </div>
                                        </div>
                                    )}
                                </div>
                                {/* Price & P/E Section */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                                        <p className="text-xs font-bold text-slate-400 uppercase mb-1">Current Price</p>
                                        <div className="text-2xl font-black text-slate-900">
                                            ₹{(analyticsData?.price || selectedAnalyticsEquity.current_price || 0).toLocaleString('en-IN')}
                                        </div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                                        <p className="text-xs font-bold text-slate-400 uppercase mb-1">P/E Ratio</p>
                                        <div className="flex items-baseline gap-2">
                                            <div className="text-2xl font-black text-indigo-600">
                                                {analyticsData?.pe ? analyticsData.pe.toFixed(2) : '-'}
                                            </div>
                                            {analyticsData?.eps && <span className="text-xs text-slate-500 font-bold">(EPS: {analyticsData.eps})</span>}
                                        </div>
                                    </div>
                                </div>

                                {/* ROE / ROCE Section */}
                                {(() => {
                                    const code = selectedAnalyticsEquity.symbol.toUpperCase();
                                    const prof = profitabilityMap[code];
                                    const isComputing = profLoading === code;
                                    return (
                                        <div className="pt-3 border-t border-slate-100">
                                            <div className="flex justify-between items-center mb-2">
                                                <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest">Profitability (3Y Avg)</h4>
                                                <button
                                                    onClick={() => handleComputeProfitability(selectedAnalyticsEquity)}
                                                    disabled={isComputing}
                                                    className="text-[10px] font-bold text-indigo-600 hover:text-indigo-700 hover:underline flex items-center gap-1 disabled:opacity-50"
                                                    title="Fetch from Yahoo Finance and compute ROE/ROCE"
                                                >
                                                    <RefreshCw className={`w-3 h-3 ${isComputing ? 'animate-spin' : ''}`} />
                                                    {isComputing ? 'Computing...' : prof ? 'Recompute' : 'Compute Metrics'}
                                                </button>
                                            </div>

                                            {prof && !prof.financials_incomplete ? (
                                                <div className={`grid gap-3 ${prof.is_bank ? 'grid-cols-1' : 'grid-cols-2'}`}>
                                                    {/* ROE card — always shown */}
                                                    <div className="bg-emerald-50 p-3 rounded-xl border border-emerald-100">
                                                        <p className="text-[10px] font-bold text-emerald-600 uppercase mb-1">ROE (3Y Avg)</p>
                                                        <div className="text-xl font-black text-emerald-700">
                                                            {prof.roe_3y_avg != null ? `${prof.roe_3y_avg.toFixed(1)}%` : '—'}
                                                        </div>
                                                        <p className="text-[9px] text-emerald-400 font-bold mt-0.5">Return on Equity</p>
                                                    </div>
                                                    {/* ROCE card — hidden for banks */}
                                                    {!prof.is_bank && (
                                                        <div className="bg-blue-50 p-3 rounded-xl border border-blue-100">
                                                            <p className="text-[10px] font-bold text-blue-600 uppercase mb-1">ROCE (3Y Avg)</p>
                                                            <div className="text-xl font-black text-blue-700">
                                                                {prof.roce_3y_avg != null ? `${prof.roce_3y_avg.toFixed(1)}%` : '—'}
                                                            </div>
                                                            <p className="text-[9px] text-blue-400 font-bold mt-0.5">Return on Capital Employed</p>
                                                        </div>
                                                    )}
                                                </div>
                                            ) : prof?.financials_incomplete ? (
                                                <div className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 font-bold">
                                                    ⚠ Incomplete financials — some FY data unavailable from Yahoo Finance.
                                                </div>
                                            ) : (
                                                <div className="text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                                                    Not computed yet. Click <span className="font-bold text-indigo-600">Compute Metrics</span> to fetch from Yahoo Finance (FY23–FY25).
                                                </div>
                                            )}

                                            {prof && (
                                                <p className="text-[9px] text-slate-300 mt-2 text-right" title="Calculated using last 3 completed financial years (FY23–FY25) from audited statements.">
                                                    FY23–FY25 · Yahoo Finance audited statements{prof.is_bank ? ' · ROCE N/A (Bank)' : ''}
                                                </p>
                                            )}
                                        </div>
                                    );
                                })()}

                                {/* Moving Averages */}
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center mb-1">
                                        <h4 className="text-sm font-black text-slate-800 uppercase">Technical Indicators</h4>
                                        <button onClick={handleRefreshAnalytics} className="text-xs text-indigo-600 font-bold hover:underline flex items-center gap-1">
                                            <RefreshCw className="w-3 h-3" /> Refresh
                                        </button>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className={`p-3 rounded-lg border flex flex-col items-center justify-center ${(analyticsData?.price && analyticsData?.ma50 && analyticsData.price > analyticsData.ma50)
                                            ? 'bg-emerald-50 border-emerald-100'
                                            : 'bg-red-50 border-red-100'
                                            }`}>
                                            <span className="text-[10px] font-bold uppercase text-slate-500 mb-1">50 DMA</span>
                                            <span className={`text-lg font-black ${(analyticsData?.price && analyticsData?.ma50 && analyticsData.price > analyticsData.ma50) ? 'text-emerald-700' : 'text-red-700'
                                                }`}>
                                                {analyticsData?.ma50 ? analyticsData.ma50.toFixed(2) : '-'}
                                            </span>
                                            <span className="text-[9px] font-bold text-slate-400 mt-1">
                                                {analyticsData?.ma50 ? ((analyticsData.price / analyticsData.ma50 - 1) * 100).toFixed(1) + '% vs Price' : ''}
                                            </span>
                                        </div>

                                        <div className={`p-3 rounded-lg border flex flex-col items-center justify-center ${(analyticsData?.price && analyticsData?.ma200 && analyticsData.price > analyticsData.ma200)
                                            ? 'bg-emerald-50 border-emerald-100'
                                            : 'bg-red-50 border-red-100'
                                            }`}>
                                            <span className="text-[10px] font-bold uppercase text-slate-500 mb-1">200 DMA</span>
                                            <span className={`text-lg font-black ${(analyticsData?.price && analyticsData?.ma200 && analyticsData.price > analyticsData.ma200) ? 'text-emerald-700' : 'text-red-700'
                                                }`}>
                                                {analyticsData?.ma200 ? analyticsData.ma200.toFixed(2) : '-'}
                                            </span>
                                            <span className="text-[9px] font-bold text-slate-400 mt-1">
                                                {analyticsData?.ma200 ? ((analyticsData.price / analyticsData.ma200 - 1) * 100).toFixed(1) + '% vs Price' : ''}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Trend Signal */}
                                    {analyticsData?.signal && (
                                        <div className={`flex items-center gap-2 p-3 rounded-lg border 
                                            ${analyticsData.signal === 'bullish' ? 'bg-emerald-50 border-emerald-200' :
                                                analyticsData.signal === 'bearish' ? 'bg-red-50 border-red-200' :
                                                    analyticsData.signal === 'long term bullish, near term bearish' ? 'bg-indigo-50 border-indigo-200' :
                                                        analyticsData.signal === 'near term bullish, long term bearish' ? 'bg-amber-50 border-amber-200' :
                                                            'bg-slate-100 border-slate-200'
                                            }`}>
                                            <TrendingUp className={`w-5 h-5 
                                                ${analyticsData.signal === 'bullish' ? 'text-emerald-600' :
                                                    analyticsData.signal === 'bearish' ? 'text-red-600' :
                                                        analyticsData.signal === 'long term bullish, near term bearish' ? 'text-indigo-600' :
                                                            analyticsData.signal === 'near term bullish, long term bearish' ? 'text-amber-600' :
                                                                'text-slate-400'
                                                }`} />
                                            <div>
                                                <div className="text-xs font-bold uppercase text-slate-500">Trend Signal</div>
                                                <div className={`text-sm font-black 
                                                    ${analyticsData.signal === 'bullish' ? 'text-emerald-700' :
                                                        analyticsData.signal === 'bearish' ? 'text-red-700' :
                                                            analyticsData.signal === 'long term bullish, near term bearish' ? 'text-indigo-700' :
                                                                analyticsData.signal === 'near term bullish, long term bearish' ? 'text-amber-700' :
                                                                    'text-slate-600'
                                                    }`}>
                                                    {analyticsData.signal}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Forward P/E Section */}
                                <div className="pt-4 border-t border-slate-100">
                                    <div className="flex flex-wrap justify-between items-center mb-3 text-slate-900">
                                        <label className="text-xs font-bold text-slate-500 uppercase mr-2">Forward P/E Projections</label>
                                        <div className="flex items-center gap-2 mt-1 sm:mt-0">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">Growth %</span>
                                            <div className="flex gap-1">
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    value={editingGrowth}
                                                    onChange={(e) => setEditingGrowth(e.target.value)}
                                                    className="w-20 rounded-lg border-2 border-slate-300 bg-white text-slate-900 text-sm font-bold text-center py-1 px-2 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none"
                                                    placeholder="10"
                                                />
                                                <button
                                                    onClick={handleUpdateGrowth}
                                                    className="bg-indigo-600 text-white px-3 py-1 rounded-lg text-[10px] font-bold uppercase hover:bg-indigo-700 shadow-sm"
                                                >
                                                    Save
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-indigo-50 p-3 rounded-lg border border-indigo-100">
                                            <p className="text-[10px] font-bold text-indigo-400 uppercase mb-1">1 Yr Forward P/E</p>
                                            <div className="text-xl font-black text-indigo-700">
                                                {analyticsData?.price && analyticsData?.eps && editingGrowth ? (
                                                    analyticsData.forward_eps ? (
                                                        (analyticsData.price / analyticsData.forward_eps).toFixed(2)
                                                    ) : (
                                                        (analyticsData.price / (analyticsData.eps * (1 + parseFloat(editingGrowth) / 100))).toFixed(2)
                                                    )
                                                ) : '-'}
                                            </div>
                                            <p className="text-[9px] text-indigo-400 font-bold mt-1">
                                                {analyticsData?.price && analyticsData?.eps && editingGrowth ? (
                                                    analyticsData.forward_eps ? (
                                                        `₹${analyticsData.price.toFixed(2)} / ${analyticsData.forward_eps.toFixed(2)} (Yahoo Est)`
                                                    ) : (
                                                        `₹${analyticsData.price.toFixed(2)} / ${(analyticsData.eps * (1 + parseFloat(editingGrowth) / 100)).toFixed(2)} (Est. EPS)`
                                                    )
                                                ) : '-'}
                                            </p>
                                        </div>
                                        <div className="bg-indigo-50 p-3 rounded-lg border border-indigo-100">
                                            <p className="text-[10px] font-bold text-indigo-400 uppercase mb-1">2 Yr Forward P/E</p>
                                            <div className="text-xl font-black text-indigo-700">
                                                {analyticsData?.price && analyticsData?.eps && editingGrowth ? (
                                                    (analyticsData.price / (analyticsData.eps * Math.pow(1 + parseFloat(editingGrowth) / 100, 2))).toFixed(2)
                                                ) : '-'}
                                            </div>
                                            <p className="text-[9px] text-indigo-400 font-bold mt-1">
                                                {analyticsData?.price && analyticsData?.eps && editingGrowth ? (
                                                    `₹${analyticsData.price.toFixed(2)} / ${(analyticsData.eps * Math.pow(1 + parseFloat(editingGrowth) / 100, 2)).toFixed(2)} (Est. EPS)`
                                                ) : '-'}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Read-only TTM EPS display for reference */}
                                    {analyticsData?.eps && (
                                        <p className="text-[10px] text-slate-400 mt-3 text-right">
                                            Based on TTM EPS: <span className="font-bold text-slate-600">{analyticsData.eps}</span>
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}

                        {analyticsData?.updated_at && (
                            <div className="absolute bottom-2 right-4 text-[9px] text-slate-300">
                                Last Analytics Update: {new Date(analyticsData.updated_at).toLocaleString()}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Add Equity Modal */}
            {isaddModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-900 uppercase">Add New Holding</h3>
                            <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <form onSubmit={handleAddSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Scrip Name</label>
                                    <input required type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Reliance Industries"
                                        value={newEquity.scrip_name} onChange={e => setNewEquity({ ...newEquity, scrip_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Ticker Symbol</label>
                                    <input required type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold uppercase text-slate-900" placeholder="e.g. RELIANCE"
                                        value={newEquity.symbol} onChange={e => setNewEquity({ ...newEquity, symbol: e.target.value.toUpperCase() })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Instrument Type</label>
                                    <select className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newEquity.instrument_type} onChange={e => setNewEquity({ ...newEquity, instrument_type: e.target.value })}>
                                        <option value="Stock">Stock</option>
                                        <option value="ETF">ETF</option>
                                        <option value="REIT">REIT</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Exchange</label>
                                    <select className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newEquity.exchange} onChange={e => setNewEquity({ ...newEquity, exchange: e.target.value as "NSE" | "BSE" })}>
                                        <option value="NSE">NSE</option>
                                        <option value="BSE">BSE</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Quantity</label>
                                    <input required type="number" min="1" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newEquity.quantity} onChange={e => setNewEquity({ ...newEquity, quantity: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Buy Price</label>
                                    <input required type="number" step="0.01" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newEquity.buy_price} onChange={e => setNewEquity({ ...newEquity, buy_price: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Buy Date</label>
                                    <input type="date" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={newEquity.buy_date} onChange={e => setNewEquity({ ...newEquity, buy_date: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">ISIN</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold placeholder:font-normal text-slate-900" placeholder="Optional"
                                        value={newEquity.isin} onChange={e => setNewEquity({ ...newEquity, isin: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Broker</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Zerodha"
                                        value={newEquity.broker} onChange={e => setNewEquity({ ...newEquity, broker: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Portfolio Holder</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Self, Family"
                                        value={newEquity.holder} onChange={e => setNewEquity({ ...newEquity, holder: e.target.value })} />
                                </div>
                            </div>
                            <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 transition-colors mt-2 uppercase text-sm tracking-wider">
                                Add Scrip
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Sell Equity Modal */}
            {isSellModalOpen && sellingEquity && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-900 uppercase">Mark as Sold</h3>
                            <button onClick={() => { setIsSellModalOpen(false); setSellingEquity(null); }} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <div className="mb-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Selling Holding</p>
                            <p className="text-lg font-black text-slate-900">{sellingEquity.scrip_name || sellingEquity.symbol}</p>
                            <p className="text-sm font-bold text-slate-500">{sellingEquity.quantity} Shares</p>
                        </div>
                        <form onSubmit={handleSellSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Quantity to Sell (Max: {sellingEquity.quantity})</label>
                                <input required type="number" min="1" max={sellingEquity.quantity} className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                    value={sellForm.quantity} onChange={e => setSellForm({ ...sellForm, quantity: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Selling Price (Per Share)</label>
                                <input required type="number" step="0.01" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                    value={sellForm.sell_price} onChange={e => setSellForm({ ...sellForm, sell_price: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Selling Date</label>
                                <input required type="date" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                    value={sellForm.sell_date} onChange={e => setSellForm({ ...sellForm, sell_date: e.target.value })} />
                            </div>
                            <button type="submit" className="w-full bg-amber-600 text-white font-bold py-3 rounded-xl hover:bg-amber-700 transition-colors mt-2 uppercase text-sm tracking-wider">
                                Confirm Sale
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit Equity Modal */}
            {isEditModalOpen && editingEquity && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white rounded-2xl w-full max-w-2xl p-6 shadow-2xl">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-900 uppercase">Edit Holding</h3>
                            <button onClick={() => { setIsEditModalOpen(false); setEditingEquity(null); }} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <form onSubmit={handleEditSubmit} className="space-y-4">
                            {/* ... grid contents ... */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Scrip Name</label>
                                    <input required type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingEquity.scrip_name || ""} onChange={e => setEditingEquity({ ...editingEquity, scrip_name: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Ticker Symbol</label>
                                    <input required type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold uppercase text-slate-900"
                                        value={editingEquity.symbol} onChange={e => setEditingEquity({ ...editingEquity, symbol: e.target.value.toUpperCase() })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Instrument Type</label>
                                    <select className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingEquity.instrument_type || "Stock"} onChange={e => setEditingEquity({ ...editingEquity, instrument_type: e.target.value })}>
                                        <option value="Stock">Stock</option>
                                        <option value="ETF">ETF</option>
                                        <option value="REIT">REIT</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Exchange</label>
                                    <select className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingEquity.exchange} onChange={e => setEditingEquity({ ...editingEquity, exchange: e.target.value as "NSE" | "BSE" })}>
                                        <option value="NSE">NSE</option>
                                        <option value="BSE">BSE</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Quantity</label>
                                    <input required type="number" min="1" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingEquity.quantity} onChange={e => setEditingEquity({ ...editingEquity, quantity: Number(e.target.value) })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Buy Price</label>
                                    <input required type="number" step="0.01" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingEquity.buy_price} onChange={e => setEditingEquity({ ...editingEquity, buy_price: Number(e.target.value) })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Buy Date</label>
                                    <input type="date" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900"
                                        value={editingEquity.buy_date} onChange={e => setEditingEquity({ ...editingEquity, buy_date: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">ISIN</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="Optional"
                                        value={editingEquity.isin || ""} onChange={e => setEditingEquity({ ...editingEquity, isin: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Broker</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Zerodha"
                                        value={editingEquity.broker || ""} onChange={e => setEditingEquity({ ...editingEquity, broker: e.target.value })} />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Portfolio Holder</label>
                                    <input type="text" className="w-full rounded-lg border-slate-200 p-2.5 text-sm font-bold text-slate-900" placeholder="e.g. Self, Family"
                                        value={editingEquity.holder || ""} onChange={e => setEditingEquity({ ...editingEquity, holder: e.target.value })} />
                                </div>
                            </div>
                            <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 transition-colors mt-2 uppercase text-sm tracking-wider">
                                Save Changes
                            </button>
                        </form>
                    </div>
                </div>
            )}
            {/* Mobile FAB for Add Scrip - REMOVED per user request */}
        </div>
    );
}

