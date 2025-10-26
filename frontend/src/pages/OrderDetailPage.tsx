/**
 * Order Detail Page
 * Shows order details with role-based workflow actions
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Order, OrderItem, Inventory, Dispatch } from '@/types';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Edit, Check, X, Search, FileText, Package, Truck, ChevronDown, ChevronUp } from 'lucide-react';
import AttachmentManager from '@/components/common/AttachmentManager';
import DispatchModal, { DispatchFormData } from '@/components/DispatchModal';
import DispatchDetailModal from '@/components/DispatchDetailModal';

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [decodingItem, setDecodingItem] = useState<OrderItem | null>(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [inventorySearch, setInventorySearch] = useState('');
  const [decodedItems, setDecodedItems] = useState<Array<{
    inventory: Inventory;
    quantity: number;
    unitPrice: number;
    gstPercentage: number;
  }>>([]);
  const [currentQuantity, setCurrentQuantity] = useState<number>(1);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const { data: order, isLoading } = useQuery<Order>({
    queryKey: ['order', orderId],
    queryFn: () => api.getOrder(orderId!),
    enabled: !!orderId,
  });

  // Fetch attachments to check if PO is uploaded
  const { data: attachments = [] } = useQuery<any[]>({
    queryKey: ['attachments', 'order', orderId],
    queryFn: async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/attachments/order/${orderId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) return [];
      return response.json();
    },
    enabled: !!orderId,
  });

  // Debounce search with 250ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(inventorySearch);
    }, 250);
    return () => clearTimeout(timer);
  }, [inventorySearch]);

  // Search inventory items
  const { data: inventoryItems } = useQuery<Inventory[]>({
    queryKey: ['inventory', debouncedSearch],
    queryFn: () => api.getInventory({ search: debouncedSearch }),
    enabled: debouncedSearch.length > 0,
  });

  // Filter out already selected items
  const availableItems = inventoryItems?.filter(
    item => !decodedItems.some(decoded => decoded.inventory.id === item.id)
  ) || [];

  // Check permissions
  const canDecode = user?.role?.permissions?.['order:update'] === true;
  const canApprove = user?.role?.permissions?.['order:approve'] === true;

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-blue-100 text-blue-800',
      pending_approval: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      completed: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      low: 'bg-blue-100 text-blue-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      urgent: 'bg-red-100 text-red-800',
    };
    return colors[priority] || 'bg-gray-100 text-gray-800';
  };

  const handleDecodeItem = (item: OrderItem) => {
    setDecodingItem(item);
    
    // If item is already decoded, pre-populate with existing data
    if (item.inventory_id && item.inventory) {
      setDecodedItems([{
        inventory: item.inventory,
        quantity: item.quantity || 1,
        unitPrice: item.unit_price ? Number(item.unit_price) : item.inventory.unit_price,
        gstPercentage: item.gst_percentage ? Number(item.gst_percentage) : 18.00,
      }]);
    } else {
      setDecodedItems([]);
    }
    
    setCurrentQuantity(item.quantity || 1);
    setInventorySearch('');
  };

  const handleEditAllDecodedItems = async () => {
    if (!order || !order.items) {
      return;
    }
    
    // Find all decoded items
    let decodedOrderItems = order.items.filter(item => item.inventory_id);
    
    if (decodedOrderItems.length === 0) {
      alert('No decoded items to edit. Please decode items first.');
      return;
    }
    
    // Check if inventory data is loaded
    let itemsWithInventory = decodedOrderItems.filter(item => item.inventory);
    
    if (itemsWithInventory.length === 0) {
      // Inventory data not loaded - fetch fresh data from API
      try {
        const freshOrder = await api.getOrder(orderId!);
        console.log('Fresh order from API:', freshOrder);
        console.log('Fresh order items:', freshOrder?.items);
        
        if (freshOrder?.items) {
          decodedOrderItems = freshOrder.items.filter((item: OrderItem) => item.inventory_id);
          console.log('Decoded items from fresh data:', decodedOrderItems);
          
          itemsWithInventory = decodedOrderItems.filter((item: OrderItem) => item.inventory);
          console.log('Items with inventory:', itemsWithInventory);
          
          // Update the query cache with fresh data
          queryClient.setQueryData(['order', orderId], freshOrder);
        }
      } catch (error) {
        console.error('Failed to fetch order:', error);
      }
      
      if (itemsWithInventory.length === 0) {
        console.error('Still no inventory data after API fetch');
        alert('Unable to load inventory data. The backend is not returning inventory information. Please check backend logs.');
        return;
      }
    }
    
    // Set the first item as the decoding item (MUST be set to open modal)
    setDecodingItem(decodedOrderItems[0]);
    
    // Pre-populate with ALL decoded items that have inventory data
    const allDecodedItems = itemsWithInventory.map(item => ({
      inventory: item.inventory!,
      quantity: item.quantity || 1,
      unitPrice: item.unit_price ? Number(item.unit_price) : item.inventory!.unit_price,
      gstPercentage: item.gst_percentage ? Number(item.gst_percentage) : 18.00,
    }));
    
    setDecodedItems(allDecodedItems);
    setInventorySearch('');
  };

  const handleSelectInventory = (inventory: Inventory) => {
    // Add to decoded items list with default 18% GST
    setDecodedItems([...decodedItems, {
      inventory,
      quantity: currentQuantity,
      unitPrice: inventory.unit_price,
      gstPercentage: 18,
    }]);
    setCurrentQuantity(1);
    setInventorySearch('');
  };

  const handleRemoveItem = (index: number) => {
    setDecodedItems(decodedItems.filter((_, i) => i !== index));
  };

  const handleUpdateItemQuantity = (index: number, quantity: number) => {
    const updated = [...decodedItems];
    updated[index].quantity = quantity;
    setDecodedItems(updated);
  };

  const handleUpdateItemGst = (index: number, gst: number) => {
    const updated = [...decodedItems];
    updated[index].gstPercentage = gst;
    setDecodedItems(updated);
  };

  const calculateTotals = () => {
    let subtotal = 0;
    let gstAmount = 0;
    
    decodedItems.forEach(item => {
      const itemSubtotal = item.quantity * item.unitPrice;
      const itemGst = (itemSubtotal * item.gstPercentage) / 100;
      subtotal += itemSubtotal;
      gstAmount += itemGst;
    });
    
    const total = subtotal + gstAmount;
    return { subtotal, gstAmount, total };
  };

  const decodeMutation = useMutation({
    mutationFn: async () => {
      if (!decodingItem || decodedItems.length === 0) throw new Error('No items to decode');
      
      const items = decodedItems.map(item => ({
        inventory_id: item.inventory.id,
        unit_price: item.unitPrice,
        quantity: item.quantity,
        gst_percentage: item.gstPercentage,
      }));
      
      // Check if we're editing all decoded items (multiple items already decoded)
      const isEditingAll = order?.items?.filter(item => item.inventory_id).length! > 0 && 
                           decodedItems.length > 1;
      
      if (isEditingAll) {
        // Use update endpoint to replace all decoded items
        return api.updateDecodedItems(orderId!, items);
      } else {
        // Use decode endpoint for initial decode or single item
        return api.decodeOrderItemMultiple(orderId!, decodingItem.id, items);
      }
    },
    onSuccess: async () => {
      // Invalidate and refetch to ensure inventory data is loaded
      await queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      await queryClient.refetchQueries({ queryKey: ['order', orderId] });
      setDecodingItem(null);
      setDecodedItems([]);
      setInventorySearch('');
    },
    onError: (error: any) => {
      // Keep error visible in modal
      console.error('Decode error:', error);
    },
  });

  const submitForApprovalMutation = useMutation({
    mutationFn: () => api.submitOrderForApproval(orderId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    },
  });

  const approveMutation = useMutation({
    mutationFn: (comments?: string) => api.approveOrder(orderId!, comments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (comments: string) => api.rejectOrder(orderId!, { reason: comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleApprove = () => {
    approveMutation.mutate(undefined);
  };

  const handleReject = () => {
    setShowRejectModal(true);
  };

  const handleRejectSubmit = () => {
    if (rejectionReason.trim()) {
      rejectMutation.mutate(rejectionReason.trim());
      setShowRejectModal(false);
      setRejectionReason('');
    }
  };

  const handleRejectCancel = () => {
    setShowRejectModal(false);
    setRejectionReason('');
    rejectMutation.reset();
  };

  const handleGetQuotation = async () => {
    try {
      // Fetch PDF with authentication
      const response = await fetch(`/api/v1/orders/${orderId}/quotation/pdf`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to generate quotation');
      }

      // Get the PDF blob
      const blob = await response.blob();
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Quotation_${order?.order_number || 'order'}.pdf`;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading quotation:', error);
      alert('Failed to generate quotation. Please try again.');
    }
  };

  // Mark quote sent to customer
  const quoteSentMutation = useMutation({
    mutationFn: () => api.post(`/orders/${orderId}/quote-sent`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to mark quotation as sent');
    },
  });

  // Request PO approval
  const requestPOApprovalMutation = useMutation({
    mutationFn: () => api.post(`/orders/${orderId}/request-po-approval`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to request PO approval');
    },
  });

  // Approve PO
  const approvePOMutation = useMutation({
    mutationFn: () => api.post(`/orders/${orderId}/approve-po`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to approve PO');
    },
  });

  // Reject PO
  const [showPORejectModal, setShowPORejectModal] = useState(false);
  const [poRejectionReason, setPORejectionReason] = useState('');

  const rejectPOMutation = useMutation({
    mutationFn: (reason: string) => api.post(`/orders/${orderId}/reject-po`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      setShowPORejectModal(false);
      setPORejectionReason('');
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to reject PO');
    },
  });

  const handlePORejectSubmit = () => {
    if (poRejectionReason.trim()) {
      rejectPOMutation.mutate(poRejectionReason.trim());
    }
  };

  // Dispatch Management
  const [showDispatchModal, setShowDispatchModal] = useState(false);
  const [selectedDispatch, setSelectedDispatch] = useState<Dispatch | null>(null);
  
  // Collapsible sections state
  const [isOrderItemsExpanded, setIsOrderItemsExpanded] = useState(true);
  const [isDispatchesExpanded, setIsDispatchesExpanded] = useState(true);
  const [isOutstandingExpanded, setIsOutstandingExpanded] = useState(true);

  // Fetch dispatches for this order
  const { data: dispatches = [] } = useQuery<Dispatch[]>({
    queryKey: ['dispatches', orderId],
    queryFn: () => api.getOrderDispatches(orderId!),
    enabled: !!orderId && order?.workflow_stage === 'inventory_check',
  });

  // Create dispatch mutation
  const createDispatchMutation = useMutation({
    mutationFn: (data: DispatchFormData) => api.createDispatch(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['dispatches', orderId] });
      setShowDispatchModal(false);
    },
    onError: (error: any) => {
      // Error is displayed in the modal
      console.error('Failed to create dispatch:', error);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading order details...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Order not found</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header - Compact */}
      <div className="mb-3">
        <button
          onClick={() => navigate('/orders')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-2 text-sm"
        >
          <ArrowLeft size={16} className="mr-1" />
          Back to Orders
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{order.order_number}</h1>
            <p className="text-xs text-gray-500">
              {new Date(order.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(order.status)}`}>
              {order.status.replace('_', ' ').toUpperCase()}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityBadge(order.priority)}`}>
              {order.priority.toUpperCase()}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Main Content - More width for order items */}
        <div className="lg:col-span-3 space-y-4">
          {/* Customer Info - Compact */}
          <div className="card p-3">
            <h2 className="text-sm font-semibold mb-2 text-gray-700">Customer Information</h2>
            <div className="grid grid-cols-4 gap-3">
              <div>
                <p className="text-xs text-gray-500">Customer</p>
                <p className="text-sm font-medium">{order.customer?.name || order.customer?.hospital_name || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Hospital</p>
                <p className="text-sm font-medium">{order.customer?.hospital_name || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Contact</p>
                <p className="text-sm font-medium">{order.customer?.contact_person || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Email</p>
                <p className="text-sm font-medium">{order.customer?.email || '-'}</p>
              </div>
            </div>
          </div>

          {/* Order Items */}
          <div className="card flex flex-col max-h-[600px]">
            {/* Fixed Header */}
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <button
                onClick={() => setIsOrderItemsExpanded(!isOrderItemsExpanded)}
                className="flex items-center gap-2 hover:text-blue-600 transition-colors"
              >
                <h2 className="text-xl font-semibold">Order Items</h2>
                {isOrderItemsExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>
              {canDecode && order.status === 'draft' && (
                <button
                  onClick={() => navigate(`/orders/${orderId}/decode`)}
                  className="btn btn-primary btn-sm"
                >
                  <Edit size={16} className="mr-1" />
                  {order.items?.some(item => !item.inventory_id) ? 'Decode Items' : 'Edit Decoded Items'}
                </button>
              )}
            </div>

            {/* Scrollable Table */}
            {isOrderItemsExpanded && (
            <div className="flex-1 overflow-y-auto">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0">
                  <tr className="border-b">
                    <th className="text-left p-3 text-sm font-semibold text-gray-700">Item</th>
                    <th className="text-center p-3 text-sm font-semibold text-gray-700">Qty</th>
                    <th className="text-right p-3 text-sm font-semibold text-gray-700">Unit Price</th>
                    <th className="text-right p-3 text-sm font-semibold text-gray-700">GST %</th>
                    <th className="text-right p-3 text-sm font-semibold text-gray-700">Subtotal</th>
                    <th className="text-right p-3 text-sm font-semibold text-gray-700">GST Amt</th>
                    <th className="text-right p-3 text-sm font-semibold text-gray-700">Total</th>
                    <th className="text-center p-3 text-sm font-semibold text-gray-700">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items?.map((item: OrderItem) => {
                    const unitPrice = item.unit_price ? Number(item.unit_price) : 0;
                    const gstPercentage = item.gst_percentage ? Number(item.gst_percentage) : 0;
                    const subtotal = item.quantity * unitPrice;
                    const gstAmount = (subtotal * gstPercentage) / 100;
                    const total = subtotal + gstAmount;

                    return (
                      <tr key={item.id} className="border-b hover:bg-gray-50">
                        <td className="p-3">
                          <div>
                            <p className="font-medium text-gray-900">{item.inventory?.item_name || item.item_description}</p>
                            <p className="text-xs text-gray-500">{item.inventory?.sku || 'Not decoded'}</p>
                          </div>
                        </td>
                        <td className="p-3 text-center text-sm text-gray-900">{item.quantity}</td>
                        <td className="p-3 text-right text-sm text-gray-900">₹{unitPrice.toFixed(2)}</td>
                        <td className="p-3 text-right text-sm text-gray-900">{gstPercentage.toFixed(2)}%</td>
                        <td className="p-3 text-right text-sm text-gray-900">₹{subtotal.toFixed(2)}</td>
                        <td className="p-3 text-right text-sm text-gray-900">₹{gstAmount.toFixed(2)}</td>
                        <td className="p-3 text-right text-sm font-semibold text-gray-900">₹{total.toFixed(2)}</td>
                        <td className="p-3 text-center">
                          {item.inventory_id ? (
                            <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Decoded</span>
                          ) : (
                            <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">Not Decoded</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            )}

            {/* Fixed Footer - Order Total */}
            {isOrderItemsExpanded && order.items?.some(item => item.inventory_id) && (
              <div className="border-t-2 border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-4 flex-shrink-0">
                <div className="flex justify-end space-x-8">
                {(() => {
                  let orderSubtotal = 0;
                  let orderGstAmount = 0;
                  
                  order.items?.forEach(item => {
                    if (item.inventory_id) {
                      const unitPrice = item.unit_price ? Number(item.unit_price) : 0;
                      const gstPercentage = item.gst_percentage ? Number(item.gst_percentage) : 0;
                      const itemSubtotal = item.quantity * unitPrice;
                      const itemGst = (itemSubtotal * gstPercentage) / 100;
                      
                      orderSubtotal += itemSubtotal;
                      orderGstAmount += itemGst;
                    }
                  });
                  
                  const orderTotal = orderSubtotal + orderGstAmount;
                  
                  return (
                    <>
                      <div className="text-right">
                        <p className="text-xs text-gray-600">Subtotal</p>
                        <p className="text-sm font-semibold text-gray-900">₹{orderSubtotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-600">Total GST</p>
                        <p className="text-sm font-semibold text-gray-900">₹{orderGstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-600">Grand Total</p>
                        <p className="text-lg font-bold text-blue-600">₹{orderTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                      </div>
                    </>
                  );
                })()}
                </div>
              </div>
            )}
          </div>

          {/* Dispatches Section - Only show in inventory_check stage */}
          {order.workflow_stage === 'inventory_check' && (
            <>
              {/* Dispatches */}
              {dispatches.length > 0 && (
                <div className="card">
                  <div className="flex items-center justify-between mb-4">
                    <button
                      onClick={() => setIsDispatchesExpanded(!isDispatchesExpanded)}
                      className="flex items-center gap-2 hover:text-blue-600 transition-colors"
                    >
                      <Truck size={24} className="text-blue-600" />
                      <h2 className="text-xl font-semibold">Dispatches ({dispatches.length})</h2>
                      {isDispatchesExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>
                  </div>
                  {isDispatchesExpanded && (
                  <div className="space-y-3">
                    {dispatches.map((dispatch) => (
                      <div 
                        key={dispatch.id} 
                        className="border border-gray-200 rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer"
                        onClick={() => setSelectedDispatch(dispatch)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="font-semibold text-blue-600 hover:text-blue-800 underline">
                              {dispatch.dispatch_number}
                            </p>
                            <p className="text-sm text-gray-600">
                              Date: {new Date(dispatch.dispatch_date).toLocaleDateString()}
                            </p>
                          </div>
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                            {dispatch.status}
                          </span>
                        </div>
                        {dispatch.courier_name && (
                          <p className="text-sm text-gray-600">
                            Courier: {dispatch.courier_name}
                            {dispatch.tracking_number && ` - ${dispatch.tracking_number}`}
                          </p>
                        )}
                        <div className="mt-2 text-sm text-gray-600">
                          <p className="font-medium">Items: {dispatch.items.length}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  )}
                </div>
              )}

              {/* Outstanding Items */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <button
                    onClick={() => setIsOutstandingExpanded(!isOutstandingExpanded)}
                    className="flex items-center gap-2 hover:text-blue-600 transition-colors"
                  >
                    <Package size={24} className="text-orange-600" />
                    <h2 className="text-xl font-semibold">Outstanding Items</h2>
                    {isOutstandingExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>
                  {(user?.role_name === 'inventory_admin' || user?.role_name === 'executive') && (
                    <button
                      onClick={() => setShowDispatchModal(true)}
                      className="btn btn-primary btn-sm flex items-center gap-1"
                      disabled={order.items?.filter(item => item.inventory_id && (item.outstanding_quantity || item.quantity) > 0).length === 0}
                    >
                      <Package size={16} />
                      Create Dispatch
                    </button>
                  )}
                </div>
                {isOutstandingExpanded && (
                <div className="space-y-2">
                  {order.items?.filter(item => item.inventory_id && (item.outstanding_quantity || item.quantity) > 0).length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <Package size={48} className="mx-auto mb-2 text-gray-400" />
                      <p>All items have been dispatched</p>
                    </div>
                  ) : (
                    order.items
                      ?.filter(item => item.inventory_id && (item.outstanding_quantity || item.quantity) > 0)
                      .map((item) => {
                        const outstanding = item.outstanding_quantity ?? item.quantity;
                        const dispatched = item.dispatched_quantity ?? 0;
                        const status = item.status || 'pending';
                        const displayName = item.inventory?.item_name || item.item_description;
                        const sku = item.inventory?.sku;
                        
                        return (
                          <div key={item.id} className="border border-gray-200 rounded-lg p-3 bg-white">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div>
                                  <p className="font-medium text-gray-900">{displayName}</p>
                                  {sku && <p className="text-xs text-gray-500 mt-0.5">SKU: {sku}</p>}
                                </div>
                                <div className="mt-1 flex gap-4 text-sm">
                                  <span className="text-gray-600">
                                    Ordered: <span className="font-medium">{item.quantity}</span>
                                  </span>
                                  <span className="text-gray-600">
                                    Dispatched: <span className="font-medium text-blue-600">{dispatched}</span>
                                  </span>
                                  <span className="text-gray-600">
                                    Outstanding: <span className="font-medium text-orange-600">{outstanding}</span>
                                  </span>
                                </div>
                              </div>
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                status === 'completed' ? 'bg-green-100 text-green-800' :
                                status === 'partial' ? 'bg-orange-100 text-orange-800' :
                                status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {status}
                              </span>
                            </div>
                          </div>
                        );
                      })
                  )}
                </div>
                )}
              </div>
            </>
          )}

          {/* Notes */}
          {order.notes && (
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Order Notes</h2>
              <p className="text-gray-700 whitespace-pre-wrap">{order.notes}</p>
            </div>
          )}
        </div>

        {/* Sidebar - Compact */}
        <div className="space-y-3">
          {/* Workflow Actions */}
          <div className="card p-3">
            <h2 className="text-sm font-semibold mb-2">Actions</h2>
            
            {/* Decoder Actions */}
            {canDecode && order.status === 'draft' && (
              <div className="space-y-2">
                <p className="text-xs text-gray-600 mb-2">
                  Decode all items and submit
                </p>
                <button
                  onClick={() => submitForApprovalMutation.mutate()}
                  className="btn btn-primary btn-sm w-full text-xs"
                  disabled={order.items?.some(item => !item.inventory_id) || submitForApprovalMutation.isPending}
                >
                  <Check size={14} className="mr-1" />
                  {submitForApprovalMutation.isPending ? 'Submitting...' : 'Submit'}
                </button>
              </div>
            )}

            {/* Executive Submit for Approval (if order is still draft) */}
            {canApprove && order.status === 'draft' && !canDecode && (
              <div className="space-y-2">
                <p className="text-xs text-gray-600 mb-2">
                  Submit order for approval
                </p>
                <button
                  onClick={() => submitForApprovalMutation.mutate()}
                  className="btn btn-primary btn-sm w-full text-xs"
                  disabled={order.items?.some(item => !item.inventory_id) || submitForApprovalMutation.isPending}
                >
                  <Check size={14} className="mr-1" />
                  {submitForApprovalMutation.isPending ? 'Submitting...' : 'Submit for Approval'}
                </button>
              </div>
            )}

            {/* Executive Approve/Reject Actions */}
            {canApprove && order.status === 'pending_approval' && (
              <div className="space-y-2">
                <p className="text-xs text-gray-600 mb-2">
                  Review and approve/reject
                </p>
                <div className="flex gap-1">
                  <button
                    onClick={handleApprove}
                    className="btn btn-sm btn-primary flex-1 text-xs"
                    disabled={approveMutation.isPending}
                  >
                    <Check size={12} className="mr-1" />
                    {approveMutation.isPending ? 'Approving...' : 'Approve'}
                  </button>
                  <button
                    onClick={handleReject}
                    className="btn btn-sm btn-danger flex-1 text-xs"
                    disabled={rejectMutation.isPending}
                  >
                    <X size={12} className="mr-1" />
                    {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
                  </button>
                </div>
              </div>
            )}

            {/* Approved/Quotation Stage */}
            {(order.status === 'approved' && order.workflow_stage === 'quotation') && (
              <div className="space-y-2">
                <div className="text-center py-2">
                  <Check size={32} className="mx-auto text-green-600 mb-1" />
                  <p className="text-sm text-green-600 font-medium">Approved</p>
                  <p className="text-xs text-gray-600">Ready for quotation</p>
                </div>
                {(user?.role_name === 'executive' || (user?.role_name === 'sales_rep' && order.sales_rep_id === user?.id)) && (
                  <>
                    <button
                      onClick={handleGetQuotation}
                      className="btn btn-primary btn-sm w-full text-xs"
                    >
                      <FileText size={14} className="mr-1" />
                      Get Quotation
                    </button>
                    <button
                      onClick={() => quoteSentMutation.mutate()}
                      disabled={quoteSentMutation.isPending}
                      className="btn btn-sm w-full text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
                    >
                      <Check size={14} className="mr-1" />
                      {quoteSentMutation.isPending ? 'Processing...' : 'Quote Sent to Customer'}
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Waiting for Purchase Order */}
            {order.workflow_stage === 'waiting_purchase_order' && (
              <div className="space-y-2">
                <div className="text-center py-2">
                  <FileText size={32} className="mx-auto text-blue-600 mb-1" />
                  <p className="text-sm text-blue-600 font-medium">Waiting for PO</p>
                  <p className="text-xs text-gray-600">Upload purchase order in attachments</p>
                </div>
                {(user?.role_name === 'sales_rep' && order.sales_rep_id === user?.id) && (
                  <>
                    <button
                      onClick={() => {
                        if (!attachments || attachments.length === 0) {
                          alert('Please upload the Purchase Order in the Attachments section before submitting for approval.');
                          return;
                        }
                        requestPOApprovalMutation.mutate();
                      }}
                      disabled={requestPOApprovalMutation.isPending}
                      className="btn btn-primary btn-sm w-full text-xs"
                    >
                      <Check size={14} className="mr-1" />
                      {requestPOApprovalMutation.isPending ? 'Requesting...' : 'PO Uploaded - Request Approval'}
                    </button>
                    <div className={`text-xs text-center py-1 ${attachments && attachments.length > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {attachments && attachments.length > 0 
                        ? `✓ ${attachments.length} attachment(s) uploaded` 
                        : '⚠ No PO uploaded - Please add in Attachments'}
                    </div>
                  </>
                )}
                {user?.role_name === 'executive' && (
                  <>
                    <button
                      onClick={() => {
                        if (!attachments || attachments.length === 0) {
                          alert('Please upload the Purchase Order in the Attachments section before submitting for approval.');
                          return;
                        }
                        requestPOApprovalMutation.mutate();
                      }}
                      disabled={requestPOApprovalMutation.isPending}
                      className="btn btn-primary btn-sm w-full text-xs"
                    >
                      <Check size={14} className="mr-1" />
                      {requestPOApprovalMutation.isPending ? 'Requesting...' : 'PO Uploaded - Request Approval'}
                    </button>
                    <div className={`text-xs text-center py-1 ${attachments && attachments.length > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {attachments && attachments.length > 0 
                        ? `✓ ${attachments.length} attachment(s) uploaded` 
                        : '⚠ No PO uploaded - Please add in Attachments'}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Pending PO Approval */}
            {order.workflow_stage === 'po_approval' && (
              <div className="space-y-2">
                <div className="text-center py-2">
                  <FileText size={32} className="mx-auto text-yellow-600 mb-1" />
                  <p className="text-sm text-yellow-600 font-medium">Pending PO Approval</p>
                  <p className="text-xs text-gray-600">Waiting for executive review</p>
                </div>
                {user?.role_name === 'executive' && (
                  <>
                    <button
                      onClick={() => approvePOMutation.mutate()}
                      disabled={approvePOMutation.isPending}
                      className="btn btn-success btn-sm w-full text-xs"
                    >
                      <Check size={14} className="mr-1" />
                      {approvePOMutation.isPending ? 'Approving...' : 'Approve PO'}
                    </button>
                    <button
                      onClick={() => setShowPORejectModal(true)}
                      className="btn btn-danger btn-sm w-full text-xs"
                    >
                      <X size={14} className="mr-1" />
                      Reject PO
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Order Details */}
          <div className="card p-3">
            <h2 className="text-sm font-semibold mb-2">Details</h2>
            <div className="space-y-2 text-xs">
              <div>
                <p className="text-gray-500">Workflow Stage</p>
                <p className="font-medium">{order.workflow_stage.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-gray-500">Priority</p>
                <p className="font-medium">{order.priority}</p>
              </div>
              <div>
                <p className="text-gray-500">Total Items</p>
                <p className="font-medium">{order.items?.length || 0}</p>
              </div>
              {order.po_number && (
                <div>
                  <p className="text-gray-500">PO Number</p>
                  <p className="font-medium">{order.po_number}</p>
                </div>
              )}
            </div>
          </div>

          {/* Audit Trail */}
          <div className="card p-3">
            <h2 className="text-sm font-semibold mb-2">Audit</h2>
            <div className="space-y-2 text-xs">
              <div>
                <p className="text-gray-500">Created</p>
                <p className="font-medium">{new Date(order.created_at).toLocaleString()}</p>
                {order.created_by && <p className="text-gray-600">by User ID: {order.created_by}</p>}
              </div>
              {order.updated_at !== order.created_at && (
                <div>
                  <p className="text-gray-500">Last Updated</p>
                  <p className="font-medium">{new Date(order.updated_at).toLocaleString()}</p>
                  {order.updated_by && <p className="text-gray-600">by User ID: {order.updated_by}</p>}
                </div>
              )}
            </div>
          </div>

          {/* Attachments */}
          <div className="card p-3">
            <AttachmentManager
              entityType="order"
              entityId={order.id}
              canUpload={true}
              canDelete={true}
            />
          </div>
        </div>
      </div>

      {/* Decode Modal */}
      {decodingItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
            {/* Fixed Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
              <h2 className="text-2xl font-bold">Decode Order Item</h2>
              <button
                onClick={() => {
                  setDecodingItem(null);
                  decodeMutation.reset();
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">

              {/* Search Inventory - Always at Top */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Add Inventory Item
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="text"
                    value={inventorySearch}
                    onChange={(e) => setInventorySearch(e.target.value)}
                    placeholder="Search by SKU or item name..."
                    className="input pl-10"
                  />
                </div>

                {/* Search Results - Filtered */}
                {inventorySearch && availableItems && availableItems.length > 0 && (
                  <div className="mt-2 border rounded-lg max-h-60 overflow-y-auto">
                    {availableItems.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => handleSelectInventory(item)}
                        className="w-full text-left p-3 hover:bg-gray-50 border-b last:border-b-0 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{item.item_name}</p>
                            <p className="text-sm text-gray-500">SKU: {item.sku}</p>
                          </div>
                          <div className="text-right ml-4">
                            <p className="text-sm font-medium text-gray-900">₹{item.unit_price.toLocaleString()}</p>
                            <p className="text-xs text-gray-500">Stock: {item.stock_quantity}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {inventorySearch && availableItems && availableItems.length === 0 && (
                  <p className="mt-2 text-sm text-gray-500 text-center py-4">
                    {inventoryItems && inventoryItems.length > 0 ? 'All matching items already added' : 'No items found'}
                  </p>
                )}
              </div>

              {/* Decoded Items List - Scrollable */}
              {decodedItems.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Decoded Items ({decodedItems.length})</h3>
                  <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
                    {decodedItems.map((item, index) => (
                      <div key={index} className="p-3 bg-gray-50 border rounded-lg">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{item.inventory.item_name}</p>
                            <p className="text-xs text-gray-500">SKU: {item.inventory.sku}</p>
                            <div className="grid grid-cols-3 gap-2 mt-2">
                              <div>
                                <label className="text-xs text-gray-500">Qty</label>
                                <input
                                  type="number"
                                  value={item.quantity}
                                  onChange={(e) => handleUpdateItemQuantity(index, Number(e.target.value))}
                                  onWheel={(e) => e.currentTarget.blur()}
                                  min="1"
                                  className="input input-sm w-full mt-1"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500">Price</label>
                                <input
                                  type="number"
                                  value={item.unitPrice}
                                  readOnly
                                  disabled
                                  className="input input-sm w-full mt-1 bg-gray-100 cursor-not-allowed"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500">GST %</label>
                                <input
                                  type="number"
                                  value={item.gstPercentage}
                                  onChange={(e) => handleUpdateItemGst(index, Number(e.target.value))}
                                  onWheel={(e) => e.currentTarget.blur()}
                                  min="0"
                                  max="100"
                                  step="0.01"
                                  className="input input-sm w-full mt-1"
                                />
                              </div>
                            </div>
                            <div className="mt-2 text-sm space-y-1">
                              <div className="flex justify-between text-gray-600">
                                <span>Subtotal:</span>
                                <span>₹{(item.quantity * item.unitPrice).toLocaleString()}</span>
                              </div>
                              <div className="flex justify-between text-gray-600">
                                <span>GST ({item.gstPercentage}%):</span>
                                <span>₹{((item.quantity * item.unitPrice * item.gstPercentage) / 100).toLocaleString()}</span>
                              </div>
                              <div className="flex justify-between font-medium text-gray-900 border-t pt-1">
                                <span>Total:</span>
                                <span>₹{(item.quantity * item.unitPrice * (1 + item.gstPercentage / 100)).toLocaleString()}</span>
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveItem(index)}
                            className="text-red-600 hover:text-red-800 ml-2"
                          >
                            <X size={20} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Total Calculation */}
              {decodedItems.length > 0 && (
                <div className="mb-6 p-4 bg-gray-50 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Subtotal</span>
                    <span className="font-medium text-gray-900">₹{calculateTotals().subtotal.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">GST (Total)</span>
                    <span className="font-medium text-gray-900">₹{calculateTotals().gstAmount.toLocaleString()}</span>
                  </div>
                  <div className="border-t pt-2 flex items-center justify-between">
                    <span className="text-gray-700 font-semibold">Total Amount</span>
                    <span className="text-2xl font-bold text-gray-900">
                      ₹{calculateTotals().total.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Fixed Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
              {/* Error Display */}
              {decodeMutation.isError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-red-800">
                    <strong>Error:</strong> {(decodeMutation.error as any)?.response?.data?.detail || (decodeMutation.error as any)?.message || 'Failed to decode item'}
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => {
                    setDecodingItem(null);
                    decodeMutation.reset();
                  }}
                  className="btn btn-secondary"
                  disabled={decodeMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  onClick={() => decodeMutation.mutate()}
                  className="btn btn-primary flex items-center"
                  disabled={decodedItems.length === 0 || decodeMutation.isPending}
                >
                  {decodeMutation.isPending && (
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {decodeMutation.isPending ? 'Decoding...' : `Decode with ${decodedItems.length} Item${decodedItems.length !== 1 ? 's' : ''}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reject Order Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full flex flex-col">
            {/* Fixed Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
              <h2 className="text-xl font-bold text-gray-900">Reject Order</h2>
              <button
                onClick={handleRejectCancel}
                className="text-gray-400 hover:text-gray-600"
                disabled={rejectMutation.isPending}
              >
                <X size={24} />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <p className="text-sm text-gray-600 mb-4">
                Please provide a reason for rejecting this order. The order will be sent back to draft status for the decoder to update.
              </p>
              
              <div>
                <label htmlFor="rejectionReason" className="block text-sm font-medium text-gray-700 mb-2">
                  Rejection Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="rejectionReason"
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Enter the reason for rejection..."
                  className="input w-full"
                  rows={4}
                  disabled={rejectMutation.isPending}
                  autoFocus
                />
              </div>

              {/* Error Display */}
              {rejectMutation.isError && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-800">
                    <strong>Error:</strong> {(rejectMutation.error as any)?.response?.data?.detail || (rejectMutation.error as any)?.message || 'Failed to reject order'}
                  </p>
                </div>
              )}
            </div>

            {/* Fixed Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3 flex-shrink-0">
              <button
                onClick={handleRejectCancel}
                className="btn btn-secondary"
                disabled={rejectMutation.isPending}
              >
                Cancel
              </button>
              <button
                onClick={handleRejectSubmit}
                className="btn btn-danger flex items-center"
                disabled={!rejectionReason.trim() || rejectMutation.isPending}
              >
                {rejectMutation.isPending && (
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {rejectMutation.isPending ? 'Rejecting...' : 'Reject Order'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject PO Modal */}
      {showPORejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full flex flex-col">
            {/* Fixed Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
              <h2 className="text-2xl font-bold">Reject Purchase Order</h2>
              <button
                onClick={() => {
                  setShowPORejectModal(false);
                  setPORejectionReason('');
                  rejectPOMutation.reset();
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-4">
              <p className="text-gray-600 mb-4">
                Please provide a reason for rejecting this purchase order. The sales team will be notified.
              </p>
              <textarea
                value={poRejectionReason}
                onChange={(e) => setPORejectionReason(e.target.value)}
                placeholder="Enter rejection reason..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 min-h-[120px]"
                autoFocus
              />
              {rejectPOMutation.isError && (
                <p className="text-red-600 text-sm mt-2">
                  Failed to reject PO. Please try again.
                </p>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowPORejectModal(false);
                  setPORejectionReason('');
                  rejectPOMutation.reset();
                }}
                className="btn btn-secondary"
                disabled={rejectPOMutation.isPending}
              >
                Cancel
              </button>
              <button
                onClick={handlePORejectSubmit}
                className="btn btn-danger flex items-center"
                disabled={!poRejectionReason.trim() || rejectPOMutation.isPending}
              >
                {rejectPOMutation.isPending && (
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {rejectPOMutation.isPending ? 'Rejecting...' : 'Reject PO'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Dispatch Modal */}
      {showDispatchModal && (
        <DispatchModal
          orderItems={order.items || []}
          orderId={orderId!}
          onClose={() => setShowDispatchModal(false)}
          onSubmit={(data) => createDispatchMutation.mutate(data)}
          isSubmitting={createDispatchMutation.isPending}
          error={createDispatchMutation.error?.response?.data?.detail}
        />
      )}

      {/* Dispatch Detail Modal */}
      {selectedDispatch && (
        <DispatchDetailModal
          dispatch={selectedDispatch}
          onClose={() => setSelectedDispatch(null)}
        />
      )}
    </div>
  );
}
