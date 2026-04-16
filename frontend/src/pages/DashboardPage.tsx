/**
 * CEO Dashboard — comprehensive metrics across all modules.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import api from '@/services/api';
import { DashboardStats } from '@/types';
import { ShoppingCart, DollarSign, FileText, BarChart2 } from 'lucide-react';

const fmt = (n: number) =>
  n >= 1_00_00_000 ? `₹${(n / 1_00_00_000).toFixed(1)}Cr`
  : n >= 1_00_000 ? `₹${(n / 1_00_000).toFixed(1)}L`
  : n >= 1_000 ? `₹${(n / 1_000).toFixed(1)}K`
  : `₹${n.toFixed(0)}`;

interface FyPoint { month: string; invoice_value: number; pending_order_value: number; }

function KpiCard({
  title, value, sub, icon: Icon, iconBg,
}: {
  title: string; value: string; sub?: string;
  icon: React.ElementType; iconBg: string;
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

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
  });

  const { data: fyTrend = [] } = useQuery<FyPoint[]>({
    queryKey: ['fy-trend'],
    queryFn: () => api.getFyTrend(),
  });

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
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">CEO Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {now.toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* ── KPI row: 3 cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          title="Invoiced This Month"
          value={fmt(Number(s.invoiced_this_month))}
          sub={`All-time invoiced: ${fmt(Number(s.total_invoiced))}`}
          icon={FileText}
          iconBg="bg-green-500"
        />
        <KpiCard
          title="Quotation Value (Pending)"
          value={fmt(Number(s.pending_quotation_value))}
          sub={`${s.pending_quotations} order${s.pending_quotations !== 1 ? 's' : ''} awaiting PO`}
          icon={DollarSign}
          iconBg="bg-orange-500"
        />
        <KpiCard
          title="Pending Order Value"
          value={fmt(Number(s.total_pending_order_value))}
          sub={`${s.pending_orders} pending orders · ${s.pending_approval_orders} awaiting approval`}
          icon={ShoppingCart}
          iconBg="bg-blue-500"
        />
      </div>

      {/* ── FY bar chart: full width ── */}
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
