/**
 * Dispatch Detail Modal Component
 * Shows read-only dispatch information including items and tracking details
 */
import { useState } from 'react';
import { X, Truck, Package, FileText, Download, Trash2 } from 'lucide-react';
import { Dispatch } from '@/types';
import { useAuth } from '@/context/AuthContext';
import api from '@/services/api';

interface DispatchDetailModalProps {
  dispatch: Dispatch;
  onClose: () => void;
  onDeleted?: () => void;
}

export default function DispatchDetailModal({
  dispatch,
  onClose,
  onDeleted
}: DispatchDetailModalProps) {
  const { user } = useAuth();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const canDownload = user?.role_name === 'quoter' || user?.role_name === 'executive';
  const canDelete = user?.role_name === 'inventory_admin' || user?.role_name === 'executive';

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.deleteDispatch(dispatch.id);
      onDeleted?.();
      onClose();
    } catch (err) {
      alert('Failed to delete dispatch. Please try again.');
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  const handleDownloadInvoice = async () => {
    try {
      const response = await fetch(`/api/v1/dispatches/${dispatch.id}/invoice/pdf`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download invoice');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Invoice_${dispatch.dispatch_number}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading invoice:', error);
      alert('Failed to download invoice. Please try again.');
    }
  };

  const handleDownloadDC = async () => {
    try {
      const response = await fetch(`/api/v1/dispatches/${dispatch.id}/dc/pdf`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download delivery challan');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `DC_${dispatch.dispatch_number}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading DC:', error);
      alert('Failed to download delivery challan. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <Truck size={18} className="text-blue-600" />
            <div>
              <h2 className="text-base font-bold leading-tight">{dispatch.dispatch_number}</h2>
              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                dispatch.status === 'delivered' ? 'bg-green-100 text-green-800' :
                dispatch.status === 'in_transit' ? 'bg-blue-100 text-blue-800' :
                dispatch.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {dispatch.status.replace('_', ' ').toUpperCase()}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {canDelete && !confirmDelete && (
              <button
                onClick={() => setConfirmDelete(true)}
                className="flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-800 border border-red-200 hover:border-red-400 px-2 py-1 rounded transition-colors"
              >
                <Trash2 size={13} />
                Delete
              </button>
            )}
            {canDelete && confirmDelete && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-red-700 font-medium">Confirm delete?</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="text-xs font-semibold text-white bg-red-600 hover:bg-red-700 px-2 py-1 rounded"
                >
                  {deleting ? 'Deleting...' : 'Yes, Delete'}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="text-xs font-medium text-gray-600 hover:text-gray-800 border border-gray-300 px-2 py-1 rounded"
                >
                  Cancel
                </button>
              </div>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 ml-1">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-4 py-3 overflow-y-auto flex-1">

          {/* Top two-column section */}
          <div className="grid grid-cols-2 gap-3 mb-4">

            {/* Left: compact info table */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="px-2 py-1.5 text-gray-500 font-medium w-28 bg-gray-50">Date</td>
                    <td className="px-2 py-1.5 text-gray-900 font-semibold">
                      {new Date(dispatch.dispatch_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </td>
                  </tr>
                  {dispatch.invoice_number && (
                    <tr className="border-b border-gray-100">
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Invoice #</td>
                      <td className="px-2 py-1.5 text-gray-900 font-mono font-semibold">{dispatch.invoice_number}</td>
                    </tr>
                  )}
                  {dispatch.po_number && (
                    <tr className="border-b border-gray-100">
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">PO #</td>
                      <td className="px-2 py-1.5 text-gray-900 font-mono font-semibold">{dispatch.po_number}</td>
                    </tr>
                  )}
                  {dispatch.dc_number && (
                    <tr className="border-b border-gray-100">
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">DC #</td>
                      <td className="px-2 py-1.5 text-gray-900 font-mono font-semibold">{dispatch.dc_number}</td>
                    </tr>
                  )}
                  {dispatch.payment_terms && (
                    <tr className="border-b border-gray-100">
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Payment Terms</td>
                      <td className="px-2 py-1.5 text-gray-900 font-semibold">{dispatch.payment_terms}</td>
                    </tr>
                  )}
                  {dispatch.courier_name && (
                    <tr className="border-b border-gray-100">
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Courier</td>
                      <td className="px-2 py-1.5 text-gray-900">{dispatch.courier_name}</td>
                    </tr>
                  )}
                  {dispatch.tracking_number && (
                    <tr className="border-b border-gray-100">
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Tracking</td>
                      <td className="px-2 py-1.5 text-gray-900 font-mono">{dispatch.tracking_number}</td>
                    </tr>
                  )}
                  {dispatch.notes && (
                    <tr>
                      <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Notes</td>
                      <td className="px-2 py-1.5 text-gray-900">{dispatch.notes}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Right: Bank Details */}
            {(dispatch.bank_account_name || dispatch.bank_name) ? (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-2 py-1.5 bg-gray-50 border-b border-gray-200">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Bank Details</p>
                </div>
                <table className="w-full text-xs">
                  <tbody>
                    {dispatch.bank_account_name && (
                      <tr className="border-b border-gray-100">
                        <td className="px-2 py-1.5 text-gray-500 font-medium w-28 bg-gray-50">Account Name</td>
                        <td className="px-2 py-1.5 text-gray-900 font-semibold">{dispatch.bank_account_name}</td>
                      </tr>
                    )}
                    {dispatch.bank_account_number && (
                      <tr className="border-b border-gray-100">
                        <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Acc. Number</td>
                        <td className="px-2 py-1.5 text-gray-900 font-mono font-semibold">{dispatch.bank_account_number}</td>
                      </tr>
                    )}
                    {dispatch.bank_name && (
                      <tr className="border-b border-gray-100">
                        <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Bank</td>
                        <td className="px-2 py-1.5 text-gray-900">{dispatch.bank_name}</td>
                      </tr>
                    )}
                    {dispatch.bank_ifsc && (
                      <tr className="border-b border-gray-100">
                        <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">IFSC</td>
                        <td className="px-2 py-1.5 text-gray-900 font-mono">{dispatch.bank_ifsc}</td>
                      </tr>
                    )}
                    {dispatch.bank_branch && (
                      <tr>
                        <td className="px-2 py-1.5 text-gray-500 font-medium bg-gray-50">Branch</td>
                        <td className="px-2 py-1.5 text-gray-900">{dispatch.bank_branch}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="border border-dashed border-gray-200 rounded-lg flex items-center justify-center">
                <p className="text-xs text-gray-400">No bank details</p>
              </div>
            )}
          </div>

          {/* Dispatched Items */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Package size={15} className="text-blue-600" />
              <h3 className="text-sm font-semibold">Dispatched Items ({dispatch.items.length})</h3>
              <span className="ml-auto text-xs text-gray-500">
                Total qty: <span className="font-bold text-blue-600">{dispatch.items.reduce((s, i) => s + i.quantity, 0)}</span>
              </span>
            </div>
            <div className="space-y-1.5">
              {dispatch.items.map((item, index) => {
                const mainQty = item.alternate_quantity ? item.quantity - item.alternate_quantity : item.quantity;
                return (
                  <div key={item.id} className="border border-gray-200 rounded p-2 bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-900 truncate">
                          <span className="text-gray-400 mr-1">#{index + 1}</span>
                          {item.inventory_item?.description || 'Item'}
                        </p>
                        {item.inventory_item?.sku && (
                          <p className="text-xs text-gray-500">SKU: <span className="font-mono">{item.inventory_item.sku}</span></p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0 ml-3">
                        <p className="text-xs text-gray-500">Qty</p>
                        <p className="text-lg font-bold text-blue-600">{item.alternate_quantity ? mainQty : item.quantity}</p>
                      </div>
                    </div>
                    {item.alternate_inventory_item && item.alternate_quantity ? (
                      <div className="mt-1.5 pt-1.5 border-t border-dashed border-gray-300">
                        <div className="flex items-center justify-between bg-purple-50 border border-purple-200 rounded px-2 py-1">
                          <div className="min-w-0 flex-1">
                            <span className="text-xs font-semibold text-purple-700">Alt: </span>
                            <span className="text-xs font-mono text-purple-800">{item.alternate_inventory_item.sku}</span>
                            {item.alternate_inventory_item.description && (
                              <span className="text-xs text-purple-600 ml-1">— {item.alternate_inventory_item.description}</span>
                            )}
                          </div>
                          <p className="text-sm font-bold text-purple-600 ml-2">{item.alternate_quantity}</p>
                        </div>
                        <p className="text-xs text-gray-400 mt-0.5">Main: {mainQty} · Alt: {item.alternate_quantity} · Total: {item.quantity}</p>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Terms & Conditions */}
          {dispatch.terms && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Terms &amp; Conditions</p>
              <div className="bg-gray-50 border border-gray-200 rounded p-3">
                <p className="text-xs text-gray-700 whitespace-pre-line">{dispatch.terms}</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-gray-200 bg-gray-50 flex justify-between items-center flex-shrink-0">
          {canDownload ? (
            <div className="flex gap-2">
              <button onClick={handleDownloadInvoice} className="btn btn-primary btn-sm flex items-center gap-1.5">
                <FileText size={14} />
                Download Invoice
              </button>
              <button onClick={handleDownloadDC} className="btn btn-secondary btn-sm flex items-center gap-1.5">
                <Download size={14} />
                Download DC
              </button>
            </div>
          ) : <div />}
          <button onClick={onClose} className="btn btn-secondary btn-sm">Close</button>
        </div>
      </div>
    </div>
  );
}
