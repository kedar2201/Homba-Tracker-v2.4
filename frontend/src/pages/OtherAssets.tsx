import { useState, useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
    ChevronRight,
    ChevronDown,
    Building2,
    ShieldCheck,
    Coins,
    Landmark,
    Briefcase,
    Pencil,
    X,
    Save,
    Plus,
    PlusCircle,
    Download
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../components/ui/data-table";
import api from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";

type OtherAsset = {
    id?: number;
    category: string;
    name: string;
    institution?: string;
    valuation: number;
    description?: string;
};

const CATEGORY_ICONS: Record<string, any> = {
    INSURANCE: ShieldCheck,
    RETIREMENT: Landmark,
    REAL_ESTATE: Building2,
    GOLD: Coins,
    BOND: Landmark,
    SAVINGS: Briefcase,
    MISC: Briefcase
};

const LIQUIDABLE_CATEGORIES = ["INSURANCE", "RETIREMENT", "GOLD", "BOND", "SAVINGS"];
const OTHER_CATEGORIES = ["REAL_ESTATE", "MISC"];

export default function OtherAssetsPage() {
    const location = useLocation();
    const query = new URLSearchParams(location.search);
    const filterCat = query.get("cat");

    const isLiquidable = location.pathname === "/liquidable-assets";
    const availableCategories = isLiquidable ? LIQUIDABLE_CATEGORIES : OTHER_CATEGORIES;
    const pageTitle = isLiquidable ? "Liquidable Assets" : "Other Assets";
    const pageDesc = isLiquidable ? "Insurance, Retirement, Gold, and Savings Portfolios" : "Real Estate and Miscellaneous Assets";

    const [data, setData] = useState<OtherAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedGroup, setExpandedGroup] = useState<string | null>(filterCat);
    const [modalAsset, setModalAsset] = useState<OtherAsset | null>(null);
    const [saving, setSaving] = useState(false);

    const fetchAssets = () => {
        api.get("/other-assets/")
            .then((res: any) => setData(res.data))
            .catch((err: any) => console.error(err))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchAssets();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!modalAsset) return;

        setSaving(true);
        try {
            if (modalAsset.id) {
                await api.put(`/other-assets/${modalAsset.id}`, modalAsset);
            } else {
                await api.post("/other-assets/", modalAsset);
            }
            setModalAsset(null);
            fetchAssets();
        } catch (err) {
            console.error(err);
            alert("Failed to save asset");
        } finally {
            setSaving(false);
        }
    };

    const openCreateModal = (category?: string) => {
        setModalAsset({
            category: category || (isLiquidable ? "SAVINGS" : "MISC"),
            name: "",
            institution: "",
            valuation: 0,
            description: ""
        });
    };

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        const exportData = data.map(item => ({
            'Category': item.category,
            'Name': item.name,
            'Institution': item.institution || '-',
            'Valuation': item.valuation,
            'Description': item.description || '-'
        }));

        if (format === 'pdf') {
            exportToPDF(exportData, ['Category', 'Name', 'Institution', 'Valuation', 'Description'], pageTitle);
        } else if (format === 'excel') {
            exportToExcel(exportData, pageTitle.replace(/\s+/g, '_'));
        } else {
            exportToCSV(exportData, pageTitle.replace(/\s+/g, '_'));
        }
    };

    const groupedData = useMemo(() => {
        const groups: Record<string, { total: number, items: OtherAsset[] }> = {};
        data.forEach(item => {
            if (!availableCategories.includes(item.category)) return;

            if (!groups[item.category]) {
                groups[item.category] = { total: 0, items: [] };
            }
            groups[item.category].items.push(item);
            groups[item.category].total += item.valuation;
        });
        return Object.entries(groups).sort((a, b) => b[1].total - a[1].total);
    }, [data, availableCategories]);

    const columns: ColumnDef<OtherAsset>[] = [
        {
            accessorKey: "name",
            header: "Asset Name",
            cell: ({ row }) => <span className="font-bold text-slate-900">{row.original.name}</span>
        },
        {
            accessorKey: "institution",
            header: "Institution",
            cell: ({ row }) => <span className="text-slate-700 font-medium">{row.original.institution || "-"}</span>
        },
        {
            accessorKey: "valuation",
            header: "Valuation",
            cell: ({ row }) => <span className="font-black text-slate-900">₹{row.original.valuation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        },
        {
            accessorKey: "description",
            header: "Details",
            cell: ({ row }) => <span className="text-slate-600 text-sm">{row.original.description || "-"}</span>
        },
        {
            id: "actions",
            header: "Action",
            cell: ({ row }) => (
                <button
                    onClick={() => setModalAsset(row.original)}
                    className="p-1.5 hover:bg-indigo-50 text-indigo-600 rounded-md transition-colors"
                    title="Edit Asset"
                >
                    <Pencil className="w-4 h-4" />
                </button>
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
                    <h2 className="text-base sm:text-3xl lg:text-4xl font-black tracking-tight text-slate-900 uppercase">{pageTitle}</h2>
                    <p className="text-slate-500 text-[9px] sm:text-sm lg:text-base">{pageDesc}</p>
                </div>
                <div className="flex flex-wrap gap-2">
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
                    <button
                        onClick={() => openCreateModal()}
                        className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl hover:bg-indigo-700 transition-all font-bold text-xs shadow-sm uppercase"
                    >
                        <PlusCircle className="w-5 h-5" />
                        <span>Add New Asset</span>
                    </button>
                </div>
            </div>

            <div className="space-y-4">
                {groupedData.map(([cat, group]) => {
                    const Icon = CATEGORY_ICONS[cat] || Briefcase;
                    const isFiltered = filterCat ? filterCat === cat : true;
                    if (!isFiltered) return null;

                    return (
                        <div key={cat} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden group">
                            <div className="flex items-center pr-5">
                                <button
                                    onClick={() => setExpandedGroup(expandedGroup === cat ? null : cat)}
                                    className={`flex-1 flex items-center justify-between p-4 sm:p-5 hover:bg-slate-50 transition-colors ${expandedGroup === cat ? "bg-slate-50 border-b border-slate-100" : ""
                                        }`}
                                >
                                    <div className="flex items-center gap-3 sm:gap-4">
                                        <div className="bg-indigo-600 p-2 sm:p-2.5 rounded-xl text-white">
                                            <Icon className="w-5 h-5 sm:w-6 sm:h-6" />
                                        </div>
                                        <div className="text-left">
                                            <h3 className="font-bold text-slate-900 text-xs sm:text-xl tracking-tight uppercase">{cat.replace("_", " ")}</h3>
                                            <p className="text-[9px] sm:text-sm text-slate-500 font-medium">{group.items.length} Records</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-4 sm:gap-12 text-right items-center">
                                        <div>
                                            <p className="text-[8px] sm:text-[10px] text-slate-400 uppercase font-black tracking-widest mb-0.5 sm:mb-1">Total Value</p>
                                            <p className="text-sm sm:text-xl lg:text-2xl font-black text-indigo-600">₹{group.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                        </div>
                                        <div className="bg-slate-100 p-1 rounded-full text-slate-400 group-hover:text-indigo-600 transition-colors">
                                            {expandedGroup === cat ? <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5" /> : <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5" />}
                                        </div>
                                    </div>
                                </button>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        openCreateModal(cat);
                                    }}
                                    className="ml-4 p-2 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-600 hover:text-white transition-all shadow-sm group/btn"
                                    title={`Add to ${cat.replace("_", " ")}`}
                                >
                                    <Plus className="w-5 h-5" />
                                </button>
                            </div>
                            {(expandedGroup === cat || filterCat === cat) && (
                                <div className="p-4 bg-slate-50/20">
                                    <DataTable columns={columns} data={group.items} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Modal (Create or Edit) */}
            {modalAsset && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg border max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between p-6 border-b bg-slate-50/50">
                            <h3 className="text-xl font-black text-slate-900 uppercase tracking-tight">
                                {modalAsset.id ? "Edit Asset Entry" : "Create New Asset"}
                            </h3>
                            <button onClick={() => setModalAsset(null)} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Category</label>
                                    <select
                                        className="w-full p-2.5 bg-slate-50 border rounded-lg font-medium text-slate-900"
                                        value={modalAsset.category}
                                        onChange={(e: any) => setModalAsset({ ...modalAsset, category: e.target.value })}
                                    >
                                        {availableCategories.map(c => (
                                            <option key={c} value={c}>{c.replace("_", " ")}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Valuation (₹)</label>
                                    <input
                                        type="number"
                                        required
                                        className="w-full p-2.5 bg-slate-50 border rounded-lg font-bold text-slate-900"
                                        value={modalAsset.valuation}
                                        onChange={(e: any) => setModalAsset({ ...modalAsset, valuation: parseFloat(e.target.value) })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">Asset Name</label>
                                <input
                                    required
                                    placeholder="e.g. PPF Account, Family Flat, Gold coins"
                                    className="w-full p-2.5 bg-slate-50 border rounded-lg font-medium text-slate-900"
                                    value={modalAsset.name}
                                    onChange={(e: any) => setModalAsset({ ...modalAsset, name: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">Institution</label>
                                <input
                                    placeholder="e.g. SBI, LIC, Post Office"
                                    className="w-full p-2.5 bg-slate-50 border rounded-lg font-medium text-slate-900"
                                    value={modalAsset.institution || ""}
                                    onChange={(e: any) => setModalAsset({ ...modalAsset, institution: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">Details / Description</label>
                                <textarea
                                    placeholder="Any additional details..."
                                    className="w-full p-2.5 bg-slate-50 border rounded-lg font-medium text-slate-500 text-xs h-20"
                                    value={modalAsset.description || ""}
                                    onChange={(e: any) => setModalAsset({ ...modalAsset, description: e.target.value })}
                                />
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setModalAsset(null)}
                                    className="flex-1 px-4 py-3 rounded-xl border font-bold text-slate-600 hover:bg-slate-50 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    disabled={saving}
                                    className="flex-1 px-4 py-3 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {saving ? <span className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></span> : <Save className="w-4 h-4" />}
                                    {modalAsset.id ? "Save Changes" : "Create Asset"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
