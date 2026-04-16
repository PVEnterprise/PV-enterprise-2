/**
 * Dispatch Modal Component
 * Allows inventory admin to create dispatches for order items
 */
import { useState, useEffect, useRef } from 'react';
import { X, Package, AlertCircle, Plus, Trash2 } from 'lucide-react';
import { OrderItem } from '@/types';
import api from '@/services/api';

interface DispatchModalProps {
  orderItems: OrderItem[];
  orderId: string;
  onClose: () => void;
  onSubmit: (dispatchData: DispatchFormData) => void;
  isSubmitting: boolean;
  error?: string;
}

interface AlternateItem {
  inventory_id: string;
  sku: string;
  description: string;
  available_stock: number;
  quantity: number;
}

export interface DispatchItemData {
  order_item_id: string;
  inventory_id: string;
  quantity: number;
  item_description: string;
  available_stock: number;
  outstanding_quantity: number;
  showAlternate: boolean;
  alternate: AlternateItem | null;
}

export interface DispatchFormData {
  order_id: string;
  dispatch_date: string;
  courier_name: string;
  tracking_number: string;
  notes: string;
  items: Array<{
    order_item_id: string;
    inventory_id: string;
    quantity: number;
    alternate_inventory_id?: string;
    alternate_quantity?: number;
  }>;
}

