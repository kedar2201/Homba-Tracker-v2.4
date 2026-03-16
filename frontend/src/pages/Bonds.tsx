import { useState, useEffect, useMemo } from "react";
import { Lock, RefreshCw, Info } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../components/ui/data-table";
import api from "../lib/api";

type Bond = {
    id: number | string;
    name: string;
    symbol: string;
    quantity: number;
    buy_price: number;
    current_price: number;
    current_value: number;
    invested_value: number;
    pnl: number;
    pnl_percentage: number;
    type: "Equity-based" | "MF-based";
    holder: string;
};

export default function BondsPage() {
    const [data, setData] = useState<Bond[]>([]);
    const [loading, setLoading] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [eqRes, mfRes] = await Promise.all([
                api.get("/equity/"),
                api.get("/mutual-funds/")
            ]);

            const equityBonds: Bond[] = eqRes.data
                .filter((e: any) => e.symbol.startsWith("SGB"))
                .map((e: any) => ({
                    id: `eq-${e.id}`,
                    name: e.scrip_name || e.symbol,
                    symbol: e.symbol,
                    quantity: e.quantity,
                    buy_price: e.buy_price,
                    current_price: e.current_price || e.buy_price,
                    current_value: e.current_value,
                    invested_value: e.invested_value,
                    pnl: e.pnl,
                    pnl_percentage: e.pnl_percentage,
                    type: "Equity-based",
                    holder: e.holder || "-"
                }));

            const mfBonds: Bond[] = mfRes.data
                .filter((m: any) => m.interest_rate > 0 || m.scheme_name.toLowerCase().includes("sgb"))
                .map((m: any) => ({
                    id: `mf-${m.id}`,
                    name: m.scheme_name,
                    symbol: m.amfi_code || "SGB",
                    quantity: m.units,
                    buy_price: m.invested_amount / m.units,
                    current_price: m.current_nav,
                    current_value: m.current_value,
                    invested_value: m.invested_amount,
                    pnl: m.pnl,
                    pnl_percentage: m.pnl_percentage,
                    type: "MF-based",
                    holder: m.holder || "-"
                }));

            setData([...equityBonds, ...mfBonds]);
            setLastUpdated(new Date());
        } catch (err) {
            console.error("Failed to fetch bonds:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const totals = useMemo(() => {
        const invested = data.reduce((sum, b) => sum + b.invested_value, 0);
        const current = data.reduce((sum, b) => sum + b.current_value, 0);
        const pnl = current - invested;
        const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;
        return { invested, current, pnl, pnlPct };
    }, [data]);

    const columns: ColumnDef<Bond>[] = [
        {
            accessorKey: "name",
            header: "Bond Name",
            cell: ({ row }) => (
                <div className="flex flex-col">
                    <span className="font-black text-slate-900 uppercase">{row.original.name}</span>
                    <span className="text-[10px] text-slate-500 font-bold uppercase">{row.original.symbol} • {row.original.type}</span>
                </div>
            )
        },
        {
            accessorKey: "quantity",
            header: "Qty / Units",
            cell: ({ row }) => <span className="text-slate-700 font-medium">{row.original.quantity.toLocaleString('en-IN')}</span>
        },
        {
            accessorKey: "buy_price",
            header: "Avg Price",
            cell: ({ row }) => <span className="text-slate-700">₹{row.original.buy_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
        },
        {
            accessorKey: "current_price",
            header: "Current Value",
            cell: ({ row }) => <span className="text-indigo-700 font-bold">₹{row.original.current_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
        },
        {
            accessorKey: "current_value",
            header: "Total Worth",
            cell: ({ row }) => <span className="font-black text-slate-900">₹{row.original.current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        },
        {
            accessorKey: "pnl",
            header: "P&L",
            cell: ({ row }) => (
                <div className={`font-black ${row.original.pnl >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                    {row.original.pnl >= 0 ? '+' : ''}₹{row.original.pnl.toLocaleString('en-IN')} ({row.original.pnl_percentage.toFixed(2)}%)
                </div>
            )
        },
        {
            accessorKey: "holder",
            header: "Holder",
            cell: ({ row }) => <span className="text-xs font-bold text-slate-500 uppercase">{row.original.holder}</span>
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
                    <h2 className="text-base sm:text-3xl lg:text-4xl font-black tracking-tight text-slate-900 uppercase flex items-center gap-2 sm:gap-3">
                        <Lock className="w-8 h-8 sm:w-12 sm:h-12 text-indigo-600" />
                        Bonds & Gold Bonds
                    </h2>
                    <p className="text-slate-500 text-[10px] sm:text-sm lg:text-base">Sovereign Gold Bonds and other fixed-income securities.</p>
                    {lastUpdated && (
                        <p className="text-[10px] text-slate-400 mt-1 font-bold">
                            LAST UPDATED: {lastUpdated.toLocaleTimeString()}
                        </p>
                    )}
                </div>
                <button
                    onClick={fetchData}
                    className="inline-flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl hover:bg-indigo-700 transition-all font-bold text-xs shadow-sm uppercase"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-sm border border-slate-200">
                    <p className="text-slate-400 text-[9px] sm:text-[10px] font-black uppercase tracking-widest mb-1 sm:mb-2">Total Bond Value</p>
                    <h3 className="text-sm sm:text-xl lg:text-2xl font-black text-indigo-600">₹{totals.current.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
                <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-sm border border-slate-200">
                    <p className="text-slate-400 text-[9px] sm:text-[10px] font-black uppercase tracking-widest mb-1 sm:mb-2">Total Invested</p>
                    <h3 className="text-sm sm:text-xl lg:text-2xl font-black text-slate-900">₹{totals.invested.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
                <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-sm border border-slate-200">
                    <p className="text-slate-400 text-[9px] sm:text-[10px] font-black uppercase tracking-widest mb-1 sm:mb-2">Overall P&L</p>
                    <h3 className={`text-sm sm:text-xl lg:text-2xl font-black ${totals.pnl >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {totals.pnl >= 0 ? '+' : ''}₹{Math.abs(totals.pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({totals.pnlPct.toFixed(2)}%)
                    </h3>
                </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3 text-blue-700">
                <Info className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <p className="text-xs font-semibold leading-relaxed">
                    Sovereign Gold Bonds (SGBs) are reflected here consolidated from your Equity and Mutual Fund holdings.
                    Valuations are based on the latest gold market prices or exchange LTP.
                </p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <DataTable columns={columns} data={data} />
            </div>
        </div>
    );
}
