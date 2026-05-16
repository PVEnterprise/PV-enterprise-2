import React, { useState, useEffect } from 'react';
import { Package, Users, FileText, DollarSign, ExternalLink, ChevronDown, ChevronUp, Printer, Download } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import DataTable, { Column } from '../components/common/DataTable';

interface OutstandingItemByCustomer {
  order_item_id: string;
  order_id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  hospital_name: string;
  item_id: string;
  item_name: string;
  sku: string;
  ordered: number;
  dispatched: number;
  outstanding: number;
  unit_price: number;
  outstanding_value: number;
  item_status: string;
  order_status: string;
  available_stock: number;
}

interface OutstandingSummary {
  total_outstanding_items: number;
  total_outstanding_value: number;
  total_customers: number;
  total_orders: number;
}

const OutstandingPage: React.FC = () => {
  const [byCustomer, setByCustomer] = useState<OutstandingItemByCustomer[]>([]);
  const [summary, setSummary] = useState<OutstandingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const handleExportExcel = async () => {
    const XLSX = await import('xlsx');

    // Build groups from current state
    const groups = byCustomer.reduce((acc, item) => {
      const key = item.customer_id;
      if (!acc[key]) acc[key] = { customer_name: item.customer_name, hospital_name: item.hospital_name, items: [] };
      acc[key].items.push(item);
      return acc;
    }, {} as Record<string, { customer_name: string; hospital_name: string; items: OutstandingItemByCustomer[] }>);

    const rows: (string | number)[][] = [];

    // Column headers
    rows.push(['Customer / Hospital', 'Item', 'Ordered', 'Dispatched', 'Pending', 'Order No', 'Stock', 'Status']);

    Object.values(groups).forEach(group => {
      const label = group.customer_name === group.hospital_name
        ? group.customer_name
        : `${group.customer_name} — ${group.hospital_name}`;
      // Customer header row
      rows.push([`${label} (${group.items.length} item${group.items.length !== 1 ? 's' : ''})`, '', '', '', '', '', '', '']);

      group.items.forEach(item => {
        // Show "SKU — Description" if they differ, otherwise just SKU
        const itemLabel = item.item_name && item.item_name !== item.sku
          ? `${item.sku} — ${item.item_name}`
          : item.sku;
        rows.push([
          '',
          itemLabel,
          item.ordered,
          item.dispatched,
          item.outstanding,
          item.order_number,
          item.available_stock,
          item.item_status,
        ]);
      });
    });

    const ws = XLSX.utils.aoa_to_sheet(rows);

    // Set column widths
    ws['!cols'] = [
      { wch: 42 }, { wch: 30 },
      { wch: 9 }, { wch: 11 }, { wch: 9 },
      { wch: 14 }, { wch: 8 }, { wch: 10 },
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Pending Items');
    XLSX.writeFile(wb, `pending_items_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  const handlePrint = () => window.print();

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryData, byCustomerData] = await Promise.all([
        api.getOutstandingSummary(),
        api.getOutstandingByCustomer(),
      ]);

      setSummary(summaryData);
      setByCustomer(byCustomerData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load outstanding items');
      console.error('Error fetching outstanding data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Define columns for DataTable
  const columns: Column<OutstandingItemByCustomer>[] = [
    {
      key: 'item_name',
      label: 'Item',
      sortable: true,
      width: '20%',
      render: (_value, row) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{row.item_name}</div>
          <div className="text-xs text-gray-500">{row.sku}</div>
        </div>
      ),
    },
    {
      key: 'customer_name',
      label: 'Customer',
      sortable: true,
      width: '18%',
      render: (_value, row) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{row.customer_name}</div>
          <div className="text-xs text-gray-500">{row.hospital_name}</div>
        </div>
      ),
    },
    {
      key: 'ordered',
      label: 'Ordered',
      sortable: true,
      width: '8%',
      render: (value) => <div className="text-right">{value}</div>,
    },
    {
      key: 'dispatched',
      label: 'Dispatched',
      sortable: true,
      width: '8%',
      render: (value) => <div className="text-right">{value}</div>,
    },
    {
      key: 'outstanding',
      label: 'Pending',
      sortable: true,
      width: '10%',
      render: (value) => (
        <div className="text-right">
          <span className="font-semibold text-orange-600">{value}</span>
        </div>
      ),
    },
    {
      key: 'order_number',
      label: 'Order',
      sortable: true,
      width: '12%',
      render: (_value, row) => (
        <Link
          to={`/orders/${row.order_id}`}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
        >
          {row.order_number}
          <ExternalLink className="w-3 h-3" />
        </Link>
      ),
    },
    {
      key: 'available_stock',
      label: 'Available Stock',
      sortable: true,
      width: '10%',
      render: (value) => (
        <div className="text-right">
          <span className={`font-medium ${value > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {value}
          </span>
        </div>
      ),
    },
    {
      key: 'item_status',
      label: 'Status',
      sortable: true,
      width: '10%',
      render: (value) => {
        const statusColors: Record<string, string> = {
          'pending': 'bg-yellow-100 text-yellow-800',
          'partial': 'bg-orange-100 text-orange-800',
          'completed': 'bg-green-100 text-green-800',
          'cancelled': 'bg-red-100 text-red-800',
        };
        const colorClass = statusColors[value?.toLowerCase()] || 'bg-gray-100 text-gray-800';
        return (
          <div className="text-center">
            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colorClass}`}>
              {value || 'N/A'}
            </span>
          </div>
        );
      },
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading outstanding items...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  // Group data by customer for the print-only table
  const customerGroups = byCustomer.reduce((acc, item) => {
    const key = item.customer_id;
    if (!acc[key]) {
      acc[key] = { customer_name: item.customer_name, hospital_name: item.hospital_name, items: [] };
    }
    acc[key].items.push(item);
    return acc;
  }, {} as Record<string, { customer_name: string; hospital_name: string; items: OutstandingItemByCustomer[] }>);

  return (
    <div className="space-y-6">
      {/* Header with Collapse Toggle */}
      <div className="card p-4 screen-only">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
            className="flex-1 flex items-center justify-between hover:bg-gray-50 transition-colors rounded p-2 -m-2"
          >
            <div className="text-left">
              <h1 className="text-2xl font-bold text-gray-900">Pending Items</h1>
              <p className="text-gray-600 mt-1">Track pending deliveries across all orders</p>
            </div>
            <div className="ml-4">
              {isSummaryExpanded ? (
                <ChevronUp size={24} className="text-gray-600" />
              ) : (
                <ChevronDown size={24} className="text-gray-600" />
              )}
            </div>
          </button>
          {/* Action buttons */}
          <div className="flex items-center gap-2 ml-4 no-print">
            <button
              onClick={handleExportExcel}
              className="btn btn-secondary flex items-center gap-2 text-sm"
            >
              <Download size={15} />
              Export Excel
            </button>
            <button
              onClick={handlePrint}
              className="btn btn-primary flex items-center gap-2 text-sm"
            >
              <Printer size={15} />
              Print
            </button>
          </div>
        </div>

        {/* Summary Cards - Collapseable */}
        {isSummaryExpanded && summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Items</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{summary.total_outstanding_items}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Package className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Value</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  ₹{summary.total_outstanding_value.toLocaleString()}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Customers</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{summary.total_customers}</p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <Users className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Orders</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{summary.total_orders}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-lg">
                <FileText className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </div>
        </div>
        )}
      </div>

      {/* Pending Items Table — screen only */}
      <div
        className="overflow-auto transition-all duration-300 screen-only"
        style={{
          maxHeight: isSummaryExpanded
            ? 'calc(100vh - 320px)'
            : 'calc(100vh - 210px)'
        }}
      >
        <DataTable
          data={byCustomer}
          columns={columns}
          isLoading={loading}
          emptyMessage="No outstanding items found"
          showAuditInfo={false}
          enableSorting={true}
          enableGrouping={true}
          maxGroupLevels={2}
          tableId="outstanding-items"
          defaultGroupBy={['customer_name', 'item_name']}
        />
      </div>

      {/* ── Print-only view ─────────────────────────────────────────────── */}
      <div className="print-only" style={{ display: 'none' }}>
        <div style={{ marginBottom: 12 }}>
          <h1 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Pending Items</h1>
          <p style={{ fontSize: 11, color: '#555', margin: '2px 0 0' }}>
            SreeDevi Life Sciences &mdash; Printed on {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
            {summary && (
              <> &nbsp;|&nbsp; {summary.total_outstanding_items} items &nbsp;|&nbsp; {summary.total_customers} customers &nbsp;|&nbsp; ₹{summary.total_outstanding_value.toLocaleString('en-IN')} value</>
            )}
          </p>
        </div>
        <table className="print-table">
          <thead>
            <tr>
              <th>Customer / Hospital</th>
              <th>SKU</th>
              <th>Item</th>
              <th style={{ textAlign: 'right' }}>Ordered</th>
              <th style={{ textAlign: 'right' }}>Dispatched</th>
              <th style={{ textAlign: 'right', color: '#c2410c' }}>Pending</th>
              <th>Order No</th>
              <th style={{ textAlign: 'right' }}>Stock</th>
              <th style={{ textAlign: 'center' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {Object.values(customerGroups).map((group) => (
              <React.Fragment key={group.customer_name}>
                <tr className="customer-row">
                  <td colSpan={9}>{group.customer_name} — {group.hospital_name} ({group.items.length} item{group.items.length !== 1 ? 's' : ''})</td>
                </tr>
                {group.items.map((item) => (
                  <tr key={item.order_item_id}>
                    <td style={{ paddingLeft: 20, color: '#6b7280', fontSize: 9 }}></td>
                    <td>{item.sku}</td>
                    <td>{item.item_name}</td>
                    <td style={{ textAlign: 'right' }}>{item.ordered}</td>
                    <td style={{ textAlign: 'right' }}>{item.dispatched}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600, color: '#c2410c' }}>{item.outstanding}</td>
                    <td>{item.order_number}</td>
                    <td style={{ textAlign: 'right', color: item.available_stock > 0 ? '#15803d' : '#dc2626' }}>{item.available_stock}</td>
                    <td style={{ textAlign: 'center' }} className={`status-${item.item_status}`}>{item.item_status}</td>
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OutstandingPage;
