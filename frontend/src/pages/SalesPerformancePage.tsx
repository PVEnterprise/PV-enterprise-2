/**
 * Sales Performance page — executive-only drill-down. Search a sales
 * employee and month to view their visit/leave/order metrics.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/services/api';
import { RepSummary } from '@/types';
import AutocompleteField, { AutocompleteOption } from '@/components/common/AutocompleteField';
import DataTable, { Column } from '@/components/common/DataTable';
import { Activity, MapPin, CalendarOff, Sun, ShoppingCart } from 'lucide-react';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function StatCard({ label, value, icon: Icon }: { label: string; value: number | string; icon: React.ElementType }) {
  return (
    <div className="card flex items-center gap-3">
      <div className="bg-primary-50 p-2 rounded-md">
        <Icon size={18} className="text-primary-600" />
      </div>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

const orderColumns: Column<any>[] = [
  { key: 'order_number', label: 'Order #', width: '20%' },
  { key: 'customer_name', label: 'Customer', width: '30%' },
  { key: 'workflow_stage', label: 'Stage', width: '20%' },
  { key: 'created_at', label: 'Created', width: '15%', render: (v) => new Date(v).toLocaleDateString('en-IN') },
  { key: 'po_amount', label: 'PO Amount', width: '15%', render: (v) => v ? `₹${Number(v).toLocaleString('en-IN')}` : '-' },
];

export default function SalesPerformancePage() {
  const now = new Date();
  const [salesRepId, setSalesRepId] = useState<string | number>('');
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());

  const fetchReps = async (search: string): Promise<AutocompleteOption[]> => {
    const reps = await api.getEmployees({ role: 'sales_rep', search });
    return reps.map((r: any) => ({ value: r.id, label: r.name || r.full_name, subtitle: r.city }));
  };

  const { data: summary, isLoading } = useQuery<RepSummary>({
    queryKey: ['rep-summary', salesRepId, month, year],
    queryFn: () => api.getRepSummary({ sales_rep_id: salesRepId as string, month, year }),
    enabled: !!salesRepId,
  });

  return (
    <div className="w-full">
      <div className="flex items-center gap-3 mb-4 bg-white p-4 rounded-lg shadow-sm">
        <Activity size={18} className="text-primary-600" />
        <h1 className="text-xl font-bold text-gray-900">Sales Performance</h1>
      </div>

      <div className="card mb-4 flex items-center gap-4">
        <div className="flex-1">
          <AutocompleteField
            label="Sales Employee"
            value={salesRepId}
            onChange={setSalesRepId}
            fetchOptions={fetchReps}
            placeholder="Search sales employee..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Month</label>
          <select className="input" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
          <input
            type="number"
            className="input w-24"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </div>
      </div>

      {!salesRepId && (
        <div className="card text-center text-gray-400 italic py-8">
          Search and select a sales employee above to view their monthly performance.
        </div>
      )}

      {salesRepId && isLoading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
        </div>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <StatCard label="Visits" value={summary.visit_count} icon={MapPin} />
            <StatCard label="Leave Days" value={summary.leave_days} icon={CalendarOff} />
            <StatCard label="Holidays" value={summary.holiday_days} icon={Sun} />
            <StatCard label="Orders Created" value={summary.orders_created} icon={ShoppingCart} />
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Orders in {MONTHS[month - 1]} {year}</h3>
            <DataTable
              data={summary.orders}
              columns={orderColumns}
              emptyMessage="No orders created this month"
              showAuditInfo={false}
            />
          </div>
        </>
      )}
    </div>
  );
}
