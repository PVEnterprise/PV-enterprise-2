/**
 * Dispatch Modal Component
 * Allows inventory admin to create dispatches for order items
 */
import { useState, useRef } from 'react';
import { X, Package, Plus, Trash2 } from 'lucide-react';
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

const DEFAULT_TERMS = `1) GST 5% included in this invoice.
2) Payment shall be made 100% in advance along side with Delivery.
3) 3 years warrenty.
4) Freight included.`;

const PAYMENT_TERMS_OPTIONS = [
  'Due on Receipt',
  'Net 15',
  'Net 30',
  'Net 45',
  'Net 60',
];

export interface DispatchFormData {
  order_id: string;
  dispatch_date: string;
  courier_name: string;
  tracking_number: string;
  notes: string;
  terms: string;
  payment_terms: string;
  po_number: string;
  dc_number: string;
  invoice_number: string;
  bank_account_name: string;
  bank_account_number: string;
  bank_name: string;
  bank_ifsc: string;
  bank_branch: string;
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
        setResults((data as any).items ?? data);
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
        className="input w-full text-xs"
        autoFocus
      />
      {loading && <p className="text-xs text-gray-500 mt-0.5">Searching...</p>}
      {open && results.length > 0 && (
        <div className="absolute z-50 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 max-h-40 overflow-y-auto">
          {results.map((r) => (
            <button
              key={r.id}
              type="button"
              className="w-full text-left px-2 py-1.5 hover:bg-blue-50 text-xs border-b border-gray-100 last:border-0"
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
        <div className="absolute z-50 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 p-2 text-xs text-gray-500">
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
  const [terms, setTerms] = useState(DEFAULT_TERMS);
  const [paymentTerms, setPaymentTerms] = useState('Due on Receipt');
  const [bankAccountName, setBankAccountName] = useState('Sreedevi Life Sciences');
  const [bankAccountNumber, setBankAccountNumber] = useState('42285740549');
  const [bankName, setBankName] = useState('State Bank of India');
  const [bankIfsc, setBankIfsc] = useState('SBIN0021790');
  const [bankBranch, setBankBranch] = useState('Manikonda, Hyderabad');
  const [poNumber, setPoNumber] = useState('');
  const [dcNumber, setDcNumber] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [dispatchItems, setDispatchItems] = useState<DispatchItemData[]>([]);

  const availableItems = orderItems.filter(
    item => item.inventory_id &&
      (item.outstanding_quantity || 0) > 0 &&
      !dispatchItems.some(di => di.order_item_id === item.id)
  );

  const addItem = (item: OrderItem) => {
    setDispatchItems(prev => [...prev, {
      order_item_id: item.id,
      inventory_id: item.inventory_id!,
      quantity: 1,
      item_description: item.item_description,
      available_stock: item.inventory?.stock_quantity || 0,
      outstanding_quantity: item.outstanding_quantity || 0,
      showAlternate: false,
      alternate: null,
    }]);
  };

  const removeItem = (index: number) => {
    setDispatchItems(prev => prev.filter((_, i) => i !== index));
  };

  const handleQuantityChange = (index: number, newQuantity: number) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    if (newQuantity < 0) newQuantity = 0;
    if (newQuantity > item.outstanding_quantity) newQuantity = item.outstanding_quantity;
    let alternate = item.alternate;
    if (alternate && alternate.quantity > newQuantity) {
      alternate = { ...alternate, quantity: newQuantity };
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
    updatedItems[index] = {
      ...item,
      alternate: {
        inventory_id: selected.id,
        sku: selected.sku,
        description: selected.description,
        available_stock: selected.stock,
        quantity: Math.min(1, item.quantity),
      }
    };
    setDispatchItems(updatedItems);
  };

  const handleAlternateQtyChange = (index: number, newQty: number) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    if (!item.alternate) return;
    if (newQty < 0) newQty = 0;
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
      terms,
      payment_terms: paymentTerms,
      bank_account_name: bankAccountName,
      bank_account_number: bankAccountNumber,
      bank_name: bankName,
      bank_ifsc: bankIfsc,
      bank_branch: bankBranch,
      po_number: poNumber,
      dc_number: dcNumber,
      invoice_number: invoiceNumber,
      items: itemsToDispatch,
    });
  };

  const getTotalItems = () => dispatchItems.filter(item => item.quantity > 0).length;
  const getTotalQuantity = () => dispatchItems.reduce((sum, item) => sum + item.quantity, 0);
  const canSubmit = () => getTotalItems() > 0 && dispatchDate && !isSubmitting;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-4 py-2.5 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <Package size={16} className="text-blue-600" />
            <h2 className="text-base font-bold">Create Dispatch</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={isSubmitting}>
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="px-4 py-3 overflow-y-auto flex-1">
          {/* Dispatch Details */}
          <div className="mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Dispatch Details</h3>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Dispatch Date <span className="text-red-500">*</span></label>
                <input type="date" value={dispatchDate} onChange={(e) => setDispatchDate(e.target.value)} className="input w-full text-xs py-1" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Courier Name</label>
                <input type="text" value={courierName} onChange={(e) => setCourierName(e.target.value)} placeholder="e.g., Blue Dart, DTDC" className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Tracking Number</label>
                <input type="text" value={trackingNumber} onChange={(e) => setTrackingNumber(e.target.value)} placeholder="Enter tracking number" className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Notes</label>
                <input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Additional notes" className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">PO #</label>
                <input type="text" value={poNumber} onChange={(e) => setPoNumber(e.target.value)} placeholder="Purchase Order number" className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">DC #</label>
                <input type="text" value={dcNumber} onChange={(e) => setDcNumber(e.target.value)} placeholder="Delivery Challan number" className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Invoice #</label>
                <input type="text" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} placeholder="Invoice number" className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Payment Terms</label>
                <select value={paymentTerms} onChange={(e) => setPaymentTerms(e.target.value)} className="input w-full text-xs py-1">
                  {PAYMENT_TERMS_OPTIONS.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Terms &amp; Conditions</label>
                <textarea value={terms} onChange={(e) => setTerms(e.target.value)} rows={5} className="input w-full text-xs py-1 resize-none font-mono" />
              </div>
            </div>
          </div>

          {/* Bank Details */}
          <div className="mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Bank Details</h3>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Account Name</label>
                <input type="text" value={bankAccountName} onChange={(e) => setBankAccountName(e.target.value)} className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Account Number</label>
                <input type="text" value={bankAccountNumber} onChange={(e) => setBankAccountNumber(e.target.value)} className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Bank Name</label>
                <input type="text" value={bankName} onChange={(e) => setBankName(e.target.value)} className="input w-full text-xs py-1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">IFSC Code</label>
                <input type="text" value={bankIfsc} onChange={(e) => setBankIfsc(e.target.value)} className="input w-full text-xs py-1" />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Branch</label>
                <input type="text" value={bankBranch} onChange={(e) => setBankBranch(e.target.value)} className="input w-full text-xs py-1" />
              </div>
            </div>
          </div>

          {/* Items to Dispatch — two-column side-by-side layout */}
          <div className="grid grid-cols-2 gap-3">
            {/* Left: Items added to this dispatch */}
            <div className="flex flex-col min-h-0">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex-shrink-0">
                Items to Dispatch {dispatchItems.length > 0 && <span className="ml-1 text-blue-600">({dispatchItems.length})</span>}
              </h3>
              <div className="overflow-y-auto max-h-72 flex-1">
                {dispatchItems.length === 0 ? (
                  <div className="text-center py-6 text-xs text-gray-400 border border-dashed border-gray-300 rounded h-full flex items-center justify-center">
                    <span>Add items from the right panel</span>
                  </div>
                ) : (
                  <div className="space-y-1.5 pr-0.5">
                    {dispatchItems.map((item, index) => {
                      const mainQty = item.alternate ? item.quantity - item.alternate.quantity : item.quantity;
                      return (
                        <div key={item.order_item_id} className="border border-gray-200 rounded p-2 bg-gray-50">
                          {/* Main item row */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-gray-900 truncate">{item.item_description}</p>
                              <div className="flex flex-wrap gap-2 text-xs text-gray-500 mt-0.5">
                                <span>Pending: <span className="font-medium text-orange-600">{item.outstanding_quantity}</span></span>
                                <span>Stock: <span className={`font-medium ${item.available_stock > 0 ? 'text-green-600' : 'text-red-600'}`}>{item.available_stock}</span></span>
                                {item.alternate && (
                                  <span className="text-blue-600">Main: <span className="font-medium">{mainQty}</span></span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5 flex-shrink-0">
                              <div>
                                <label className="block text-xs font-medium text-gray-600 mb-0.5">Dispatch Qty</label>
                                <input
                                  type="number"
                                  value={item.quantity}
                                  onChange={(e) => handleQuantityChange(index, Number(e.target.value))}
                                  onWheel={(e) => e.currentTarget.blur()}
                                  min="0"
                                  max={item.outstanding_quantity}
                                  className="input w-16 text-xs py-1"
                                />
                              </div>
                              <button
                                type="button"
                                onClick={() => removeItem(index)}
                                className="text-gray-400 hover:text-red-500 mt-4"
                                title="Remove from dispatch"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>

                          {/* Alternate item section */}
                          {item.alternate ? (
                            <div className="mt-1.5 pt-1.5 border-t border-dashed border-gray-300">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">Alternate Catalog ID</span>
                                <button type="button" onClick={() => removeAlternate(index)} className="text-red-400 hover:text-red-600">
                                  <Trash2 size={11} />
                                </button>
                              </div>
                              <div className="flex items-start gap-2 bg-purple-50 border border-purple-200 rounded p-1.5">
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs font-medium text-purple-800 truncate">
                                    <span className="font-mono">{item.alternate.sku}</span>
                                    {item.alternate.description && <span className="text-purple-600 ml-1">— {item.alternate.description}</span>}
                                  </p>
                                  <p className="text-xs text-gray-500 mt-0.5">
                                    Stock: <span className={item.alternate.available_stock > 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>{item.alternate.available_stock}</span>
                                    <span className="ml-2 text-gray-400">Main: {mainQty} · Alt: {item.alternate.quantity} · Total: {item.quantity}</span>
                                  </p>
                                </div>
                                <div className="w-16 flex-shrink-0">
                                  <label className="block text-xs font-medium text-gray-600 mb-0.5">Alt Qty</label>
                                  <input
                                    type="number"
                                    value={item.alternate.quantity}
                                    onChange={(e) => handleAlternateQtyChange(index, Number(e.target.value))}
                                    onWheel={(e) => e.currentTarget.blur()}
                                    min="0"
                                    max={item.quantity}
                                    className="input w-full text-xs py-1"
                                  />
                                </div>
                              </div>
                            </div>
                          ) : item.showAlternate ? (
                            <div className="mt-1.5 pt-1.5 border-t border-dashed border-gray-300">
                              <p className="text-xs font-semibold text-purple-700 uppercase tracking-wide mb-1">Search Alternate Catalog ID</p>
                              <AlternateSearch onSelect={(selected) => handleAlternateSelect(index, selected)} />
                            </div>
                          ) : null}

                          {/* Toggle button */}
                          {!item.alternate && (
                            <div className="mt-1.5">
                              <button
                                type="button"
                                onClick={() => toggleAlternate(index)}
                                className="flex items-center gap-0.5 text-xs font-medium text-purple-600 hover:text-purple-800 transition-colors"
                              >
                                <Plus size={10} />
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
            </div>

            {/* Right: Available items to add */}
            <div className="flex flex-col min-h-0">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex-shrink-0">
                Add Items to Dispatch {availableItems.length > 0 && <span className="ml-1 text-gray-400">({availableItems.length})</span>}
              </h4>
              <div className="overflow-y-auto max-h-72 border border-gray-200 rounded divide-y divide-gray-100">
                {availableItems.length === 0 ? (
                  <div className="text-center py-6 text-xs text-gray-400 h-full flex items-center justify-center">
                    <span>All items added</span>
                  </div>
                ) : (
                  availableItems.map((item) => (
                    <div key={item.id} className="flex items-center justify-between gap-2 px-2 py-1.5 hover:bg-gray-50">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{item.item_description}</p>
                        <p className="text-xs text-gray-500">
                          Pending: <span className="text-orange-600 font-medium">{item.outstanding_quantity}</span>
                          <span className="ml-2">Stock: <span className={`font-medium ${(item.inventory?.stock_quantity || 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>{item.inventory?.stock_quantity || 0}</span></span>
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => addItem(item)}
                        className="flex items-center gap-0.5 text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-2 py-1 rounded transition-colors flex-shrink-0"
                      >
                        <Plus size={10} />
                        Add
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Summary */}
          {getTotalItems() > 0 && (
            <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-xs text-gray-600">Total Items</p>
                  <p className="text-lg font-bold text-blue-600">{getTotalItems()}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Total Quantity</p>
                  <p className="text-lg font-bold text-blue-600">{getTotalQuantity()}</p>
                </div>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mt-2 bg-red-50 border border-red-200 rounded p-2">
              <p className="text-xs text-red-800"><strong>Error:</strong> {error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-gray-200 bg-gray-50 flex gap-2 justify-end flex-shrink-0">
          <button onClick={onClose} className="btn btn-secondary text-sm" disabled={isSubmitting}>Cancel</button>
          <button onClick={handleSubmit} className="btn btn-primary text-sm flex items-center gap-2" disabled={!canSubmit()}>
            {isSubmitting && (
              <svg className="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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
