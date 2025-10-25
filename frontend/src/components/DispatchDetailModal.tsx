/**
 * Dispatch Detail Modal Component
 * Shows read-only dispatch information including items and tracking details
 */
import { X, Truck, Package, Calendar, MapPin } from 'lucide-react';
import { Dispatch } from '@/types';

interface DispatchDetailModalProps {
  dispatch: Dispatch;
  onClose: () => void;
}

export default function DispatchDetailModal({
  dispatch,
  onClose
}: DispatchDetailModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <Truck size={28} className="text-blue-600" />
            <div>
              <h2 className="text-2xl font-bold">{dispatch.dispatch_number}</h2>
              <p className="text-sm text-gray-600">Dispatch Details</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {/* Status Badge */}
          <div className="mb-6">
            <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${
              dispatch.status === 'delivered' ? 'bg-green-100 text-green-800' :
              dispatch.status === 'in_transit' ? 'bg-blue-100 text-blue-800' :
              dispatch.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {dispatch.status.replace('_', ' ').toUpperCase()}
            </span>
          </div>

          {/* Dispatch Information */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-1">
                <Calendar size={16} />
                <label className="text-sm font-medium">Dispatch Date</label>
              </div>
              <p className="text-gray-900 font-medium">
                {new Date(dispatch.dispatch_date).toLocaleDateString('en-IN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </p>
            </div>

            {dispatch.courier_name && (
              <div>
                <div className="flex items-center gap-2 text-gray-600 mb-1">
                  <Truck size={16} />
                  <label className="text-sm font-medium">Courier Service</label>
                </div>
                <p className="text-gray-900 font-medium">{dispatch.courier_name}</p>
              </div>
            )}

            {dispatch.tracking_number && (
              <div>
                <div className="flex items-center gap-2 text-gray-600 mb-1">
                  <MapPin size={16} />
                  <label className="text-sm font-medium">Tracking Number</label>
                </div>
                <p className="text-gray-900 font-medium font-mono">{dispatch.tracking_number}</p>
              </div>
            )}

            {dispatch.notes && (
              <div className="col-span-2">
                <label className="text-sm font-medium text-gray-600 mb-1 block">Notes</label>
                <p className="text-gray-900">{dispatch.notes}</p>
              </div>
            )}
          </div>

          {/* Dispatched Items */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Package size={20} className="text-blue-600" />
              <h3 className="text-lg font-semibold">Dispatched Items ({dispatch.items.length})</h3>
            </div>
            
            <div className="space-y-2">
              {dispatch.items.map((item, index) => (
                <div
                  key={item.id}
                  className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-gray-500">#{index + 1}</span>
                        <p className="font-medium text-gray-900">
                          {item.inventory_item?.item_name || 'Item'}
                        </p>
                      </div>
                      {item.inventory_item?.sku && (
                        <p className="text-sm text-gray-600">SKU: {item.inventory_item.sku}</p>
                      )}
                    </div>
                    
                    <div className="text-right">
                      <p className="text-sm text-gray-600">Quantity</p>
                      <p className="text-2xl font-bold text-blue-600">{item.quantity}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Summary */}
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Total Items</p>
                <p className="text-xl font-bold text-blue-600">{dispatch.items.length}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Quantity</p>
                <p className="text-xl font-bold text-blue-600">
                  {dispatch.items.reduce((sum, item) => sum + item.quantity, 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Dispatched On</p>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(dispatch.created_at).toLocaleDateString('en-IN')}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end flex-shrink-0">
          <button
            onClick={onClose}
            className="btn btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
