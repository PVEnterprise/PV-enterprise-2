/**
 * Dispatch Modal Component
 * Allows inventory admin to create dispatches for order items
 */
import { useState, useEffect } from 'react';
import { X, Package, AlertCircle } from 'lucide-react';
import { OrderItem, Inventory } from '@/types';

interface DispatchModalProps {
  orderItems: OrderItem[];
  orderId: string;
  onClose: () => void;
  onSubmit: (dispatchData: DispatchFormData) => void;
  isSubmitting: boolean;
  error?: string;
}

export interface DispatchItemData {
  order_item_id: string;
  inventory_id: string;
  quantity: number;
  item_description: string;
  available_stock: number;
  outstanding_quantity: number;
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
  }>;
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

  // Initialize dispatch items with outstanding items
  useEffect(() => {
    const outstandingItems = orderItems
      .filter(item => item.inventory_id && (item.outstanding_quantity || 0) > 0)
      .map(item => ({
        order_item_id: item.id,
        inventory_id: item.inventory_id!,
        quantity: item.outstanding_quantity || 0,
        item_description: item.item_description,
        available_stock: item.inventory?.stock_quantity || 0,
        outstanding_quantity: item.outstanding_quantity || 0
      }));
    
    setDispatchItems(outstandingItems);
  }, [orderItems]);

  const handleQuantityChange = (index: number, newQuantity: number) => {
    const updatedItems = [...dispatchItems];
    const item = updatedItems[index];
    
    // Validate quantity
    if (newQuantity < 0) newQuantity = 0;
    if (newQuantity > item.outstanding_quantity) {
      newQuantity = item.outstanding_quantity;
    }
    if (newQuantity > item.available_stock) {
      newQuantity = item.available_stock;
    }
    
    updatedItems[index] = { ...item, quantity: newQuantity };
    setDispatchItems(updatedItems);
  };

  const handleSubmit = () => {
    // Filter items with quantity > 0
    const itemsToDispatch = dispatchItems
      .filter(item => item.quantity > 0)
      .map(item => ({
        order_item_id: item.order_item_id,
        inventory_id: item.inventory_id,
        quantity: item.quantity
      }));

    if (itemsToDispatch.length === 0) {
      return;
    }

    const formData: DispatchFormData = {
      order_id: orderId,
      dispatch_date: dispatchDate,
      courier_name: courierName,
      tracking_number: trackingNumber,
      notes: notes,
      items: itemsToDispatch
    };

    onSubmit(formData);
  };

  const getTotalItems = () => dispatchItems.filter(item => item.quantity > 0).length;
  const getTotalQuantity = () => dispatchItems.reduce((sum, item) => sum + item.quantity, 0);

  const canSubmit = () => {
    return getTotalItems() > 0 && dispatchDate && !isSubmitting;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <Package size={24} className="text-blue-600" />
            <h2 className="text-2xl font-bold">Create Dispatch</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isSubmitting}
          >
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
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dispatch Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={dispatchDate}
                  onChange={(e) => setDispatchDate(e.target.value)}
                  className="input w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Courier Name
                </label>
                <input
                  type="text"
                  value={courierName}
                  onChange={(e) => setCourierName(e.target.value)}
                  placeholder="e.g., Blue Dart, DTDC"
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tracking Number
                </label>
                <input
                  type="text"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  placeholder="Enter tracking number"
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Additional notes"
                  className="input w-full"
                />
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
              <div className="space-y-3">
                {dispatchItems.map((item, index) => (
                  <div
                    key={item.order_item_id}
                    className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900 mb-1">
                          {item.item_description}
                        </p>
                        <div className="flex gap-4 text-sm text-gray-600">
                          <span>
                            Pending: <span className="font-medium text-orange-600">{item.outstanding_quantity}</span>
                          </span>
                          <span>
                            Available Stock: <span className={`font-medium ${item.available_stock > 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {item.available_stock}
                            </span>
                          </span>
                        </div>
                      </div>
                      
                      <div className="w-32">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Dispatch Qty
                        </label>
                        <input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleQuantityChange(index, Number(e.target.value))}
                          onWheel={(e) => e.currentTarget.blur()}
                          min="0"
                          max={Math.min(item.outstanding_quantity, item.available_stock)}
                          className="input w-full"
                        />
                        {item.quantity > item.available_stock && (
                          <p className="text-xs text-red-600 mt-1">
                            Exceeds available stock
                          </p>
                        )}
                        {item.quantity > item.outstanding_quantity && (
                          <p className="text-xs text-red-600 mt-1">
                            Exceeds outstanding
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
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
              <p className="text-sm text-red-800">
                <strong>Error:</strong> {error}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex gap-3 justify-end flex-shrink-0">
          <button
            onClick={onClose}
            className="btn btn-secondary"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="btn btn-primary flex items-center gap-2"
            disabled={!canSubmit()}
          >
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
