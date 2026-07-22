/**
 * Invoices Page - List generated invoices with a preview pane.
 */
import { useState, useEffect } from 'react';
import { FileText } from 'lucide-react';
import api from '@/services/api';
import { InvoiceListItem } from '@/types';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<InvoiceListItem | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);

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

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className="h-[calc(100vh-80px)] flex gap-4">
      {/* Left Section - Invoice List */}
      <div className="w-[35%] bg-white rounded-lg shadow-sm flex flex-col">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Invoices</h2>
          <p className="text-xs text-gray-500 mt-0.5">{invoices.length} generated</p>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="text-center text-gray-500 py-8">Loading...</div>
          ) : invoices.length === 0 ? (
            <div className="text-center text-gray-500 py-8 px-4">
              <p className="text-sm">No invoices generated yet</p>
            </div>
          ) : (
            invoices.map((inv) => {
              const active = selected?.dispatch_id === inv.dispatch_id;
              return (
                <button
                  key={inv.dispatch_id}
                  onClick={() => setSelected(inv)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-100 transition-colors ${
                    active ? 'bg-primary-50 border-l-4 border-l-primary-600' : 'hover:bg-gray-50 border-l-4 border-l-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold text-gray-900">
                      {inv.invoice_number}
                    </span>
                    <span className="text-xs text-gray-500">{formatDate(inv.dispatch_date)}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-600">
                    {inv.customer_name}
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                    <span>Dispatch: <span className="font-mono">{inv.dispatch_number}</span></span>
                    <span>Order: <span className="font-mono">{inv.order_number}</span></span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Section - Invoice Preview */}
      <div className="w-[65%] bg-white rounded-lg shadow-sm flex flex-col">
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
    </div>
  );
}