function AlternateSearch({ onSelect }: { onSelect: (item: { id: string; sku: string; description: string; stock: number }) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = (val: string) => {
    setQuery(val);
    if (timer.current) clearTimeout(timer.current);
    if (!val.trim()) { setResults([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.getInventory({ search: val, limit: 10 });
        setResults(data);
        setOpen(true);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 300);
  };

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => search(e.target.value)}
        placeholder="Search by Catalog ID or description..."
        className="input w-full text-sm"
        autoFocus
      />
      {loading && <p className="text-xs text-gray-500 mt-1">Searching...</p>}
      {open && results.length > 0 && (
        <div className="absolute z-50 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto">
          {results.map((r) => (
            <button
              key={r.id}
              type="button"
              className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm border-b border-gray-100 last:border-0"
              onClick={() => {
                onSelect({ id: r.id, sku: r.sku, description: r.description || '', stock: r.stock_quantity });
                setQuery('');
                setResults([]);
                setOpen(false);
              }}
            >
              <span className="font-mono font-medium text-blue-700">{r.sku}</span>
              {r.description && <span className="text-gray-500 ml-2">— {r.description}</span>}
              <span className="text-xs text-gray-400 ml-2">Stock: {r.stock_quantity}</span>
            </button>
          ))}
        </div>
      )}
      {open && results.length === 0 && !loading && (
        <div className="absolute z-50 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 p-3 text-sm text-gray-500">
          No items found
        </div>
      )}
    </div>
  );
}

export default function DispatchModal({
  orderItems,
  orderId,
  onClose,
  onSubmit,
  isSubmitting,
  error
}: DispatchModalProps) {
  const [dispatchDate, setDispatchDate] = useState(new Date().toISOString().split('T')[0]);
  const [courierName, setCourierName] = useState('');
  const [trackingNumber, setTrackingNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [dispatchItems, setDispatchItems] = useState<DispatchItemData[]>([]);

  useEffect(() => {
    const outstandingItems = orderItems
      .filter(item => item.inventory_id && (item.outstanding_quantity || 0) > 0)
      .map(item => ({
        order_item_id: item.id,
        inventory_id: item.inventory_id!,
        quantity: item.outstanding_quantity || 0,
        item_description: item.item_description,
        available_stock: item.inventory?.stock_quantity || 0,
        outstanding_quantity: item.outstanding_quantity || 0,
        showAlternate: false,
        alternate: null,
      }));
    setDispatchItems(outstandingItems);
  }, [orderItems]);

  const handleQuantityChange = (index: number, newQuantity: number) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    if (newQuantity < 0) newQuantity = 0;
    if (newQuantity > item.outstanding_quantity) newQuantity = item.outstanding_quantity;
    // If alternate exists, alternate qty cannot exceed new total - 1
    let alternate = item.alternate;
    if (alternate && alternate.quantity >= newQuantity) {
      alternate = { ...alternate, quantity: newQuantity - 1 > 0 ? newQuantity - 1 : 0 };
    }
    updatedItems[index] = { ...item, quantity: newQuantity, alternate };
    setDispatchItems(updatedItems);
  };

  const toggleAlternate = (index: number) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    updatedItems[index] = { ...item, showAlternate: !item.showAlternate, alternate: item.showAlternate ? null : item.alternate };
    setDispatchItems(updatedItems);
  };

  const handleAlternateSelect = (index: number, selected: { id: string; sku: string; description: string; stock: number }) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    const defaultAltQty = Math.min(1, item.quantity - 1);
    updatedItems[index] = {
      ...item,
      alternate: {
        inventory_id: selected.id,
        sku: selected.sku,
        description: selected.description,
        available_stock: selected.stock,
        quantity: defaultAltQty > 0 ? defaultAltQty : 1,
      }
    };
    setDispatchItems(updatedItems);
  };

  const handleAlternateQtyChange = (index: number, newQty: number) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    if (!item.alternate) return;
    if (newQty < 1) newQty = 1;
    const maxAlt = item.quantity;
    if (newQty > maxAlt) newQty = maxAlt;
    if (newQty > item.alternate.available_stock) newQty = item.alternate.available_stock;
    updatedItems[index] = { ...item, alternate: { ...item.alternate, quantity: newQty } };
    setDispatchItems(updatedItems);
  };

  const removeAlternate = (index: number) => {
    const updatedItems = [...dispatchItems];
    updatedItems[index] = { ...updatedItems[index], alternate: null, showAlternate: false };
    setDispatchItems(updatedItems);
  };

  const handleSubmit = () => {
    const itemsToDispatch = dispatchItems
      .filter(item => item.quantity > 0)
      .map(item => ({
        order_item_id: item.order_item_id,
        inventory_id: item.inventory_id,
        quantity: item.quantity,
        ...(item.alternate && item.alternate.quantity > 0 ? {
          alternate_inventory_id: item.alternate.inventory_id,
          alternate_quantity: item.alternate.quantity,
        } : {}),
      }));

    if (itemsToDispatch.length === 0) return;

    onSubmit({
      order_id: orderId,
      dispatch_date: dispatchDate,
      courier_name: courierName,
      tracking_number: trackingNumber,
      notes,
      items: itemsToDispatch,
    });
  };

  const getTotalItems = () => dispatchItems.filter(item => item.quantity > 0).length;
  const getTotalQuantity = () => dispatchItems.reduce((sum, item) => sum + item.quantity, 0);
  const canSubmit = () => getTotalItems() > 0 && dispatchDate && !isSubmitting;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <Package size={24} className="text-blue-600" />
            <h2 className="text-2xl font-bold">Create Dispatch</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={isSubmitting}>
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {/* Dispatch Details */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Dispatch Details</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dispatch Date <span className="text-red-500">*</span></label>
                <input type="date" value={dispatchDate} onChange={(e) => setDispatchDate(e.target.value)} className="input w-full" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Courier Name</label>
                <input type="text" value={courierName} onChange={(e) => setCourierName(e.target.value)} placeholder="e.g., Blue Dart, DTDC" className="input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tracking Number</label>
                <input type="text" value={trackingNumber} onChange={(e) => setTrackingNumber(e.target.value)} placeholder="Enter tracking number" className="input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Additional notes" className="input w-full" />
              </div>
            </div>
          </div>

          {/* Items to Dispatch */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Items to Dispatch</h3>
            {dispatchItems.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <AlertCircle size={48} className="mx-auto mb-2 text-gray-400" />
                <p>No outstanding items to dispatch</p>
              </div>
            ) : (
              <div className="space-y-4">
                {dispatchItems.map((item, index) => {
                  const mainQty = item.alternate ? item.quantity - item.alternate.quantity : item.quantity;
                  return (
                    <div key={item.order_item_id} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      {/* Main item row */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="font-medium text-gray-900 mb-1">{item.item_description}</p>
                          <div className="flex gap-4 text-sm text-gray-600">
                            <span>Pending: <span className="font-medium text-orange-600">{item.outstanding_quantity}</span></span>
                            <span>Available Stock: <span className={`font-medium ${item.available_stock > 0 ? 'text-green-600' : 'text-red-600'}`}>{item.available_stock}</span></span>
                            {item.alternate && (
                              <span className="text-blue-600">Main Qty: <span className="font-medium">{mainQty}</span></span>
                            )}
                          </div>
                        </div>
                        <div className="w-32">
                          <label className="block text-sm font-medium text-gray-700 mb-1">Dispatch Qty</label>
                          <input
                            type="number"
                            value={item.quantity}
                            onChange={(e) => handleQuantityChange(index, Number(e.target.value))}
                            onWheel={(e) => e.currentTarget.blur()}
                            min="0"
                            max={item.outstanding_quantity}
                            className="input w-full"
                          />
                        </div>
                      </div>

                      {/* Alternate item section */}
                      {item.alternate ? (
                        <div className="mt-3 pt-3 border-t border-dashed border-gray-300">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">Alternate Catalog ID</span>
                            <button type="button" onClick={() => removeAlternate(index)} className="text-red-400 hover:text-red-600">
                              <Trash2 size={14} />
                            </button>
                          </div>
                          <div className="flex items-start gap-3 bg-purple-50 border border-purple-200 rounded-lg p-3">
                            <div className="flex-1">
                              <p className="text-sm font-medium text-purple-800">
                                <span className="font-mono">{item.alternate.sku}</span>
                                {item.alternate.description && <span className="text-purple-600 ml-2">— {item.alternate.description}</span>}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                Stock: <span className={item.alternate.available_stock > 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>{item.alternate.available_stock}</span>
                                <span className="ml-3 text-gray-400">Main: {mainQty} · Alternate: {item.alternate.quantity} · Total: {item.quantity}</span>
                              </p>
                            </div>
                            <div className="w-28">
                              <label className="block text-xs font-medium text-gray-600 mb-1">Alt Qty</label>
                              <input
                                type="number"
                                value={item.alternate.quantity}
                                onChange={(e) => handleAlternateQtyChange(index, Number(e.target.value))}
                                onWheel={(e) => e.currentTarget.blur()}
                                min="1"
                                max={item.quantity}
                                className="input w-full text-sm"
                              />
                              <p className="text-xs text-gray-400 mt-0.5">max {item.quantity}</p>
                            </div>
                          </div>
                        </div>
                      ) : item.showAlternate ? (
                        <div className="mt-3 pt-3 border-t border-dashed border-gray-300">
                          <p className="text-xs font-semibold text-purple-700 uppercase tracking-wide mb-2">Search Alternate Catalog ID</p>
                          <AlternateSearch onSelect={(selected) => handleAlternateSelect(index, selected)} />
                        </div>
                      ) : null}

                      {/* Toggle button */}
                      {!item.alternate && item.quantity > 1 && (
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={() => toggleAlternate(index)}
                            className="flex items-center gap-1 text-xs font-medium text-purple-600 hover:text-purple-800 transition-colors"
                          >
                            <Plus size={12} />
                            {item.showAlternate ? 'Cancel alternate' : 'Add other Catalog ID'}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Summary */}
          {getTotalItems() > 0 && (
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-600">Total Items to Dispatch</p>
                  <p className="text-2xl font-bold text-blue-600">{getTotalItems()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total Quantity</p>
                  <p className="text-2xl font-bold text-blue-600">{getTotalQuantity()}</p>
                </div>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800"><strong>Error:</strong> {error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex gap-3 justify-end flex-shrink-0">
          <button onClick={onClose} className="btn btn-secondary" disabled={isSubmitting}>Cancel</button>
          <button onClick={handleSubmit} className="btn btn-primary flex items-center gap-2" disabled={!canSubmit()}>
            {isSubmitting && (
              <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {isSubmitting ? 'Creating Dispatch...' : 'Create Dispatch'}
          </button>
        </div>
      </div>
    </div>
  );
}
