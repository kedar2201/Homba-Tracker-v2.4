import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, TrendingDown, PieChart as PieChartIcon, Zap } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../lib/api';

interface EquityData {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  invested_amount: number;
  current_value: number;
  gain_loss: number;
  gain_loss_percent: number;
  buy_units?: number;
  sell_units?: number;
}

interface MFData {
  scheme_name: string;
  units: number;
  cost_basis: number;
  current_nav: number;
  invested_amount: number;
  current_value: number;
  gain_loss: number;
  gain_loss_percent: number;
  p_buy_units?: number;
  p_sell_units?: number;
}


export default function Analytics() {
  const navigate = useNavigate();
  const [equities, setEquities] = useState<EquityData[]>([]);
  const [mfs, setMFs] = useState<MFData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'equities' | 'mfs'>('summary');
  const [viewMode, setViewMode] = useState<'invested' | 'current'>('current');
  const [dmaData, setDmaData] = useState<{ summary: any, total_value: number }>({ summary: {}, total_value: 0 });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    const fetchData = async () => {
      try {
        // Fetch equities
        const eqResponse = await api.get('/equity/');
        const equityData: EquityData[] = (eqResponse.data || []).map((eq: any) => {
          const invested = eq.invested_value ?? (eq.quantity * (eq.buy_price ?? eq.avg_cost ?? 0));
          const current = eq.current_value ?? (eq.quantity * (eq.current_price ?? 0));
          const gain = current - invested;
          return {
            symbol: eq.symbol,
            quantity: eq.quantity,
            avg_cost: eq.buy_price ?? eq.avg_cost ?? 0,
            current_price: eq.current_price ?? 0,
            invested_amount: invested,
            current_value: current,
            gain_loss: gain,
            gain_loss_percent: invested > 0 ? (gain / invested) * 100 : 0,
            buy_units: eq.buy_units,
            sell_units: eq.sell_units
          };
        });

        // Fetch mutual funds
        const mfResponse = await api.get('/mutual-funds/');

        const mfData: MFData[] = (mfResponse.data || []).map((mf: any) => {
          const invested = mf.invested_amount ?? (mf.units * (mf.cost_basis ?? 0));
          const current = mf.current_value ?? (mf.units * (mf.current_nav ?? 0));
          const gain = current - invested;
          return {
            scheme_name: mf.scheme_name,
            units: mf.units,
            cost_basis: mf.cost_basis ?? 0,
            current_nav: mf.current_nav ?? 0,
            invested_amount: invested,
            current_value: current,
            gain_loss: gain,
            gain_loss_percent: invested > 0 ? (gain / invested) * 100 : 0,
            p_buy_units: mf.p_buy_units,
            p_sell_units: mf.p_sell_units
          };
        });

        // Fetch DMA signals for analytics summary
        const dmaResponse = await api.get('/reports/dma-signals');
        setDmaData({
          summary: dmaResponse.data.summary || {},
          total_value: dmaResponse.data.total_value || 0
        });

        setEquities(equityData);
        setMFs(mfData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [navigate]);

  const metrics = useMemo(() => {
    const allAssets = [...equities, ...mfs];
    const totalInvested = allAssets.reduce((sum, asset) => sum + asset.invested_amount, 0);
    const totalCurrent = allAssets.reduce((sum, asset) => sum + asset.current_value, 0);
    const totalGain = totalCurrent - totalInvested;
    const gainPercent = totalInvested > 0 ? (totalGain / totalInvested) * 100 : 0;

    const eqInvested = equities.reduce((sum, e) => sum + e.invested_amount, 0);
    const eqCurrent = equities.reduce((sum, e) => sum + e.current_value, 0);
    const mfInvested = mfs.reduce((sum, m) => sum + m.invested_amount, 0);
    const mfCurrent = mfs.reduce((sum, m) => sum + m.current_value, 0);

    // Calculate Portfolio Units
    let totalUnits = 0;
    equities.forEach(e => totalUnits += (e.buy_units || 0) - (e.sell_units || 0));
    mfs.forEach(m => totalUnits += (m.p_buy_units || 0) - (m.p_sell_units || 0));

    const portfolioNAV = totalUnits > 0 ? (eqCurrent + mfCurrent) / totalUnits : 100;

    return {
      totalInvested,
      totalCurrent,
      totalGain,
      gainPercent,
      eqInvested,
      eqCurrent,
      mfInvested,
      mfCurrent,
      totalUnits,
      portfolioNAV
    };
  }, [equities, mfs]);

  const aggregatedAssets = useMemo(() => {
    const eqGroups: Record<string, { invested: number, current: number, name: string, type: 'equity' }> = {};
    const mfGroups: Record<string, { invested: number, current: number, name: string, type: 'mf' }> = {};

    equities.forEach(eq => {
      if (!eqGroups[eq.symbol]) {
        eqGroups[eq.symbol] = { invested: 0, current: 0, name: eq.symbol, type: 'equity' };
      }
      eqGroups[eq.symbol].invested += eq.invested_amount;
      eqGroups[eq.symbol].current += eq.current_value;
    });

    mfs.forEach(mf => {
      if (!mfGroups[mf.scheme_name]) {
        mfGroups[mf.scheme_name] = { invested: 0, current: 0, name: mf.scheme_name, type: 'mf' };
      }
      mfGroups[mf.scheme_name].invested += mf.invested_amount;
      mfGroups[mf.scheme_name].current += mf.current_value;
    });

    const merged = [
      ...Object.values(eqGroups),
      ...Object.values(mfGroups)
    ].map(group => {
      const gain = group.current - group.invested;
      return {
        ...group,
        gain_loss: gain,
        gain_loss_percent: group.invested > 0 ? (gain / group.invested) * 100 : 0
      };
    });

    return merged;
  }, [equities, mfs]);

  const topGainers = useMemo(() => {
    return [...aggregatedAssets]
      .sort((a, b) => b.gain_loss_percent - a.gain_loss_percent)
      .slice(0, 10);
  }, [aggregatedAssets]);

  const topLosers = useMemo(() => {
    return [...aggregatedAssets]
      .sort((a, b) => a.gain_loss_percent - b.gain_loss_percent)
      .slice(0, 10);
  }, [aggregatedAssets]);

  const allocationData = useMemo(() => [
    {
      name: 'Equities',
      value: viewMode === 'invested' ? metrics.eqInvested : metrics.eqCurrent,
      color: '#4F46E5'
    },
    {
      name: 'Mutual Funds',
      value: viewMode === 'invested' ? metrics.mfInvested : metrics.mfCurrent,
      color: '#06B6D4'
    },
  ], [metrics, viewMode]);

  const topGainersData = useMemo(() =>
    topGainers.map(item => ({
      name: item.name,
      gain: item.gain_loss_percent,
    })), [topGainers]);

  const topLosersData = useMemo(() =>
    topLosers.map(item => ({
      name: item.name,
      loss: item.gain_loss_percent,
    })), [topLosers]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-slate-500">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-4xl font-black text-slate-900 uppercase tracking-tighter">Analytics</h1>
          <p className="text-slate-500">Portfolio performance & insights</p>
        </div>

        {/* View Toggle */}
        <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
          <button
            onClick={() => setViewMode('invested')}
            className={`px-4 py-2 text-xs font-black uppercase tracking-wider rounded-lg transition-all ${viewMode === 'invested'
              ? 'bg-white text-indigo-600 shadow-sm border border-slate-200'
              : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            Invested Value
          </button>
          <button
            onClick={() => setViewMode('current')}
            className={`px-4 py-2 text-xs font-black uppercase tracking-wider rounded-lg transition-all ${viewMode === 'current'
              ? 'bg-white text-indigo-600 shadow-sm border border-slate-200'
              : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            Market Value
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('summary')}
          className={`px-4 py-3 font-bold transition-colors ${activeTab === 'summary'
            ? 'text-indigo-600 border-b-2 border-indigo-600'
            : 'text-slate-600 hover:text-slate-900'
            }`}
        >
          Summary
        </button>
        <button
          onClick={() => setActiveTab('equities')}
          className={`px-4 py-3 font-bold transition-colors ${activeTab === 'equities'
            ? 'text-indigo-600 border-b-2 border-indigo-600'
            : 'text-slate-600 hover:text-slate-900'
            }`}
        >
          Equities
        </button>
        <button
          onClick={() => setActiveTab('mfs')}
          className={`px-4 py-3 font-bold transition-colors ${activeTab === 'mfs'
            ? 'text-indigo-600 border-b-2 border-indigo-600'
            : 'text-slate-600 hover:text-slate-900'
            }`}
        >
          Mutual Funds
        </button>
      </div>

      {/* Summary Tab */}
      {activeTab === 'summary' && (
        <div className="space-y-6">
          {/* Signal Trends (DMA) */}
          <div className="space-y-4">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <Zap className="w-3 h-3 text-amber-500" />
              Technical Signal Distribution (DMA)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {Object.entries(dmaData.summary || {}).map(([trend, data]: [string, any]) => (
                <div key={trend} className={`bg-white p-6 rounded-3xl border border-slate-200 shadow-sm transition-all hover:shadow-md ${data.count > 0 ? 'opacity-100' : 'opacity-50'}`}>
                  <div className="flex justify-between items-start mb-4">
                    <span className={`px-2 py-1 rounded-full text-[9px] font-black tracking-wider 
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
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <p className="text-sm text-slate-600 mb-2">Total Invested</p>
              <p className="text-3xl font-black text-slate-900">₹{metrics.totalInvested.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <p className="text-sm text-slate-600 mb-2">Current Value</p>
              <p className="text-3xl font-black text-slate-900">₹{metrics.totalCurrent.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            </div>
            <div className={`border rounded-lg p-6 ${metrics.totalGain >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
              <p className="text-sm text-slate-600 mb-2">Total Gain/Loss</p>
              <p className={`text-3xl font-black ${metrics.totalGain >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {metrics.totalGain >= 0 ? '+' : ''}₹{metrics.totalGain.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className={`border rounded-lg p-6 ${metrics.gainPercent >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
              <p className="text-sm text-slate-600 mb-2">Return %</p>
              <p className={`text-3xl font-black ${metrics.gainPercent >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {metrics.gainPercent >= 0 ? '+' : ''}{metrics.gainPercent.toFixed(2)}%
              </p>
            </div>

            {/* Portfolio NAV & Units Card */}
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6 col-span-1 md:col-span-2 lg:col-span-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-indigo-500 uppercase tracking-widest mb-1">Portfolio NAV</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-black text-indigo-700">₹{metrics.portfolioNAV.toLocaleString('en-IN', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</span>
                  <span className="text-sm font-bold text-indigo-400">Current Unit Price</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-indigo-500 uppercase tracking-widest mb-1">Total Units</p>
                <p className="text-2xl font-black text-indigo-700">{metrics.totalUnits.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Allocation Pie Chart */}
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <PieChartIcon className="w-5 h-5 text-indigo-600" />
                Portfolio Allocation
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ₹${((value as number) / 100000).toFixed(0)}L`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {allocationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `₹${((value as number) / 100000).toFixed(1)}L`} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Top Gainers Bar Chart */}
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-600" />
                Top 10 Gainers
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topGainersData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis
                    dataKey="name"
                    interval={0}
                    tick={{ fontSize: 10, fontWeight: 700, fill: '#64748b' }}
                    tickFormatter={(value) => value.length > 10 ? `${value.substring(0, 10)}...` : value}
                  />
                  <YAxis tick={{ fontSize: 10, fontWeight: 700, fill: '#64748b' }} />
                  <Tooltip
                    cursor={{ fill: '#f8fafc' }}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [`${(value as number).toFixed(2)}%`, 'Gain']}
                  />
                  <Bar dataKey="gain" fill="#10B981" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Losers */}
          <div className="bg-white border border-slate-200 rounded-lg p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-red-600" />
              Top 10 Losers
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topLosersData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="name"
                  interval={0}
                  tick={{ fontSize: 10, fontWeight: 700, fill: '#64748b' }}
                  tickFormatter={(value) => value.length > 10 ? `${value.substring(0, 10)}...` : value}
                />
                <YAxis tick={{ fontSize: 10, fontWeight: 700, fill: '#64748b' }} />
                <Tooltip
                  cursor={{ fill: '#f8fafc' }}
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [`${(value as number).toFixed(2)}%`, 'Loss']}
                />
                <Bar dataKey="loss" fill="#EF4444" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Equities Tab */}
      {activeTab === 'equities' && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="text-left py-3 px-4 font-bold text-slate-700 uppercase text-xs">Symbol</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Qty</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Avg Cost</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Current Price</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Invested</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Current Value</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Gain/Loss</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Return %</th>
                </tr>
              </thead>
              <tbody>
                {equities.map((eq, idx) => (
                  <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-4 px-4 font-bold text-slate-900">{eq.symbol}</td>
                    <td className="text-right py-4 px-4 text-slate-700">{eq.quantity}</td>
                    <td className="text-right py-4 px-4 text-slate-700">₹{eq.avg_cost.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 text-slate-700">₹{eq.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 font-bold text-slate-900">₹{eq.invested_amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 font-bold text-slate-900">₹{eq.current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className={`text-right py-4 px-4 font-bold ${eq.gain_loss >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {eq.gain_loss >= 0 ? '+' : ''}₹{eq.gain_loss.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`text-right py-4 px-4 font-bold ${eq.gain_loss_percent >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {eq.gain_loss_percent >= 0 ? '+' : ''}{eq.gain_loss_percent.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Mutual Funds Tab */}
      {activeTab === 'mfs' && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="text-left py-3 px-4 font-bold text-slate-700 uppercase text-xs">Scheme</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Units</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Cost/Unit</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Current NAV</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Invested</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Current Value</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Gain/Loss</th>
                  <th className="text-right py-3 px-4 font-bold text-slate-700 uppercase text-xs">Return %</th>
                </tr>
              </thead>
              <tbody>
                {mfs.map((mf, idx) => (
                  <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-4 px-4 font-bold text-slate-900">{mf.scheme_name}</td>
                    <td className="text-right py-4 px-4 text-slate-700">{mf.units.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 text-slate-700">₹{mf.cost_basis.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 text-slate-700">₹{mf.current_nav.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 font-bold text-slate-900">₹{mf.invested_amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="text-right py-4 px-4 font-bold text-slate-900">₹{mf.current_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className={`text-right py-4 px-4 font-bold ${mf.gain_loss >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {mf.gain_loss >= 0 ? '+' : ''}₹{mf.gain_loss.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`text-right py-4 px-4 font-bold ${mf.gain_loss_percent >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {mf.gain_loss_percent >= 0 ? '+' : ''}{mf.gain_loss_percent.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
