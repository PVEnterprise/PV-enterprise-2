/**
 * Invoices Page - List generated invoices with a single filter panel and a preview pane.
 */
import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileText, Filter, X, Pencil } from 'lucide-react';
import api from '@/services/api';
import { InvoiceListItem } from '@/types';

const NOT_SET = '(Not set)';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<InvoiceListItem | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);

  const [searchParams, setSearchParams] = useSearchParams();
  const [filtersOpen, setFiltersOpen] = useState(false);

  const [invoiceNumberInput, setInvoiceNumberInput] = useState(searchParams.get('invoice_number') || '');
  const [customerInput, setCustomerInput] = useState(searchParams.get('customer') || '');
  const [amountMinInput, setAmountMinInput] = useState(searchParams.get('amount_min') || '');
  const [amountMaxInput, setAmountMaxInput] = useState(searchParams.get('amount_max') || '');

  const cityFilter = useMemo(
    () => (searchParams.get('city') ? searchParams.get('city')!.split(',').filter(Boolean) : []),
    [searchParams]
  );
  const paymentTermsFilter = useMemo(
    () => (searchParams.get('payment_terms') ? searchParams.get('payment_terms')!.split(',').filter(Boolean) : []),
    [searchParams]
  );

  const updateParam = (key: string, value: string | string[] | null) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (!value || (Array.isArray(value) && value.length === 0)) {
        next.delete(key);
      } else if (Array.isArray(value)) {
        next.set(key, value.join(','));
      } else {
        next.set(key, value);
      }
      return next;
    }, { replace: true });
  };

  // Debounce text/range filters into the URL so it doesn't spam history on every keystroke.
  // The filtered table itself (below) reacts to the input state immediately, not the debounce.
  useEffect(() => {
    const t = setTimeout(() => updateParam('invoice_number', invoiceNumberInput || null), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoiceNumberInput]);

  useEffect(() => {
    const t = setTimeout(() => updateParam('customer', customerInput || null), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerInput]);

  useEffect(() => {
    const t = setTimeout(() => updateParam('amount_min', amountMinInput || null), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [amountMinInput]);

  useEffect(() => {
    const t = setTimeout(() => updateParam('amount_max', amountMaxInput || null), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [amountMaxInput]);

  const toggleArrayFilter = (key: 'city' | 'payment_terms', current: string[], value: string) => {
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    updateParam(key, next);
  };

  const clearAllFilters = () => {
    setInvoiceNumberInput('');
    setCustomerInput('');
    setAmountMinInput('');
    setAmountMaxInput('');
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      ['invoice_number', 'customer', 'amount_min', 'amount_max', 'city', 'payment_terms'].forEach((k) => next.delete(k));
      return next;
    }, { replace: true });
  };

  const activeFilterCount =
    (invoiceNumberInput ? 1 : 0) +
    (customerInput ? 1 : 0) +
    (cityFilter.length > 0 ? 1 : 0) +
    (paymentTermsFilter.length > 0 ? 1 : 0) +
    ((amountMinInput || amountMaxInput) ? 1 : 0);

  const hasActiveFilters = activeFilterCount > 0;

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const data = await api.getInvoicedDispatches();
      setInvoices(data);
      if (data.length > 0) {
        setSelected(data[0]);
      }
    } catch (error) {
      console.error('Error fetching invoices:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!selected) {
      setPdfUrl(null);
      return;
    }

    let cancelled = false;
    const loadPreview = async () => {
      setPreviewLoading(true);
      setPreviewError(false);
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/v1/dispatches/${selected.dispatch_id}/invoice/pdf`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!response.ok) {
          throw new Error('Failed to load invoice preview');
        }

        const blob = await response.blob();
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        setPdfUrl(url);
      } catch (error) {
        console.error('Error loading invoice preview:', error);
        if (!cancelled) setPreviewError(true);
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    };

    loadPreview();

    return () => {
      cancelled = true;
    };
  }, [selected]);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  const cityOptions = useMemo(() => {
    return Array.from(new Set(invoices.map((i) => i.customer_city || NOT_SET))).sort();
  }, [invoices]);

  const paymentTermsOptions = useMemo(() => {
    return Array.from(new Set(invoices.map((i) => i.payment_terms || NOT_SET))).sort();
  }, [invoices]);

  const filteredInvoices = useMemo(() => {
    const min = amountMinInput ? parseFloat(amountMinInput) : null;
    const max = amountMaxInput ? parseFloat(amountMaxInput) : null;
    return invoices.filter((inv) => {
      if (invoiceNumberInput && !inv.invoice_number.toLowerCase().includes(invoiceNumberInput.toLowerCase())) return false;
      if (customerInput && !inv.customer_name.toLowerCase().includes(customerInput.toLowerCase())) return false;
      if (cityFilter.length > 0 && !cityFilter.includes(inv.customer_city || NOT_SET)) return false;
      if (paymentTermsFilter.length > 0 && !paymentTermsFilter.includes(inv.payment_terms || NOT_SET)) return false;
      if (min !== null && !isNaN(min) && inv.invoice_amount < min) return false;
      if (max !== null && !isNaN(max) && inv.invoice_amount > max) return false;
      return true;
    });
  }, [invoices, invoiceNumberInput, customerInput, cityFilter, paymentTermsFilter, amountMinInput, amountMaxInput]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const formatAmount = (n: number) => `₹${(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

  const amountChipLabel = () => {
    if (amountMinInput && amountMaxInput) return `Amount: ₹${amountMinInput} – ₹${amountMaxInput}`;
    if (amountMinInput) return `Amount: ≥ ₹${amountMinInput}`;
    return `Amount: ≤ ₹${amountMaxInput}`;
  };

  const chips: { key: string; label: string; onRemove: () => void }[] = [
    ...(invoiceNumberInput ? [{ key: 'invoice_number', label: `Invoice #: "${invoiceNumberInput}"`, onRemove: () => setInvoiceNumberInput('') }] : []),
    ...(customerInput ? [{ key: 'customer', label: `Customer: "${customerInput}"`, onRemove: () => setCustomerInput('') }] : []),
    ...(cityFilter.length > 0 ? [{ key: 'city', label: `City: ${cityFilter.join(', ')}`, onRemove: () => updateParam('city', null) }] : []),
    ...(paymentTermsFilter.length > 0 ? [{ key: 'payment_terms', label: `Payment Terms: ${paymentTermsFilter.join(', ')}`, onRemove: () => updateParam('payment_terms', null) }] : []),
    ...((amountMinInput || amountMaxInput) ? [{ key: 'amount', label: amountChipLabel(), onRemove: () => { setAmountMinInput(''); setAmountMaxInput(''); } }] : []),
  ];

  return (
    <div className="h-[calc(100vh-80px)] flex gap-4">
      {/* Left Section - Invoice Table */}
      <div className="w-[36%] bg-white rounded-lg shadow-sm flex flex-col">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Invoices</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {filteredInvoices.length} of {invoices.length} shown
              </p>
            </div>
            <button
              onClick={() => setFiltersOpen(true)}
              className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
                hasActiveFilters
                  ? 'bg-primary-50 border-primary-200 text-primary-700 hover:bg-primary-100'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Filter size={14} />
              Filter
              {hasActiveFilters && (
                <span className="flex items-center justify-center h-4 w-4 text-[10px] font-semibold rounded-full bg-primary-600 text-white">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>

          {/* Visual representation of active filters - editable and clearable */}
          {chips.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 mt-3">
              {chips.map((chip) => (
                <button
                  key={chip.key}
                  onClick={() => setFiltersOpen(true)}
                  className="group flex items-center gap-1 bg-primary-50 border border-primary-200 text-primary-700 rounded-full pl-2.5 pr-1 py-0.5 text-xs hover:bg-primary-100"
                  title="Click to edit"
                >
                  <Pencil size={10} className="opacity-60" />
                  {chip.label}
                  <span
                    role="button"
                    aria-label={`Remove filter: ${chip.label}`}
                    tabIndex={0}
                    onClick={(e) => { e.stopPropagation(); chip.onRemove(); }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.stopPropagation();
                        e.preventDefault();
                        chip.onRemove();
                      }
                    }}
                    className="p-0.5 rounded-full hover:bg-primary-200"
                  >
                    <X size={11} />
                  </span>
                </button>
              ))}
              <button
                onClick={clearAllFilters}
                className="text-xs text-gray-500 hover:text-gray-700 underline ml-1"
              >
                Clear all
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="text-center text-gray-500 py-8">Loading...</div>
          ) : invoices.length === 0 ? (
            <div className="text-center text-gray-500 py-8 px-4">
              <p className="text-sm">No invoices generated yet</p>
            </div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-2">Invoice #</th>
                  <th className="px-4 py-2">Customer</th>
                  <th className="px-4 py-2">Amount</th>
                  <th className="px-4 py-2">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredInvoices.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center text-gray-500 py-8 text-sm">
                      No invoices match the current filters
                    </td>
                  </tr>
                ) : (
                  filteredInvoices.map((inv) => {
                    const active = selected?.dispatch_id === inv.dispatch_id;
                    return (
                      <tr
                        key={inv.dispatch_id}
                        onClick={() => setSelected(inv)}
                        className={`cursor-pointer transition-colors ${
                          active ? 'bg-primary-50' : 'hover:bg-gray-50'
                        }`}
                      >
                        <td className="px-4 py-2.5 font-mono font-semibold text-gray-900 whitespace-nowrap">
                          {inv.invoice_number}
                        </td>
                        <td className="px-4 py-2.5 text-gray-700 max-w-[140px] truncate">
                          {inv.customer_name}
                          {inv.customer_city && (
                            <span className="block text-[11px] text-gray-400 font-normal">{inv.customer_city}</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-gray-700 whitespace-nowrap">{formatAmount(inv.invoice_amount)}</td>
                        <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">{formatDate(inv.dispatch_date)}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Right Section - Invoice Preview */}
      <div className="w-[64%] bg-white rounded-lg shadow-sm flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {selected ? `Invoice ${selected.invoice_number}` : 'Preview'}
          </h2>
        </div>

        <div className="flex-1 overflow-auto bg-gray-50 flex items-center justify-center p-4">
          {!selected ? (
            <div className="text-center text-gray-500">
              <FileText size={40} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm">Select an invoice to preview</p>
            </div>
          ) : previewLoading ? (
            <div className="text-center text-gray-500">Loading preview...</div>
          ) : previewError ? (
            <div className="text-center text-gray-500 bg-white p-8 rounded-lg shadow">
              <p className="text-sm">Failed to load invoice preview.</p>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={`${pdfUrl}#toolbar=0`}
              className="w-full h-full border-0 rounded shadow-lg"
              title={selected.invoice_number}
            />
          ) : null}
        </div>
      </div>

      {/* All-in-one Filter Modal */}
      {filtersOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[85vh] flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900">Filter Invoices</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {filteredInvoices.length} of {invoices.length} invoices match
                </p>
              </div>
              <button onClick={() => setFiltersOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={22} />
              </button>
            </div>

            <div className="px-6 py-4 space-y-5 overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Invoice Number</label>
                <input
                  type="text"
                  value={invoiceNumberInput}
                  onChange={(e) => setInvoiceNumberInput(e.target.value)}
                  placeholder="Contains…"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
                <input
                  type="text"
                  value={customerInput}
                  onChange={(e) => setCustomerInput(e.target.value)}
                  placeholder="Contains…"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount Range</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={amountMinInput}
                    onChange={(e) => setAmountMinInput(e.target.value)}
                    placeholder="Min"
                    className="input w-full"
                  />
                  <span className="text-gray-400 text-sm">to</span>
                  <input
                    type="number"
                    value={amountMaxInput}
                    onChange={(e) => setAmountMaxInput(e.target.value)}
                    placeholder="Max"
                    className="input w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                <div className="border border-gray-200 rounded-lg max-h-32 overflow-auto p-2 space-y-1">
                  {cityOptions.length === 0 ? (
                    <p className="text-xs text-gray-400 px-1">No values</p>
                  ) : (
                    cityOptions.map((c) => (
                      <label key={c} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer px-1 py-0.5 rounded hover:bg-gray-50">
                        <input
                          type="checkbox"
                          checked={cityFilter.includes(c)}
                          onChange={() => toggleArrayFilter('city', cityFilter, c)}
                        />
                        {c}
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Payment Terms</label>
                <div className="border border-gray-200 rounded-lg max-h-32 overflow-auto p-2 space-y-1">
                  {paymentTermsOptions.length === 0 ? (
                    <p className="text-xs text-gray-400 px-1">No values</p>
                  ) : (
                    paymentTermsOptions.map((p) => (
                      <label key={p} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer px-1 py-0.5 rounded hover:bg-gray-50">
                        <input
                          type="checkbox"
                          checked={paymentTermsFilter.includes(p)}
                          onChange={() => toggleArrayFilter('payment_terms', paymentTermsFilter, p)}
                        />
                        {p}
                      </label>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
              <button
                onClick={clearAllFilters}
                disabled={!hasActiveFilters}
                className="text-sm text-gray-600 hover:text-gray-800 underline disabled:opacity-40 disabled:no-underline disabled:cursor-not-allowed"
              >
                Clear all
              </button>
              <button onClick={() => setFiltersOpen(false)} className="btn btn-primary">
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
