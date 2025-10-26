/**
 * Decode Order Page
 * Clean decode experience with search, selection, and editing
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Order, Inventory } from '@/types';
import { ArrowLeft, X, Save } from 'lucide-react';

interface SelectedItem {
  inventoryId: string;
  quantity: number;
  gstPercentage: number;
}

export default function DecodeOrderPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<Inventory[]>([]);
  const [selectedItems, setSelectedItems] = useState<SelectedItem[]>([]);

  // Fetch order details
  const { data: order, isLoading: orderLoading } = useQuery<Order>({
    queryKey: ['order', orderId],
    queryFn: () => api.getOrder(orderId!),
    enabled: !!orderId,
  });

  // Fetch all inventory for searching
  const { data: allInventory = [] } = useQuery<Inventory[]>({
    queryKey: ['inventory'],
    queryFn: api.getInventory,
  });

  // Pre-populate with existing decoded items
  useEffect(() => {
    if (!order?.items) return;

    const prePopulated: SelectedItem[] = [];
    order.items.forEach(item => {
      if (item.inventory_id && item.inventory) {
        prePopulated.push({
          inventoryId: item.inventory_id,
          quantity: item.quantity,
          gstPercentage: item.gst_percentage || 5
        });
      }
    });

    if (prePopulated.length > 0) {
      setSelectedItems(prePopulated);
    }
  }, [order?.items]);

  // Handle search
  const handleSearch = (term: string) => {
    setSearchTerm(term);

    if (term.trim().length === 0) {
      setSearchResults([]);
      return;
    }

    // Get already selected inventory IDs
    const selectedIds = selectedItems.map(s => s.inventoryId);

    // Filter inventory
    const results = allInventory.filter(inv =>
      !selectedIds.includes(inv.id) &&
      (inv.item_name.toLowerCase().includes(term.toLowerCase()) ||
        inv.sku.toLowerCase().includes(term.toLowerCase()) ||
        inv.description?.toLowerCase().includes(term.toLowerCase()))
    ).slice(0, 10);

    setSearchResults(results);
  };

  // Handle selecting an inventory item
  const handleSelectInventory = (inventoryId: string) => {
    const inventory = allInventory.find(inv => inv.id === inventoryId);
    if (!inventory) return;

    setSelectedItems(prev => [...prev, {
      inventoryId,
      quantity: 1,
      gstPercentage: 5
    }]);

    // Clear search
    setSearchTerm('');
    setSearchResults([]);
  };

  // Handle removing an item
  const handleRemoveItem = (inventoryId: string) => {
    setSelectedItems(prev => prev.filter(item => item.inventoryId !== inventoryId));
  };

  // Handle updating quantity
  const handleUpdateQuantity = (inventoryId: string, quantity: number) => {
    setSelectedItems(prev => prev.map(item =>
      item.inventoryId === inventoryId ? { ...item, quantity } : item
    ));
  };

  // Handle updating GST
  const handleUpdateGST = (inventoryId: string, gstPercentage: number) => {
    setSelectedItems(prev => prev.map(item =>
      item.inventoryId === inventoryId ? { ...item, gstPercentage } : item
    ));
  };

  // Get inventory details
  const getInventoryDetails = (inventoryId: string) => {
    return allInventory.find(inv => inv.id === inventoryId);
  };

  // Save decoded items mutation
  const saveDecodedItemsMutation = useMutation({
    mutationFn: async () => {
      // Use the update decoded items endpoint
      const items = selectedItems.map(item => ({
        inventory_id: item.inventoryId,
        quantity: item.quantity,
        gst_percentage: item.gstPercentage
      }));
      await api.updateDecodedItems(orderId!, items);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      navigate(`/orders/${orderId}`);
    },
  });

  if (orderLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading order...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-red-600">Order not found</div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Split Screen Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side - Decode Interface (70%) */}
        <div className="w-[70%] flex flex-col bg-gray-50">
          {/* Fixed Header */}
          <div className="flex-shrink-0 bg-white border-b border-gray-200 p-4">
            <div className="flex items-center gap-4 mb-3">
              <button
                onClick={() => navigate(`/orders/${orderId}`)}
                className="btn btn-secondary btn-sm flex items-center gap-2"
              >
                <ArrowLeft size={18} />
                Back to Order
              </button>
              <div className="flex-1">
                <h1 className="text-xl font-bold text-gray-900">
                  Decode Order: {order.order_number}
                </h1>
                <p className="text-sm text-gray-600">
                  {order.customer?.hospital_name}
                </p>
              </div>
            </div>

            {/* Search Bar */}
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search inventory by name, SKU, or description..."
              className="input w-full"
            />

            {/* Search Results Dropdown */}
            {searchResults.length > 0 && (
              <div className="mt-2 bg-white border border-gray-200 rounded-lg max-h-60 overflow-y-auto shadow-lg">
                <div className="p-2 space-y-1">
                  {searchResults.map((inv) => (
                    <button
                      key={inv.id}
                      onClick={() => handleSelectInventory(inv.id)}
                      className="w-full text-left p-3 hover:bg-blue-50 border border-gray-200 rounded-lg transition-colors"
                    >
                      <div className="font-medium text-gray-900">{inv.item_name}</div>
                      <div className="text-sm text-gray-600 mt-1">
                        SKU: {inv.sku} | Stock: {inv.stock_quantity} | Price: ₹{inv.unit_price}
                      </div>
                      {inv.description && (
                        <div className="text-xs text-gray-500 mt-1">{inv.description}</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Scrollable Content Area - Fixed max height */}
          <div className="flex-1 overflow-y-auto p-4" style={{ maxHeight: 'calc(100vh - 300px)' }}>
            {selectedItems.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500">
                  <p className="text-lg font-medium">No items selected</p>
                  <p className="text-sm mt-2">Search and select inventory items to decode this order</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {selectedItems.map((selection) => {
                  const inv = getInventoryDetails(selection.inventoryId);
                  if (!inv) return null;

                  return (
                    <div
                      key={selection.inventoryId}
                      className="bg-green-50 border border-green-200 rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <p className="font-medium text-green-900 text-lg">{inv.item_name}</p>
                          <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-green-800">
                            <div>SKU: <span className="font-medium">{inv.sku}</span></div>
                            <div>Stock: <span className="font-medium">{inv.stock_quantity}</span></div>
                            <div>Price: <span className="font-medium">₹{inv.unit_price}</span></div>
                            <div>Category: <span className="font-medium">{inv.category}</span></div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleRemoveItem(selection.inventoryId)}
                          className="text-red-600 hover:text-red-800 p-1"
                        >
                          <X size={20} />
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-4 pt-3 border-t border-green-300">
                        <div>
                          <label className="block text-sm font-medium text-green-900 mb-1">
                            Quantity
                          </label>
                          <input
                            type="number"
                            value={selection.quantity}
                            onChange={(e) => handleUpdateQuantity(selection.inventoryId, parseInt(e.target.value) || 1)}
                            className="input w-full"
                            min="1"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-green-900 mb-1">
                            GST %
                          </label>
                          <input
                            type="number"
                            value={selection.gstPercentage}
                            onChange={(e) => handleUpdateGST(selection.inventoryId, parseFloat(e.target.value) || 0)}
                            className="input w-full"
                            min="0"
                            max="100"
                            step="0.1"
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Fixed Footer */}
          <div className="flex-shrink-0 bg-white border-t border-gray-200 p-4">
            <div className="flex items-center justify-between gap-4">
              <button
                onClick={() => navigate(`/orders/${orderId}`)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => saveDecodedItemsMutation.mutate()}
                disabled={selectedItems.length === 0 || saveDecodedItemsMutation.isPending}
                className="btn btn-primary flex items-center gap-2"
              >
                <Save size={20} />
                {saveDecodedItemsMutation.isPending
                  ? 'Saving...'
                  : `Save ${selectedItems.length} Decoded Item${selectedItems.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>

        {/* Right Side - Sales Rep Description (30%) */}
        <div className="w-[30%] bg-white border-l border-gray-200 overflow-y-auto">
          <div className="p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Requirements</h3>
            {order.sales_rep_description ? (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-gray-900 whitespace-pre-wrap leading-relaxed">
                  {order.sales_rep_description}
                </p>
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-500 italic">
                  No requirements specified for this order
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  (Field: sales_rep_description is empty or null)
                </p>
              </div>
            )}

            {/* Order Info */}
            <div className="mt-6 space-y-3">
              <h3 className="font-semibold text-gray-900">Order Information</h3>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2 text-sm">
                <div>
                  <span className="text-gray-600">Order Number:</span>
                  <span className="ml-2 font-medium">{order.order_number}</span>
                </div>
                <div>
                  <span className="text-gray-600">Customer:</span>
                  <span className="ml-2 font-medium">{order.customer?.hospital_name}</span>
                </div>
                <div>
                  <span className="text-gray-600">Priority:</span>
                  <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${
                    order.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                    order.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                    order.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {order.priority}
                  </span>
                </div>
                {order.source && (
                  <div>
                    <span className="text-gray-600">Source:</span>
                    <span className="ml-2 font-medium">{order.source}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Notes */}
            {order.notes && (
              <div className="mt-6">
                <h3 className="font-semibold text-gray-900 mb-2">Notes</h3>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">
                    {order.notes}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
