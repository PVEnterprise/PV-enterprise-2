/**
 * CEO Dashboard — 3-panel sliding view: Revenue | Inventory | Customers
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import api from '@/services/api';
import { DashboardStats } from '@/types';
import {
  ShoppingCart, DollarSign, FileText, BarChart2,
  Package, Users, TrendingUp, AlertCircle, Send, UserPlus, Clock
} from 'lucide-react';

const fmt = (n: number) =>
  n >= 1_00_00_000 ? `₹${(n / 1_00_00_000).toFixed(1)}Cr`
  : n >= 1_00_000 ? `₹${(n / 1_00_000).toFixed(1)}L`
  : n >= 1_000 ? `₹${(n / 1_000).toFixed(1)}K`
  : `₹${n.toFixed(0)}`;

const AUTO_SLIDE_MS = 15_000;

interface FyPoint { month: string; invoice_value: number; pending_order_value: number; }

interface InventoryInsights {
  top_sold_items: Array<{ sku: string; description: string; unit_price: number; total_sold: number; }>;
  top_out_of_stock_pending: Array<{ sku: string; description: string; unit_price: number; stock_quantity: number; ordered_qty: number; total_value: number; }>;
  top_quotation_pending: Array<{ sku: string; description: string; unit_price: number; stock_quantity: number; order_count: number; total_qty: number; total_value: number; }>;
}

interface CustomerInsights {
  new_customers: Array<{ id: string; name: string; hospital_name: string; city: string; created_at: string; }>;
  top_revenue_customers: Array<{ id: string; name: string; hospital_name: string; revenue: number; }>;
  top_pending_customers: Array<{ id: string; name: string; hospital_name: string; pending_value: number; }>;
}

function KpiCard({ title, value, sub, icon: Icon, iconBg }: {
  title: string; value: string; sub?: string; icon: React.ElementType; iconBg: string;
}) {
  return (
    <div className="card flex flex-col gap-3">
      <div className={`${iconBg} p-2.5 rounded-lg w-fit`}>
        <Icon className="h-5 w-5 text-white" />
      </div>
      <div>
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{title}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

const RANK_CLS: Record<string, string> = {
  blue:   'bg-blue-50   text-blue-700',
  green:  'bg-green-50  text-green-700',
  red:    'bg-red-50    text-red-700',
  amber:  'bg-amber-50  text-amber-700',
  purple: 'bg-purple-50 text-purple-700',
  orange: 'bg-orange-50 text-orange-700',
};

function Row({ rank, primary, secondary, right, accent = 'blue' }: {
  rank: number; primary: string; secondary?: string; right?: string; accent?: string;
}) {
  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-gray-50 last:border-0">
      <span className={`text-[10px] font-bold rounded px-1.5 py-0.5 shrink-0 leading-none ${RANK_CLS[accent]}`}>
        {rank}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-800 truncate" title={primary}>{primary}</p>
        {secondary && <p className="text-[10px] text-gray-400 truncate" title={secondary}>{secondary}</p>}
      </div>
      {right && <p className="text-xs font-semibold text-gray-700 shrink-0">{right}</p>}
    </div>
  );
}

function Panel({ title, subtitle, icon: Icon, iconBg, children }: {
  title: string; subtitle?: string; icon: React.ElementType; iconBg: string; children: React.ReactNode;
}) {
  return (
    <div className="card flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 mb-1 pb-2.5 border-b border-gray-100">
        <div className={`${iconBg} p-1.5 rounded-md shrink-0`}>
          <Icon className="h-3.5 w-3.5 text-white" />
        </div>
        <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wide leading-none">{title}</h3>
      </div>
      {subtitle && <p className="text-[10px] text-gray-400 mb-2.5 leading-snug">{subtitle}</p>}
      <div className="flex-1 overflow-y-auto min-h-0">{children}</div>
    </div>
  );
}

function RevenueView({ stats: s, fyTrend, fyLabel }: { stats: DashboardStats; fyTrend: FyPoint[]; fyLabel: string; }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          title="Invoiced This Month"
          value={fmt(Number(s.invoiced_this_month))}
          sub={`All-time invoiced: ${fmt(Number(s.total_invoiced))}`}
          icon={FileText} iconBg="bg-green-500"
        />
        <KpiCard
          title="Quotation Value (Pending)"
          value={fmt(Number(s.pending_quotation_value))}
          sub={`${s.pending_quotations} decoded order${s.pending_quotations !== 1 ? 's' : ''} pre-PO`}
          icon={DollarSign} iconBg="bg-orange-500"
        />
        <KpiCard
          title="Pending Order Value"
          value={fmt(Number(s.total_pending_order_value))}
          sub={`${s.pending_orders} pending orders · ${s.pending_approval_orders} awaiting approval`}
          icon={ShoppingCart} iconBg="bg-blue-500"
        />
      </div>
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <BarChart2 size={18} className="text-blue-600" />
          <h3 className="font-semibold text-gray-900">{fyLabel} — Monthly Overview</h3>
          <span className="ml-auto text-sm font-semibold text-amber-600">
            {fmt(fyTrend.reduce((sum, p) => sum + p.pending_order_value, 0))} pending
          </span>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={fyTrend} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={v => fmt(v)} width={62} />
            <Tooltip
              formatter={(val: number, name: string) => [
                fmt(val),
                name === 'invoice_value' ? 'Invoice Value' : 'Pending Order Value',
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: 11 }}
              formatter={v => v === 'invoice_value' ? 'Invoice Value' : 'Pending Order Value'}
            />
            <Bar dataKey="invoice_value" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            <Bar dataKey="pending_order_value" fill="#f59e0b" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function InventoryView({ data }: { data: InventoryInsights; }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
      <Panel title="Top 10 Sold — This FY" icon={TrendingUp} iconBg="bg-green-500">
        {data.top_sold_items.length === 0
          ? <p className="text-xs text-gray-400 italic py-2">No dispatch data this FY</p>
          : data.top_sold_items.map((item, i) => (
            <Row
              key={`sold-${i}`} rank={i + 1}
              primary={item.description || item.sku}
              secondary={item.sku}
              right={`${item.total_sold} units`}
              accent="green"
            />
          ))
        }
      </Panel>
      <Panel
        title="Stock <5 with Active Orders"
        subtitle="Items with <5 units in stock that have open, non-cancelled orders — needs urgent replenishment"
        icon={AlertCircle}
        iconBg="bg-red-500"
      >
        {data.top_out_of_stock_pending.length === 0
          ? <p className="text-xs text-gray-400 italic py-2">All pending items sufficiently stocked</p>
          : data.top_out_of_stock_pending.map((item, i) => (
            <Row
              key={`oos-${i}`} rank={i + 1}
              primary={item.description || item.sku}
              secondary={`${item.sku} · in stock: ${item.stock_quantity} · ordered: ${item.ordered_qty}`}
              right={fmt(item.total_value)}
              accent="red"
            />
          ))
        }
      </Panel>
      <Panel
        title="Low Stock · Pre-PO Decoded"
        subtitle="Decoded items (<5 in stock) where quotation is sent or order is decoded but customer PO not yet received"
        icon={Send}
        iconBg="bg-amber-500"
      >
        {data.top_quotation_pending.length === 0
          ? <p className="text-xs text-gray-400 italic py-2">No low-stock pre-PO items</p>
          : data.top_quotation_pending.map((item, i) => (
            <Row
              key={`quot-${i}`} rank={i + 1}
              primary={item.description || item.sku}
              secondary={`${item.sku} · in stock: ${item.stock_quantity} · ${item.order_count} order${item.order_count !== 1 ? 's' : ''} · qty: ${item.total_qty}`}
              right={fmt(item.total_value)}
              accent="amber"
            />
          ))
        }
      </Panel>
    </div>
  );
}

function CustomerView({ data }: { data: CustomerInsights; }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
      <Panel title="Last 5 New Customers" icon={UserPlus} iconBg="bg-blue-500">
        {data.new_customers.length === 0
          ? <p className="text-xs text-gray-400 italic py-2">No customers yet</p>
          : data.new_customers.map((c, i) => (
            <Row
              key={c.id} rank={i + 1}
              primary={c.hospital_name}
              secondary={[c.name, c.city].filter(Boolean).join(' · ')}
              right={c.created_at
                ? new Date(c.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
                : ''}
              accent="blue"
            />
          ))
        }
      </Panel>
      <Panel title="Top 5 Revenue — This FY" icon={TrendingUp} iconBg="bg-green-500">
        {data.top_revenue_customers.length === 0
          ? <p className="text-xs text-gray-400 italic py-2">No revenue data this FY</p>
          : data.top_revenue_customers.map((c, i) => (
            <Row
              key={c.id} rank={i + 1}
              primary={c.hospital_name}
              secondary={c.name}
              right={fmt(c.revenue)}
              accent="green"
            />
          ))
        }
      </Panel>
      <Panel title="Top 5 Pending Order Value" icon={Clock} iconBg="bg-orange-500">
        {data.top_pending_customers.length === 0
          ? <p className="text-xs text-gray-400 italic py-2">No pending orders</p>
          : data.top_pending_customers.map((c, i) => (
            <Row
              key={c.id} rank={i + 1}
              primary={c.hospital_name}
              secondary={c.name}
              right={fmt(c.pending_value)}
              accent="orange"
            />
          ))
        }
      </Panel>
    </div>
  );
}

const VIEW_META = [
  { label: 'Revenue',   dotColor: 'bg-blue-600',   textColor: 'text-blue-700',   icon: BarChart2 },
  { label: 'Inventory', dotColor: 'bg-green-600',  textColor: 'text-green-700',  icon: Package   },
  { label: 'Customers', dotColor: 'bg-purple-600', textColor: 'text-purple-700', icon: Users     },
] as const;

export default function DashboardPage() {
  const [view, setView] = useState(0);
  const [timerKey, setTimerKey] = useState(0);

  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
  });
  const { data: fyTrend = [] } = useQuery<FyPoint[]>({
    queryKey: ['fy-trend'],
    queryFn: () => api.getFyTrend(),
  });
  const { data: inventoryInsights } = useQuery<InventoryInsights>({
    queryKey: ['dashboard-inventory-insights'],
    queryFn: () => api.getDashboardInventoryInsights(),
  });
  const { data: customerInsights } = useQuery<CustomerInsights>({
    queryKey: ['dashboard-customer-insights'],
    queryFn: () => api.getDashboardCustomerInsights(),
  });

  const goTo = useCallback((idx: number) => {
    setView(idx);
    setTimerKey(k => k + 1);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setView(prev => (prev + 1) % 3), AUTO_SLIDE_MS);
    return () => clearInterval(timer);
  }, [timerKey]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const s = stats!;
  const now = new Date();
  const fyStartYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  const fyLabel = `FY ${fyStartYear}-${String(fyStartYear + 1).slice(2)}`;

  return (
    <div className="flex flex-col gap-5 h-[calc(100vh-7rem)]">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">CEO Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {now.toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Sliding carousel — flex-1 so it fills space between header and dots */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <div
          className="flex h-full transition-transform duration-500 ease-in-out"
          style={{ transform: `translateX(-${view * 100}%)` }}
        >
          {/* View 0: Revenue */}
          <div className="w-full flex-shrink-0 h-full overflow-y-auto">
            <RevenueView stats={s} fyTrend={fyTrend} fyLabel={fyLabel} />
          </div>

          {/* View 1: Inventory */}
          <div className="w-full flex-shrink-0 h-full">
            {inventoryInsights
              ? <InventoryView data={inventoryInsights} />
              : (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600" />
                </div>
              )
            }
          </div>

          {/* View 2: Customers */}
          <div className="w-full flex-shrink-0 h-full">
            {customerInsights
              ? <CustomerView data={customerInsights} />
              : (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600" />
                </div>
              )
            }
          </div>
        </div>
      </div>

      {/* Dot navigation */}
      <div className="flex items-center justify-center gap-6 pt-1">
        {VIEW_META.map((m, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            className="flex flex-col items-center gap-1.5 group"
            aria-label={`Switch to ${m.label} view`}
          >
            <div className={`transition-all duration-300 rounded-full h-2.5 ${
              view === i ? `w-7 ${m.dotColor}` : 'w-2.5 bg-gray-300 group-hover:bg-gray-400'
            }`} />
            <span className={`text-[11px] font-medium transition-colors duration-200 ${
              view === i ? m.textColor : 'text-gray-400 group-hover:text-gray-500'
            }`}>{m.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
