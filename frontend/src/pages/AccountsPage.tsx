import React, { useState, useEffect, useCallback } from 'react';
import {
  DollarSign,
  Users,
  CheckCircle,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  X,
  AlertCircle,
} from 'lucide-react';
import api from '../services/api';
import DataTable, { Column, Action } from '../components/common/DataTable';

// ── Types ────────────────────────────────────────────────────────────────────

interface CustomerPaymentSummary {
  customer_id: string;
  customer_name: string;
  hospital_name: string;
  total_dispatched_value: number;
  total_paid: number;
  balance_due: number;
  dispatch_count: number;
  payment_count: number;
}

interface PaymentRecord {
  id: string;
  customer_id: string;
  customer_name: string;
  hospital_name: string;
  order_id: string | null;
  order_number: string | null;
  amount: number;
  payment_date: string;
  notes: string | null;
  recorded_by: string;
  recorder_name: string;
  created_at: string;
}

interface PaymentSummaryStats {
  total_customers_with_balance: number;
  total_balance_due: number;
  total_paid: number;
  total_dispatched_value: number;
}

interface Customer {
  id: string;
  name: string;
  hospital_name: string;
}

interface Order {
  id: string;
  order_number: string;
  customer_id: string;
}

// ── Record Payment Modal ──────────────────────────────────────────────────────

interface RecordPaymentModalProps {
  customers: Customer[];
  onClose: () => void;
  onSuccess: () => void;
  preselectedCustomerId?: string;
}

