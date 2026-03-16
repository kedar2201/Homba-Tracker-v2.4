import { useState, useEffect } from "react";
import { Download, ChevronDown, ChevronRight } from "lucide-react";
import api from "../lib/api";
import { exportToPDF, exportToExcel, exportToCSV } from "../lib/exportUtils";

type EquityByBroker = {
    holder: string;
    brokers: {
        broker_name: string;
        holdings: {
            symbol: string;
            quantity: number;
            current_price: number;
            current_value: number;
            invested_value: number;
            pnl: number;
            pnl_percentage: number;
        }[];
        total_value: number;
        total_invested: number;
        total_pnl: number;
    }[];
    holder_total: number;
};

type MFByAMC = {
    holder: string;
    amcs: {
        amc_name: string;
        funds: {
            scheme_name: string;
            units: number;
            current_nav: number;
            current_value: number;
            invested_amount: number;
            pnl: number;
            pnl_percentage: number;
        }[];
        total_value: number;
        total_invested: number;
        total_pnl: number;
    }[];
    holder_total: number;
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

export default function ReconciliationReport() {
    const [reportType, setReportType] = useState<'equity' | 'mutual-funds'>('equity');
    const [equityData, setEquityData] = useState<EquityByBroker[]>([]);
    const [mfData, setMfData] = useState<MFByAMC[]>([]);
    const [loading, setLoading] = useState(false);
    const [expandedHolder, setExpandedHolder] = useState<string | null>(null);
    const [expandedBrokerAMC, setExpandedBrokerAMC] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    const fetchEquityReconciliation = async () => {
        setLoading(true);
        try {
            const response = await api.get("/equity/");
            const equities = response.data;

            // Group by holder, then by broker
            const grouped: Record<string, EquityByBroker> = {};

            equities.forEach((equity: any) => {
                const holder = getDisplayName(equity.holder || "Unknown");
                const broker = equity.broker || "Unknown Broker";

                if (!grouped[holder]) {
                    grouped[holder] = {
                        holder,
                        brokers: [],
                        holder_total: 0
                    };
                }

                let brokerGroup = grouped[holder].brokers.find(b => b.broker_name === broker);
                if (!brokerGroup) {
                    brokerGroup = {
                        broker_name: broker,
                        holdings: [],
                        total_value: 0,
                        total_invested: 0,
                        total_pnl: 0
                    };
                    grouped[holder].brokers.push(brokerGroup);
                }

                const holding = {
                    symbol: equity.symbol,
                    quantity: equity.quantity,
                    current_price: equity.current_price || 0,
                    current_value: equity.current_value || 0,
                    invested_value: equity.invested_value || 0,
                    pnl: equity.pnl || 0,
                    pnl_percentage: equity.pnl_percentage || 0
                };

                brokerGroup.holdings.push(holding);
                brokerGroup.total_value += holding.current_value;
                brokerGroup.total_invested += holding.invested_value;
                brokerGroup.total_pnl += holding.pnl;
                grouped[holder].holder_total += holding.current_value;
            });

            setEquityData(Object.values(grouped));
            setLastUpdated(new Date());
        } catch (err) {
            console.error("Failed to fetch equity data", err);
        } finally {
            setLoading(false);
        }
    };

    const fetchMFReconciliation = async () => {
        setLoading(true);
        try {
            const response = await api.get("/mutual-funds/");
            const mfs = response.data;

            // Group by holder, then by AMC
            const grouped: Record<string, MFByAMC> = {};

            mfs.forEach((mf: any) => {
                const holder = getDisplayName(mf.holder || "Unknown");
                const amc = mf.amc_name || "Unknown AMC";

                if (!grouped[holder]) {
                    grouped[holder] = {
                        holder,
                        amcs: [],
                        holder_total: 0
                    };
                }

                let amcGroup = grouped[holder].amcs.find(a => a.amc_name === amc);
                if (!amcGroup) {
                    amcGroup = {
                        amc_name: amc,
                        funds: [],
                        total_value: 0,
                        total_invested: 0,
                        total_pnl: 0
                    };
                    grouped[holder].amcs.push(amcGroup);
                }

                const fund = {
                    scheme_name: mf.scheme_name,
                    units: mf.units,
                    current_nav: mf.current_nav || 0,
                    current_value: mf.current_value || 0,
                    invested_amount: mf.invested_amount || 0,
                    pnl: mf.pnl || 0,
                    pnl_percentage: mf.pnl_percentage || 0
                };

                amcGroup.funds.push(fund);
                amcGroup.total_value += fund.current_value;
                amcGroup.total_invested += fund.invested_amount;
                amcGroup.total_pnl += fund.pnl;
                grouped[holder].holder_total += fund.current_value;
            });

            setMfData(Object.values(grouped));
            setLastUpdated(new Date());
        } catch (err) {
            console.error("Failed to fetch MF data", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (reportType === 'equity') {
            fetchEquityReconciliation();
        } else {
            fetchMFReconciliation();
        }
        setExpandedHolder(null);
        setExpandedBrokerAMC(null);
    }, [reportType]);

    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        const data = reportType === 'equity' ? equityData : mfData;

        const exportData = reportType === 'equity'
            ? (data as EquityByBroker[]).flatMap(holder =>
                holder.brokers.flatMap(broker =>
                    broker.holdings.map(holding => ({
                        'Holder': holder.holder,
                        'Broker': broker.broker_name,
                        'Symbol': holding.symbol,
                        'Quantity': holding.quantity,
                        'Current Price': holding.current_price,
                        'Current Value': holding.current_value,
                        'Invested Value': holding.invested_value,
                        'P&L': holding.pnl,
                        'P&L %': holding.pnl_percentage
                    }))
                )
            )
            : (data as MFByAMC[]).flatMap(holder =>
                holder.amcs.flatMap(amc =>
                    amc.funds.map(fund => ({
                        'Holder': holder.holder,
                        'AMC': amc.amc_name,
                        'Scheme': fund.scheme_name,
                        'Units': fund.units,
                        'Current NAV': fund.current_nav,
                        'Current Value': fund.current_value,
                        'Invested Amount': fund.invested_amount,
                        'P&L': fund.pnl,
                        'P&L %': fund.pnl_percentage
                    }))
                )
            );

        const fileName = reportType === 'equity'
            ? 'Equity_Reconciliation_Report'
            : 'MutualFund_Reconciliation_Report';

        if (format === 'pdf') {
            const columns = reportType === 'equity'
                ? ['Holder', 'Broker', 'Symbol', 'Quantity', 'Current Price', 'Current Value', 'Invested Value', 'P&L', 'P&L %']
                : ['Holder', 'AMC', 'Scheme', 'Units', 'Current NAV', 'Current Value', 'Invested Amount', 'P&L', 'P&L %'];
            exportToPDF(exportData, columns, `${fileName}`);
        } else if (format === 'excel') {
            exportToExcel(exportData, fileName);
        } else {
            exportToCSV(exportData, fileName);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    const data = reportType === 'equity' ? equityData : mfData;

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div>
                    <h2 className="text-base sm:text-2xl lg:text-3xl font-black tracking-tight text-slate-900 uppercase">
                        Reconciliation Report
                    </h2>
                    <p className="text-slate-500 text-[10px] sm:text-sm lg:text-base">
                        Match your holdings with broker/AMC statements by holder and broker/AMC
                    </p>
                    {lastUpdated && (
                        <p className="text-slate-400 text-xs mt-2">
                            Last updated: {lastUpdated.toLocaleTimeString('en-IN')} on {lastUpdated.toLocaleDateString('en-IN')}
                        </p>
                    )}
                </div>
                <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                    <div className="flex w-full sm:w-auto gap-2">
                        <button
                            onClick={() => setReportType('equity')}
                            className={`flex-1 sm:flex-none px-4 py-2 rounded-xl font-bold text-xs uppercase transition-all ${reportType === 'equity'
                                ? 'bg-indigo-600 text-white'
                                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                                }`}
                        >
                            By Broker
                        </button>
                        <button
                            onClick={() => setReportType('mutual-funds')}
                            className={`flex-1 sm:flex-none px-4 py-2 rounded-xl font-bold text-xs uppercase transition-all ${reportType === 'mutual-funds'
                                ? 'bg-indigo-600 text-white'
                                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                                }`}
                        >
                            By AMC
                        </button>
                    </div>
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
                </div>
            </div>

            {/* Report Content */}
            <div className="space-y-4">
                {data.length === 0 ? (
                    <div className="p-10 text-center text-slate-400 bg-white rounded-xl">
                        No {reportType === 'equity' ? 'equity' : 'mutual fund'} holdings found
                    </div>
                ) : (
                    data.map((holder) => (
                        <div key={holder.holder} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                            {/* Holder Header */}
                            <button
                                onClick={() => setExpandedHolder(expandedHolder === holder.holder ? null : holder.holder)}
                                className="w-full flex justify-between items-center p-6 hover:bg-slate-50 transition-colors pr-8"
                            >
                                <div className="flex items-center gap-4 min-w-0">
                                    {expandedHolder === holder.holder ? (
                                        <ChevronDown className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                                    ) : (
                                        <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                                    )}
                                    <div className="text-left">
                                        <h3 className="font-black text-sm sm:text-xl text-slate-900 uppercase">{holder.holder}</h3>
                                    </div>
                                </div>
                                <div className="text-right flex-shrink-0 ml-4">
                                    <p className="font-black text-base sm:text-2xl lg:text-3xl text-indigo-700 whitespace-nowrap">₹{holder.holder_total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                </div>
                            </button>

                            {/* Broker/AMC Details */}
                            {expandedHolder === holder.holder && (
                                <div className="bg-slate-50/50 border-t border-slate-100">
                                    {reportType === 'equity'
                                        ? (holder as EquityByBroker).brokers.map((broker, idx) => (
                                            <div key={idx} className="border-b border-slate-100 last:border-b-0">
                                                <button
                                                    onClick={() => setExpandedBrokerAMC(expandedBrokerAMC === `${holder.holder}-${broker.broker_name}` ? null : `${holder.holder}-${broker.broker_name}`)}
                                                    className="w-full flex items-center p-5 ml-8 hover:bg-slate-100/50 transition-colors gap-8"
                                                >
                                                    <div className="flex items-center gap-3 flex-shrink-0">
                                                        {expandedBrokerAMC === `${holder.holder}-${broker.broker_name}` ? (
                                                            <ChevronDown className="w-4 h-4 text-slate-500" />
                                                        ) : (
                                                            <ChevronRight className="w-4 h-4 text-slate-400" />
                                                        )}
                                                        <span className="font-bold text-xs sm:text-lg text-slate-700 min-w-[120px]">{broker.broker_name}</span>
                                                    </div>
                                                    <div className="flex items-center gap-8">
                                                        <p className="font-bold text-xs sm:text-lg text-slate-900 min-w-[160px]">₹{broker.total_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                                        <p className={`font-bold text-xs sm:text-lg min-w-[140px] ${broker.total_pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                            {broker.total_pnl >= 0 ? '+' : ''}₹{broker.total_pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                        </p>
                                                    </div>
                                                </button>

                                                {/* Holdings Table */}
                                                {expandedBrokerAMC === `${holder.holder}-${broker.broker_name}` && (
                                                    <div className="p-4 ml-12 bg-white">
                                                        <div className="overflow-x-auto">
                                                            <table className="w-full text-sm">
                                                                <thead>
                                                                    <tr className="border-b border-slate-200 bg-slate-100">
                                                                        <th className="text-left py-3 px-4 font-bold text-slate-700 text-xs uppercase">Symbol</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">Qty</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">Price</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">Value</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">P&L</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {broker.holdings.map((holding, hidx) => (
                                                                        <tr key={hidx} className="border-b border-slate-100 hover:bg-slate-50">
                                                                            <td className="py-4 px-4 font-bold text-slate-900">{holding.symbol}</td>
                                                                            <td className="text-right py-4 px-4 text-base text-slate-700">{holding.quantity}</td>
                                                                            <td className="text-right py-4 px-4 text-base text-slate-700">₹{holding.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                            <td className="text-right py-4 px-4 font-bold text-base text-slate-900">₹{holding.current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                            <td className={`text-right py-4 px-4 font-bold text-base ${holding.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                                                {holding.pnl >= 0 ? '+' : ''}₹{holding.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                                            </td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ))
                                        : (holder as MFByAMC).amcs.map((amc, idx) => (
                                            <div key={idx} className="border-b border-slate-100 last:border-b-0">
                                                <button
                                                    onClick={() => setExpandedBrokerAMC(expandedBrokerAMC === `${holder.holder}-${amc.amc_name}` ? null : `${holder.holder}-${amc.amc_name}`)}
                                                    className="w-full flex items-center p-5 ml-8 hover:bg-slate-100/50 transition-colors gap-8"
                                                >
                                                    <div className="flex items-center gap-3 flex-shrink-0">
                                                        {expandedBrokerAMC === `${holder.holder}-${amc.amc_name}` ? (
                                                            <ChevronDown className="w-4 h-4 text-slate-500" />
                                                        ) : (
                                                            <ChevronRight className="w-4 h-4 text-slate-400" />
                                                        )}
                                                        <span className="font-bold text-lg text-slate-700 min-w-[120px]">{amc.amc_name}</span>
                                                    </div>
                                                    <div className="flex items-center gap-8">
                                                        <p className="font-bold text-lg text-slate-900 min-w-[160px]">₹{amc.total_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                                                        <p className={`font-bold text-lg min-w-[140px] ${amc.total_pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                            {amc.total_pnl >= 0 ? '+' : ''}₹{amc.total_pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                        </p>
                                                    </div>
                                                </button>

                                                {/* Funds Table */}
                                                {expandedBrokerAMC === `${holder.holder}-${amc.amc_name}` && (
                                                    <div className="p-4 ml-12 bg-white">
                                                        <div className="overflow-x-auto">
                                                            <table className="w-full text-sm">
                                                                <thead>
                                                                    <tr className="border-b border-slate-200 bg-slate-100">
                                                                        <th className="text-left py-3 px-4 font-bold text-slate-700 text-xs uppercase">Scheme</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">Units</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">NAV</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">Value</th>
                                                                        <th className="text-right py-3 px-4 font-bold text-slate-700 text-xs uppercase">P&L</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {amc.funds.map((fund, fidx) => (
                                                                        <tr key={fidx} className="border-b border-slate-100 hover:bg-slate-50">
                                                                            <td className="py-4 px-4 font-bold text-slate-900">{fund.scheme_name}</td>
                                                                            <td className="text-right py-4 px-4 text-base text-slate-700">{fund.units.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                                                            <td className="text-right py-4 px-4 text-base text-slate-700">₹{fund.current_nav.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                            <td className="text-right py-4 px-4 font-bold text-base text-slate-900">₹{fund.current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                                                            <td className={`text-right py-4 px-4 font-bold text-base ${fund.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                                                {fund.pnl >= 0 ? '+' : ''}₹{fund.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                                            </td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
