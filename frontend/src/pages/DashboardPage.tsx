/**
 * Dashboard page with statistics and charts.
 */
import { useQuery } from '@tanstack/react-query';
import api from '@/services/api';
import { DashboardStats } from '@/types';
import { TrendingUp, ShoppingCart, DollarSign, Package, AlertTriangle } from 'lucide-react';

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
  });

  if (isLoading) {
    return <div>Loading dashboard...</div>;
  }

  const statCards = [
    {
      name: 'Total Orders',
      value: stats?.total_orders || 0,
      icon: ShoppingCart,
      color: 'bg-blue-500',
    },
    {
      name: 'Pending Orders',
      value: stats?.pending_orders || 0,
      icon: AlertTriangle,
      color: 'bg-yellow-500',
    },
    {
      name: 'Total Revenue',
      value: `₹${(stats?.total_revenue || 0).toLocaleString()}`,
      icon: DollarSign,
      color: 'bg-green-500',
    },
    {
      name: 'Low Stock Items',
      value: stats?.low_stock_items || 0,
      icon: Package,
      color: 'bg-red-500',
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="card">
              <div className="flex items-center">
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Additional Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Pending Invoices</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Count:</span>
              <span className="font-semibold">{stats?.pending_invoices || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Outstanding Amount:</span>
              <span className="font-semibold">₹{(stats?.outstanding_amount || 0).toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Quick Stats</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Completed Orders:</span>
              <span className="font-semibold">{stats?.completed_orders || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Active Customers:</span>
              <span className="font-semibold">{stats?.active_customers || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