const RecordPaymentModal: React.FC<RecordPaymentModalProps> = ({
  customers,
  onClose,
  onSuccess,
  preselectedCustomerId,
}) => {
  const [customerId, setCustomerId] = useState(preselectedCustomerId || '');
  const [amount, setAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0]);
  const [orderId, setOrderId] = useState('');
  const [notes, setNotes] = useState('');
  const [customerOrders, setCustomerOrders] = useState<Order[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (customerId) {
      api.getOrders({ customer_id: customerId }).then((data: any) => {
        const orders = Array.isArray(data) ? data : data.items || [];
        setCustomerOrders(orders);
      }).catch(() => setCustomerOrders([]));
    } else {
      setCustomerOrders([]);
      setOrderId('');
    }
  }, [customerId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerId || !amount || !paymentDate) return;

    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setError('Amount must be a positive number');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await api.recordPayment({
        customer_id: customerId,
        amount: amountNum,
        payment_date: paymentDate,
        order_id: orderId || undefined,
        notes: notes || undefined,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to record payment');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Record Payment</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* Customer — mandatory */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Customer <span className="text-red-500">*</span>
            </label>
            <select
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              required
              className="input"
            >
              <option value="">Select a customer…</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.hospital_name} ({c.name})
                </option>
              ))}
            </select>
          </div>

          {/* Amount — mandatory */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount (₹) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              placeholder="0.00"
              className="input"
            />
          </div>

          {/* Payment Date — mandatory */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Payment Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              required
              className="input"
            />
          </div>

          {/* Order — optional */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Order <span className="text-gray-400 text-xs font-normal">(optional)</span>
            </label>
            <select
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              className="input"
              disabled={!customerId}
            >
              <option value="">No specific order</option>
              {customerOrders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.order_number}
                </option>
              ))}
            </select>
            {!customerId && (
              <p className="text-xs text-gray-400 mt-1">Select a customer to choose an order</p>
            )}
          </div>

          {/* Notes — optional */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes <span className="text-gray-400 text-xs font-normal">(optional)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="e.g. Cheque #1234, NEFT ref…"
              className="input resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !customerId || !amount || !paymentDate}
              className="btn btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Recording…' : 'Record Payment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Main Page ─────────────────────────────────────────────────────────────────

const AccountsPage: React.FC = () => {
  const [pendingSummary, setPendingSummary] = useState<CustomerPaymentSummary[]>([]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [summaryStats, setSummaryStats] = useState<PaymentSummaryStats | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [preselectedCustomer, setPreselectedCustomer] = useState<string | undefined>();
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [pendingData, paymentsData, statsData, customersData] = await Promise.all([
        api.getPaymentPendingSummary(),
        api.getPayments(),
        api.getPaymentSummary(),
        api.getCustomers(),
      ]);
      setPendingSummary(pendingData);
      setPayments(paymentsData);
      setSummaryStats(statsData);
      const cList = Array.isArray(customersData) ? customersData : customersData.items || [];
      setCustomers(cList);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load accounts data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDeletePayment = async (id: string) => {
    if (!window.confirm('Delete this payment record?')) return;
    setDeletingId(id);
    try {
      await api.deletePayment(id);
      await fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete payment');
    } finally {
      setDeletingId(null);
    }
  };

  const openModalForCustomer = (customerId: string) => {
    setPreselectedCustomer(customerId);
    setShowModal(true);
  };

  // ── Pending Summary columns ───────────────────────────────────────────────

  const pendingColumns: Column<CustomerPaymentSummary>[] = [
    {
      key: 'customer_name',
      label: 'Customer',
      sortable: true,
      width: '25%',
      render: (_v, row) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{row.hospital_name}</div>
          <div className="text-xs text-gray-500">{row.customer_name}</div>
        </div>
      ),
    },
    {
      key: 'total_dispatched_value',
      label: 'Dispatched Value',
      sortable: true,
      width: '18%',
      render: (v) => (
        <div className="text-right text-sm font-medium text-gray-800">
          ₹{Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
      ),
    },
    {
      key: 'total_paid',
      label: 'Total Paid',
      sortable: true,
      width: '16%',
      render: (v) => (
        <div className="text-right text-sm font-medium text-green-700">
          ₹{Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
      ),
    },
    {
      key: 'balance_due',
      label: 'Balance Due',
      sortable: true,
      width: '16%',
      render: (v) => {
        const n = Number(v);
        const colorClass = n > 0 ? 'text-red-600' : 'text-green-600';
        return (
          <div className={`text-right text-sm font-semibold ${colorClass}`}>
            ₹{n.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
        );
      },
    },
    {
      key: 'dispatch_count',
      label: 'Dispatches',
      sortable: true,
      width: '10%',
      render: (v) => <div className="text-center text-sm">{v}</div>,
    },
    {
      key: 'payment_count',
      label: 'Payments',
      sortable: true,
      width: '10%',
      render: (v) => <div className="text-center text-sm">{v}</div>,
    },
    {
      key: 'balance_due',
      label: 'Status',
      width: '10%',
      render: (v) => {
        const n = Number(v);
        if (n === 0) {
          return (
            <div className="text-center">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <CheckCircle size={11} /> Cleared
              </span>
            </div>
          );
        }
        if (n < 0) {
          return (
            <div className="text-center">
              <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Overpaid
              </span>
            </div>
          );
        }
        return (
          <div className="text-center">
            <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
              Pending
            </span>
          </div>
        );
      },
    },
  ];

  const pendingActions: Action<CustomerPaymentSummary>[] = [
    {
      label: 'Record Payment',
      icon: <Plus size={14} />,
      onClick: (row) => openModalForCustomer(row.customer_id),
      variant: 'primary',
      show: (row) => Number(row.balance_due) > 0,
    },
  ];

  // ── Payments History columns ──────────────────────────────────────────────

  const paymentColumns: Column<PaymentRecord>[] = [
    {
      key: 'payment_date',
      label: 'Date',
      sortable: true,
      width: '10%',
      render: (v) => (
        <div className="text-sm text-gray-700">
          {new Date(v).toLocaleDateString('en-IN')}
        </div>
      ),
    },
    {
      key: 'customer_name',
      label: 'Customer',
      sortable: true,
      width: '22%',
      render: (_v, row) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{row.hospital_name}</div>
          <div className="text-xs text-gray-500">{row.customer_name}</div>
        </div>
      ),
    },
    {
      key: 'amount',
      label: 'Amount',
      sortable: true,
      width: '14%',
      render: (v) => (
        <div className="text-right text-sm font-semibold text-green-700">
          ₹{Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
      ),
    },
    {
      key: 'order_number',
      label: 'Order',
      sortable: true,
      width: '12%',
      render: (v) =>
        v ? (
          <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
            {v}
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        ),
    },
    {
      key: 'notes',
      label: 'Notes',
      width: '22%',
      render: (v) => (
        <div className="text-xs text-gray-500 truncate max-w-xs">{v || '—'}</div>
      ),
    },
    {
      key: 'recorder_name',
      label: 'Recorded By',
      sortable: true,
      width: '14%',
      render: (v) => <div className="text-xs text-gray-600">{v}</div>,
    },
  ];

  const paymentActions: Action<PaymentRecord>[] = [
    {
      label: 'Delete',
      icon: <Trash2 size={14} />,
      onClick: (row) => handleDeletePayment(row.id),
      variant: 'danger',
    },
  ];

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading accounts data…</p>
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

  return (
    <div className="space-y-6">
      {/* ── Header + Stats ────────────────────────────────────────────────── */}
      <div className="card p-4">
        <button
          onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
          className="w-full flex items-center justify-between hover:bg-gray-50 transition-colors rounded p-2 -m-2"
        >
          <div className="text-left">
            <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
            <p className="text-gray-600 mt-1">Track customer payments and dispatched balances</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={(e) => { e.stopPropagation(); setPreselectedCustomer(undefined); setShowModal(true); }}
              className="btn btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={16} />
              Record Payment
            </button>
            {isSummaryExpanded ? (
              <ChevronUp size={24} className="text-gray-600" />
            ) : (
              <ChevronDown size={24} className="text-gray-600" />
            )}
          </div>
        </button>

        {isSummaryExpanded && summaryStats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <div className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Paid</p>
                  <p className="text-xl font-bold text-green-700 mt-1">
                    ₹{Number(summaryStats.total_paid).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>

            <div className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Balance Due</p>
                  <p className="text-xl font-bold text-red-600 mt-1">
                    ₹{Number(summaryStats.total_balance_due).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="p-3 bg-red-100 rounded-lg">
                  <DollarSign className="w-6 h-6 text-red-600" />
                </div>
              </div>
            </div>

            <div className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Customers w/ Balance</p>
                  <p className="text-xl font-bold text-gray-900 mt-1">
                    {summaryStats.total_customers_with_balance}
                  </p>
                </div>
                <div className="p-3 bg-orange-100 rounded-lg">
                  <Users className="w-6 h-6 text-orange-600" />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Pending Payments Table ────────────────────────────────────────── */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">Customers — Pending &amp; Overpaid</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            All-time balance per customer. Cleared customers are hidden.
          </p>
        </div>
        <div
          className="overflow-auto"
          style={{ maxHeight: isSummaryExpanded ? 'calc(100vh - 460px)' : 'calc(100vh - 320px)' }}
        >
          <DataTable
            data={pendingSummary}
            columns={pendingColumns}
            actions={pendingActions}
            isLoading={false}
            emptyMessage="No dispatched items found. Payments become visible once dispatches are created."
            showAuditInfo={false}
            enableSorting={true}
            tableId="accounts-pending"
          />
        </div>
      </div>

      {/* ── Payment History Table ─────────────────────────────────────────── */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Payment History</h2>
            <p className="text-sm text-gray-500 mt-0.5">All recorded payments</p>
          </div>
          <button
            onClick={() => { setPreselectedCustomer(undefined); setShowModal(true); }}
            className="btn btn-primary flex items-center gap-2 text-sm"
          >
            <Plus size={16} />
            Record Payment
          </button>
        </div>
        <div className="overflow-auto" style={{ maxHeight: '400px' }}>
          <DataTable
            data={payments}
            columns={paymentColumns}
            actions={paymentActions}
            isLoading={deletingId !== null}
            emptyMessage="No payments recorded yet"
            showAuditInfo={false}
            enableSorting={true}
            tableId="accounts-payments"
          />
        </div>
      </div>

      {/* ── Record Payment Modal ──────────────────────────────────────────── */}
      {showModal && (
        <RecordPaymentModal
          customers={customers}
          preselectedCustomerId={preselectedCustomer}
          onClose={() => { setShowModal(false); setPreselectedCustomer(undefined); }}
          onSuccess={() => {
            setShowModal(false);
            setPreselectedCustomer(undefined);
            fetchData();
          }}
        />
      )}
    </div>
  );
};

export default AccountsPage;
