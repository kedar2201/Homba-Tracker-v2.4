import { useState, useEffect, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { Plus, ChevronDown, Trash2, X, Download, Edit } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../components/ui/data-table";
import api from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";

type FixedDeposit = {
    id: number;
    bank_name: string;
    depositor_name?: string;
    depositor_code?: string;
    fd_code: string;
    principal: number;
    interest_rate: number;
    start_date: string;
    maturity_date: string;
    maturity_value?: number;
    fy_interest?: number;
    compounding_frequency: string;
    payout_type: string;
    tds_applicable: boolean;
    tds_rate: number;
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

export default function FixedDepositsPage() {
    const location = useLocation();
    const query = new URLSearchParams(location.search);
    const groupField = query.get("group"); // 'bank' or 'depositor'

    // FY Logic: Current month > 3 means FY is current year, else last year
    const currentYear = new Date().getFullYear();
    const currentFY = (new Date().getMonth() + 1) > 3 ? currentYear : currentYear - 1;

    const [data, setData] = useState<FixedDeposit[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
    const [selectedFY, setSelectedFY] = useState(currentFY);
    const [showAddModal, setShowAddModal] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingFd, setEditingFd] = useState<FixedDeposit | null>(null);

    // Form State for Single FD
    const [newFd, setNewFd] = useState({
        bank_name: "",
        depositor_name: "",
        depositor_code: "",
        fd_code: "",
        principal: 0,
        interest_rate: 0,
        start_date: new Date().toISOString().split('T')[0],
        maturity_date: "",
        compounding_frequency: "Yearly",
        payout_type: "Cumulative",
        tds_applicable: false,
        tds_rate: 0
    });

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await api.get(`/fixed-deposits/?fy_year=${selectedFY}`);
            setData(res.data);
        } catch (err) {
            console.error("Failed to fetch FDs", err);
            setError("Failed to load fixed deposits.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedFY]);

    const activeData = useMemo(() => {
        const fyStart = new Date(selectedFY, 3, 1); // April 1st
        const fyEnd = new Date(selectedFY + 1, 2, 31); // March 31st

        return data.filter(item => {
            const start = new Date(item.start_date);
            const maturity = new Date(item.maturity_date);

            // Overlap check: FD started before FY end AND matured after FY start
            return start <= fyEnd && maturity >= fyStart;
        });
    }, [data, selectedFY]);

    const handleDelete = async (id: number) => {
        if (!window.confirm("Are you sure you want to remove this Fixed Deposit? This action cannot be undone.")) {
            return;
        }
        try {
            await api.delete(`/fixed-deposits/${id}`);
            fetchData();
        } catch (err) {
            console.error("Delete failed", err);
            alert("Failed to delete Fixed Deposit.");
        }
    };

    const handleAddFd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post("/fixed-deposits/", newFd);
            setShowAddModal(false);
            fetchData();
            setNewFd({
                bank_name: "",
                depositor_name: "",
                depositor_code: "",
                fd_code: "",
                principal: 0,
                interest_rate: 0,
                start_date: new Date().toISOString().split('T')[0],
                maturity_date: "",
                compounding_frequency: "Yearly",
                payout_type: "Cumulative",
                tds_applicable: false,
                tds_rate: 0
            });
        } catch (err) {
            console.error("Failed to add FD", err);
            alert("Error adding Fixed Deposit. Check details.");
        }
    };

    const handleEdit = (fd: FixedDeposit) => {
        const cleanFd = { ...fd };
        if (cleanFd.start_date) {
            cleanFd.start_date = cleanFd.start_date.split('T')[0];
        }
        if (cleanFd.maturity_date) {
            cleanFd.maturity_date = cleanFd.maturity_date.split('T')[0];
        }
        setEditingFd(cleanFd);
        setIsEditModalOpen(true);
    };

    const handleEditSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingFd) return;
        try {
            await api.put(`/fixed-deposits/${editingFd.id}`, {
                bank_name: editingFd.bank_name,
                depositor_name: editingFd.depositor_name,
                depositor_code: editingFd.depositor_code,
                fd_code: editingFd.fd_code,
                principal: editingFd.principal,
                interest_rate: editingFd.interest_rate,
                start_date: editingFd.start_date,
                maturity_date: editingFd.maturity_date,
                compounding_frequency: editingFd.compounding_frequency,
                payout_type: editingFd.payout_type,
                tds_applicable: editingFd.tds_applicable,
                tds_rate: editingFd.tds_rate
            });
            setIsEditModalOpen(false);
            setEditingFd(null);
            fetchData();
        } catch (err) {
            console.error("Failed to update FD", err);
            alert("Failed to update Fixed Deposit");
        }
    };

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        const exportData = data.map(item => ({
            'Bank': item.bank_name,
            'Depositor': item.depositor_name || '-',
            'FD Code': item.fd_code,
            'Principal': item.principal,
            'Interest Rate': item.interest_rate,
            'Start Date': new Date(item.start_date).toLocaleDateString(),
            'Maturity Date': new Date(item.maturity_date).toLocaleDateString(),
            'Maturity Value': item.maturity_value || '-',
            'FY Interest': item.fy_interest || '-'
        }));

        if (format === 'pdf') {
            exportToPDF(exportData, ['Bank', 'Depositor', 'FD Code', 'Principal', 'Interest Rate', 'Start Date', 'Maturity Date', 'Maturity Value', 'FY Interest'], 'Fixed Deposits');
        } else if (format === 'excel') {
            exportToExcel(exportData, 'Fixed_Deposits');
        } else {
            exportToCSV(exportData, 'Fixed_Deposits');
        }
    };

    // Totals Calculation
    const fdTotals = useMemo(() => {
        let principal = 0;
        let fyInterest = 0;
        activeData.forEach(item => {
            principal += item.principal;
            fyInterest += (item.fy_interest || 0);
        });
        return { principal, fyInterest };
    }, [activeData]);

    // Grouping Logic
    const groupedData = useMemo(() => {
        if (!groupField) return null;
        const groups: Record<string, { totalPrincipal: number, totalFYInterest: number, items: FixedDeposit[] }> = {};

        activeData.forEach(item => {
            let rawKey = groupField === 'bank' ? item.bank_name : (item.depositor_name || "Unknown");
            const key = getDisplayName(rawKey);

            if (!groups[key]) {
                groups[key] = { totalPrincipal: 0, totalFYInterest: 0, items: [] };
            }
            groups[key].items.push(item);
            groups[key].totalPrincipal += item.principal;
            groups[key].totalFYInterest += (item.fy_interest || 0);
        });

        return Object.entries(groups).sort((a, b) => b[1].totalPrincipal - a[1].totalPrincipal);
    }, [activeData, groupField]);

    const columns: ColumnDef<FixedDeposit>[] = [
        {
            accessorKey: "depositor_name",
            header: "Depositor",
            cell: ({ row }) => (
                <div className="flex flex-col">
                    <span className="font-medium text-slate-900">{row.original.depositor_name || "-"}</span>
                    <span className="text-xs text-slate-500 font-bold">{row.original.depositor_code}</span>
                </div>
            )
        },
        {
            accessorKey: "bank_name",
            header: "Bank",
            cell: ({ row }) => <span className="text-slate-900 font-medium">{row.original.bank_name}</span>
        },
        {
            accessorKey: "fd_code",
            header: "FD No",
            cell: ({ row }) => <span className="text-slate-700">{row.original.fd_code}</span>
        },
        {
            accessorKey: "principal",
            header: "Invested Amount",
            cell: ({ row }) => <span className="text-slate-900 font-bold">₹{row.original.principal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        },
        {
            accessorKey: "interest_rate",
            header: "Rate (%)",
            cell: ({ row }) => <span className="text-blue-700 font-bold">{row.original.interest_rate.toFixed(2)}%</span>
        },
        {
            accessorKey: "compounding_frequency",
            header: "Interval",
            cell: ({ row }) => <span className="capitalize text-xs font-medium text-slate-500">{row.original.compounding_frequency}</span>
        },
        {
            accessorKey: "fy_interest",
            header: `FY ${selectedFY}-${(selectedFY + 1).toString().slice(-2)} Int.`,
            cell: ({ row }) => (
                <span className="font-semibold text-emerald-600">
                    ₹{(row.original.fy_interest || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
            )
        },
        {
            accessorKey: "maturity_date",
            header: "Maturity Date",
            cell: ({ row }) => <span className="text-slate-600 font-medium">{row.original.maturity_date}</span>
        },
        {
            id: "actions",
            header: "Actions",
            enableSorting: false,
            cell: ({ row }) => (
                <div className="flex gap-2">
                    <button
                        onClick={() => handleEdit(row.original)}
                        className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"
                        title="Edit"
                    >
                        <Edit className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => handleDelete(row.original.id)}
                        className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                        title="Delete"
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

    const yearOptions = [currentFY + 1, currentFY, currentFY - 1, currentFY - 2, currentFY - 3];

    return (
        <div className="space-y-6 pb-20">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div>
                    <h2 className="text-base sm:text-3xl lg:text-4xl font-black tracking-tight text-slate-900 uppercase">Fixed Deposits</h2>
                    <div className="flex items-center gap-2 mt-1">
                        <p className="text-slate-500 text-sm">Financial Year:</p>
                        <select
                            value={selectedFY}
                            onChange={(e) => setSelectedFY(parseInt(e.target.value))}
                            className="bg-transparent border-none text-indigo-600 font-bold focus:ring-0 p-0 cursor-pointer outline-none text-sm"
                        >
                            {yearOptions.map(y => (
                                <option key={y} value={y}>{y}-{(y + 1).toString().slice(-2)}</option>
                            ))}
                        </select>
                    </div>
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
                    <div className="flex w-full sm:w-auto gap-2">
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-white text-indigo-600 border border-indigo-200 px-4 py-2 rounded-xl hover:bg-indigo-50 transition-all font-bold text-xs shadow-sm uppercase"
                        >
                            <Plus className="w-4 h-4" />
                            <span>Add</span>
                        </button>
                        <Link
                            to="/fixed-deposits/upload"
                            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl hover:bg-indigo-700 transition-all font-bold text-xs shadow-sm uppercase"
                        >
                            <span>Bulk</span>
                        </Link>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-sm border border-slate-200">
                    <p className="text-slate-400 text-[9px] sm:text-[10px] font-black uppercase tracking-widest mb-1 sm:mb-2 leading-tight">Active Principal in FY {selectedFY}-{(selectedFY + 1).toString().slice(-2)}</p>
                    <h3 className="text-sm sm:text-xl lg:text-2xl font-black text-indigo-600">₹{fdTotals.principal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
                <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-sm border border-slate-200">
                    <p className="text-slate-400 text-[9px] sm:text-[10px] font-black uppercase tracking-widest mb-1 sm:mb-2 leading-tight">Interest Accrued in FY {selectedFY}-{(selectedFY + 1).toString().slice(-2)}</p>
                    <h3 className="text-sm sm:text-xl lg:text-2xl font-black text-emerald-600">₹{fdTotals.fyInterest.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                </div>
            </div>

            {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">{error}</div>}

            {!groupField ? (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                    <DataTable columns={columns} data={activeData} />
                </div>
            ) : (
                <div className="space-y-4">
                    {groupedData?.map(([name, group]) => (
                        <div key={name} className="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden group transition-all hover:border-indigo-300">
                            <button
                                onClick={() => setExpandedGroup(expandedGroup === name ? null : name)}
                                className={`w-full flex items-center justify-between p-6 transition-colors ${expandedGroup === name ? "bg-indigo-50/50" : "hover:bg-slate-50"}`}
                            >
                                <div className="flex items-center gap-3 sm:gap-4">
                                    <div className={`p-1.5 sm:p-2 rounded-xl shadow-sm transition-all ${expandedGroup === name ? 'bg-indigo-600 text-white shadow-indigo-200' : 'bg-slate-100 text-slate-400'}`}>
                                        <ChevronDown className={`w-4 h-4 sm:w-6 sm:h-6 transition-transform duration-300 ${expandedGroup === name ? '' : '-rotate-90'}`} />
                                    </div>
                                    <div className="text-left">
                                        <span className="font-black text-xs sm:text-xl text-slate-900 uppercase tracking-tight">{name} ({group.items.length})</span>
                                        <p className="text-[9px] sm:text-xs font-bold text-slate-500 mt-0.5 sm:mt-1 uppercase tracking-widest">Deposits Portfolio</p>
                                    </div>
                                </div>
                                <div className="flex gap-4 sm:gap-12 text-right items-center">
                                    <div className="hidden sm:block">
                                        <p className="text-[9px] sm:text-[10px] text-slate-400 uppercase font-black tracking-widest mb-0.5 sm:mb-1">Total Principal</p>
                                        <p className="text-sm sm:text-base lg:text-lg font-black text-slate-900">₹{group.totalPrincipal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                    </div>
                                    <div>
                                        <p className="text-[9px] sm:text-[10px] text-slate-400 uppercase font-black tracking-widest mb-0.5 sm:mb-1">FY Interest</p>
                                        <p className="text-sm sm:text-xl lg:text-2xl font-black text-indigo-700">₹{group.totalFYInterest.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                    </div>
                                </div>
                            </button>

                            {expandedGroup === name && (
                                <div className="p-4 bg-slate-50/30 border-t border-slate-100 animate-in fade-in slide-in-from-top-2">
                                    <DataTable columns={columns} data={group.items} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Add FD Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200">
                        <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50">
                            <h3 className="text-xl font-bold text-slate-900 uppercase tracking-tight">Add Single Fixed Deposit</h3>
                            <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <form onSubmit={handleAddFd} className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[85vh] overflow-y-auto">
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Bank Name</label>
                                <input required className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.bank_name} onChange={e => setNewFd({ ...newFd, bank_name: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">FD Number</label>
                                <input required className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.fd_code} onChange={e => setNewFd({ ...newFd, fd_code: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Invested Amount (Principal)</label>
                                <input required type="number" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.principal} onChange={e => setNewFd({ ...newFd, principal: parseFloat(e.target.value) })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Interest Rate (%)</label>
                                <input required type="number" step="0.01" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.interest_rate} onChange={e => setNewFd({ ...newFd, interest_rate: parseFloat(e.target.value) })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Start Date</label>
                                <input type="date" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.start_date} onChange={e => setNewFd({ ...newFd, start_date: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Maturity Date</label>
                                <input type="date" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.maturity_date} onChange={e => setNewFd({ ...newFd, maturity_date: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Compounding Interval</label>
                                <select className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.compounding_frequency} onChange={e => setNewFd({ ...newFd, compounding_frequency: e.target.value })}>
                                    <option value="Monthly">Monthly</option>
                                    <option value="Quarterly">Quarterly</option>
                                    <option value="Half-Yearly">Half-Yearly</option>
                                    <option value="Yearly">Yearly</option>
                                    <option value="On Maturity">On Maturity</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Payout Type</label>
                                <select className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.payout_type} onChange={e => setNewFd({ ...newFd, payout_type: e.target.value })}>
                                    <option value="Cumulative">Cumulative</option>
                                    <option value="Payout">Regular Payout</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">TDS Applicable</label>
                                <select className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={String(newFd.tds_applicable)} onChange={e => setNewFd({ ...newFd, tds_applicable: e.target.value === "true" })}>
                                    <option value="false">No</option>
                                    <option value="true">Yes</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">TDS Rate (%)</label>
                                <input type="number" step="0.1" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.tds_rate} onChange={e => setNewFd({ ...newFd, tds_rate: parseFloat(e.target.value) })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Depositor Name</label>
                                <input className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.depositor_name} onChange={e => setNewFd({ ...newFd, depositor_name: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Depositor Code</label>
                                <input className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={newFd.depositor_code} onChange={e => setNewFd({ ...newFd, depositor_code: e.target.value })} />
                            </div>

                            <div className="md:col-span-2 pt-4 flex gap-3">
                                <button type="submit" className="flex-1 bg-indigo-600 text-white font-black py-3 rounded-xl hover:bg-indigo-700 transition-all shadow-lg uppercase tracking-wider text-sm">
                                    Create Fixed Deposit
                                </button>
                                <button type="button" onClick={() => setShowAddModal(false)} className="px-6 py-3 border border-slate-200 rounded-xl font-bold text-slate-600 hover:bg-slate-50 uppercase text-xs tracking-widest">
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit FD Modal */}
            {isEditModalOpen && editingFd && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200">
                        <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50">
                            <h3 className="text-xl font-bold text-slate-900 uppercase tracking-tight">Edit Fixed Deposit</h3>
                            <button onClick={() => { setIsEditModalOpen(false); setEditingFd(null); }} className="text-slate-400 hover:text-slate-600">
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        <form onSubmit={handleEditSubmit} className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[85vh] overflow-y-auto">
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Bank Name</label>
                                <input required className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.bank_name} onChange={e => setEditingFd({ ...editingFd, bank_name: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">FD Number</label>
                                <input required className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.fd_code} onChange={e => setEditingFd({ ...editingFd, fd_code: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Invested Amount (Principal)</label>
                                <input required type="number" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.principal} onChange={e => setEditingFd({ ...editingFd, principal: parseFloat(e.target.value) })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Interest Rate (%)</label>
                                <input required type="number" step="0.01" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.interest_rate} onChange={e => setEditingFd({ ...editingFd, interest_rate: parseFloat(e.target.value) })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Start Date</label>
                                <input type="date" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.start_date} onChange={e => setEditingFd({ ...editingFd, start_date: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Maturity Date</label>
                                <input type="date" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.maturity_date} onChange={e => setEditingFd({ ...editingFd, maturity_date: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Compounding Interval</label>
                                <select className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.compounding_frequency} onChange={e => setEditingFd({ ...editingFd, compounding_frequency: e.target.value })}>
                                    <option value="Monthly">Monthly</option>
                                    <option value="Quarterly">Quarterly</option>
                                    <option value="Half-Yearly">Half-Yearly</option>
                                    <option value="Yearly">Yearly</option>
                                    <option value="On Maturity">On Maturity</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Payout Type</label>
                                <select className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.payout_type} onChange={e => setEditingFd({ ...editingFd, payout_type: e.target.value })}>
                                    <option value="Cumulative">Cumulative</option>
                                    <option value="Payout">Regular Payout</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">TDS Applicable</label>
                                <select className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={String(editingFd.tds_applicable)} onChange={e => setEditingFd({ ...editingFd, tds_applicable: e.target.value === "true" })}>
                                    <option value="false">No</option>
                                    <option value="true">Yes</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">TDS Rate (%)</label>
                                <input type="number" step="0.1" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.tds_rate} onChange={e => setEditingFd({ ...editingFd, tds_rate: parseFloat(e.target.value) })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Depositor Name</label>
                                <input className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.depositor_name || ""} onChange={e => setEditingFd({ ...editingFd, depositor_name: e.target.value })} />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Depositor Code</label>
                                <input className="w-full px-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm text-slate-900"
                                    value={editingFd.depositor_code || ""} onChange={e => setEditingFd({ ...editingFd, depositor_code: e.target.value })} />
                            </div>

                            <div className="md:col-span-2 pt-4 flex gap-3">
                                <button type="submit" className="flex-1 bg-indigo-600 text-white font-black py-3 rounded-xl hover:bg-indigo-700 transition-all shadow-lg uppercase tracking-wider text-sm">
                                    Update Fixed Deposit
                                </button>
                                <button type="button" onClick={() => { setIsEditModalOpen(false); setEditingFd(null); }} className="px-6 py-3 border border-slate-200 rounded-xl font-bold text-slate-600 hover:bg-slate-50 uppercase text-xs tracking-widest">
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
