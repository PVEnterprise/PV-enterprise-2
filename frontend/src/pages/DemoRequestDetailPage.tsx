/**
 * Demo Request Detail Page
 * Shows detailed information about a demo request
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { DemoRequest, DemoItem, Customer, Inventory } from '@/types';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Edit, Save, X, Building2, MapPin, User, Calendar, FileText, Package, Search, Plus, Minus, Trash2, Download } from 'lucide-react';

export default function DemoRequestDetailPage() {
  const { demoId } = useParams<{ demoId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<any>({});
  const [showItemsPanel, setShowItemsPanel] = useState(false);
  const [itemSearch, setItemSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedItems, setSelectedItems] = useState<Map<string, { item: Inventory; quantity: number }>>(new Map());
  const [itemError, setItemError] = useState('');

  // Debounce search with 200ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(itemSearch);
    }, 200);
    return () => clearTimeout(timer);
  }, [itemSearch]);

  const { data: demoRequest, isLoading } = useQuery<DemoRequest>({
    queryKey: ['demo-request', demoId],
    queryFn: () => api.getDemoRequest(demoId!),
    enabled: !!demoId,
  });

  const { data: customers } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: () => api.getCustomers({ limit: 10000 }),
    enabled: isEditing,
  });

  // Fetch demo items
  const { data: demoItems, refetch: refetchItems } = useQuery<DemoItem[]>({
    queryKey: ['demo-items', demoId],
    queryFn: () => api.getDemoItems(demoId!),
    enabled: !!demoId,
  });

  // Fetch inventory items for search
  const { data: inventoryItems } = useQuery<Inventory[]>({
    queryKey: ['inventory-search', debouncedSearch],
    queryFn: () => api.getInventory({ search: debouncedSearch, limit: 20 }),
    enabled: debouncedSearch.length > 0 && showItemsPanel,
  });

  // Filter out already added items from search results
  const existingItemIds = new Set([
    ...(demoItems?.map(item => item.inventory_item_id) || []),
    ...Array.from(selectedItems.keys()),
  ]);
  const filteredInventory = inventoryItems?.filter(item => !existingItemIds.has(item.id)) || [];

  // Check permissions
  const canUpdate = user?.role?.permissions?.['inventory:update'] === true;

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.updateDemoRequest(demoId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-request', demoId] });
      queryClient.invalidateQueries({ queryKey: ['demo-requests'] });
      setIsEditing(false);
    },
  });

  const addItemMutation = useMutation({
    mutationFn: (data: { inventory_item_id: string; quantity: number }) => 
      api.addDemoItem(demoId!, data),
    onSuccess: () => {
      refetchItems();
      setItemError('');
    },
    onError: (error: any) => {
      setItemError(error.response?.data?.detail || 'Failed to add item');
    },
  });

  const removeItemMutation = useMutation({
    mutationFn: (itemId: string) => api.removeDemoItem(demoId!, itemId),
    onSuccess: () => {
      refetchItems();
    },
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ itemId, quantity }: { itemId: string; quantity: number }) => 
      api.updateDemoItem(demoId!, itemId, { quantity }),
    onSuccess: () => {
      refetchItems();
      setItemError('');
    },
    onError: (error: any) => {
      setItemError(error.response?.data?.detail || 'Failed to update item');
    },
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: () => api.submitDemoRequest(demoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-request', demoId] });
    },
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: () => api.approveDemoRequest(demoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-request', demoId] });
    },
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: () => api.rejectDemoRequest(demoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-request', demoId] });
    },
  });

  // Dispatch mutation
  const dispatchMutation = useMutation({
    mutationFn: () => api.dispatchDemoRequest(demoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-request', demoId] });
    },
  });

  // Receive mutation
  const receiveMutation = useMutation({
    mutationFn: () => api.receiveDemoRequest(demoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-request', demoId] });
    },
  });

  const handleEdit = () => {
    setEditData({
      number: demoRequest?.number,
      hospital_id: demoRequest?.hospital_id,
      city: demoRequest?.city,
      state: demoRequest?.state,
      notes: demoRequest?.notes,
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    updateMutation.mutate(editData);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditData({});
  };

  const handleAddToSelection = (item: Inventory) => {
    const newMap = new Map(selectedItems);
    newMap.set(item.id, { item, quantity: 1 });
    setSelectedItems(newMap);
    setItemSearch('');
    setItemError('');
  };

  const handleUpdateSelectionQuantity = (itemId: string, quantity: number) => {
    const newMap = new Map(selectedItems);
    const entry = newMap.get(itemId);
    if (entry) {
      if (quantity > entry.item.stock_quantity) {
        setItemError(`Quantity (${quantity}) exceeds available stock (${entry.item.stock_quantity}) for ${entry.item.sku}`);
        return;
      }
      if (quantity < 1) {
        newMap.delete(itemId);
      } else {
        newMap.set(itemId, { ...entry, quantity });
      }
      setSelectedItems(newMap);
      setItemError('');
    }
  };

  const handleRemoveFromSelection = (itemId: string) => {
    const newMap = new Map(selectedItems);
    newMap.delete(itemId);
    setSelectedItems(newMap);
  };

  const handleSaveItems = async () => {
    setItemError('');
    for (const [itemId, { quantity }] of selectedItems) {
      try {
        await addItemMutation.mutateAsync({ inventory_item_id: itemId, quantity });
      } catch {
        // Error is handled by mutation
        return;
      }
    }
    setSelectedItems(new Map());
  };

  const handleCloseItemsPanel = () => {
    setShowItemsPanel(false);
    setSelectedItems(new Map());
    setItemSearch('');
    setItemError('');
  };

  const getStateBadge = (state: string) => {
    const colors: Record<string, string> = {
      requested: 'bg-blue-100 text-blue-800',
      submitted: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      dispatched: 'bg-purple-100 text-purple-800',
      complete: 'bg-gray-100 text-gray-800',
    };
    return colors[state] || 'bg-gray-100 text-gray-800';
  };

  const getStateLabel = (state: string) => {
    const labels: Record<string, string> = {
      requested: 'Requested',
      submitted: 'Submitted for Approval',
      approved: 'Approved',
      dispatched: 'Dispatched',
      complete: 'Complete',
    };
    return labels[state] || state;
  };

  const isExecutive = user?.role_name === 'executive' || user?.role_name === 'admin';
  const canSubmit = canUpdate && demoRequest?.state === 'requested' && demoItems && demoItems.length > 0;
  const canApproveReject = isExecutive && demoRequest?.state === 'submitted';
  const canDispatch = canUpdate && demoRequest?.state === 'approved';
  const canReceive = canUpdate && demoRequest?.state === 'dispatched';
  const canDownloadChallan = demoRequest?.state === 'dispatched';

  const handleDownloadChallan = async () => {
    try {
      const blob = await api.downloadDemoChallan(demoId!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Demo_Challan_${demoRequest?.number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download challan:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!demoRequest) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Demo request not found</div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/demos')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft size={20} className="mr-2" />
          Back to Demo Requests
        </button>
        
        <div className="flex items-center justify-between">
          <div>
            {isEditing ? (
              <input
                type="text"
                value={editData.number || ''}
                onChange={(e) => setEditData({ ...editData, number: e.target.value })}
                className="text-3xl font-bold text-gray-900 border-b-2 border-blue-500 bg-transparent outline-none"
              />
            ) : (
              <h1 className="text-3xl font-bold text-gray-900">{demoRequest.number}</h1>
            )}
            <p className="text-gray-500 mt-1">Demo Request Details</p>
          </div>
          
          {!isEditing && (
            <div className="flex gap-2">
              {/* Edit Items - only in requested state */}
              {canUpdate && demoRequest.state === 'requested' && (
                <button
                  onClick={() => setShowItemsPanel(true)}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <Package size={16} />
                  Edit Items
                </button>
              )}
              
              {/* Submit for Approval - inventory admin, requested state, has items */}
              {canSubmit && (
                <button
                  onClick={() => submitMutation.mutate()}
                  className="btn bg-yellow-500 hover:bg-yellow-600 text-white flex items-center gap-2"
                  disabled={submitMutation.isPending}
                >
                  {submitMutation.isPending ? 'Submitting...' : 'Submit for Approval'}
                </button>
              )}
              
              {/* Approve/Reject - executive only, submitted state */}
              {canApproveReject && (
                <>
                  <button
                    onClick={() => rejectMutation.mutate()}
                    className="btn bg-red-500 hover:bg-red-600 text-white flex items-center gap-2"
                    disabled={rejectMutation.isPending || approveMutation.isPending}
                  >
                    {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
                  </button>
                  <button
                    onClick={() => approveMutation.mutate()}
                    className="btn bg-green-500 hover:bg-green-600 text-white flex items-center gap-2"
                    disabled={approveMutation.isPending || rejectMutation.isPending}
                  >
                    {approveMutation.isPending ? 'Approving...' : 'Approve'}
                  </button>
                </>
              )}
              
              {/* Dispatch - inventory admin, approved state */}
              {canDispatch && (
                <button
                  onClick={() => dispatchMutation.mutate()}
                  className="btn bg-purple-500 hover:bg-purple-600 text-white flex items-center gap-2"
                  disabled={dispatchMutation.isPending}
                >
                  {dispatchMutation.isPending ? 'Dispatching...' : 'Dispatch'}
                </button>
              )}
              
              {/* Received - inventory admin, dispatched state */}
              {canReceive && (
                <button
                  onClick={() => receiveMutation.mutate()}
                  className="btn bg-green-500 hover:bg-green-600 text-white flex items-center gap-2"
                  disabled={receiveMutation.isPending}
                >
                  {receiveMutation.isPending ? 'Processing...' : 'Received'}
                </button>
              )}
              
              {/* Download Demo Challan - only when dispatched or complete */}
              {canDownloadChallan && (
                <button
                  onClick={handleDownloadChallan}
                  className="btn bg-purple-500 hover:bg-purple-600 text-white flex items-center gap-2"
                >
                  <Download size={16} />
                  Download Demo Challan
                </button>
              )}
              
              {/* Edit - only in requested state */}
              {canUpdate && demoRequest.state === 'requested' && (
                <button
                  onClick={handleEdit}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <Edit size={16} />
                  Edit
                </button>
              )}
            </div>
          )}
          
          {isEditing && (
            <div className="flex gap-2">
              <button
                onClick={handleCancel}
                className="btn btn-secondary flex items-center gap-2"
                disabled={updateMutation.isPending}
              >
                <X size={16} />
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="btn btn-primary flex items-center gap-2"
                disabled={updateMutation.isPending}
              >
                <Save size={16} />
                {updateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Hospital Information */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Building2 size={20} className="text-blue-600" />
              <h2 className="text-xl font-semibold">Hospital Information</h2>
            </div>
            
            {isEditing ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hospital
                  </label>
                  <select
                    value={editData.hospital_id}
                    onChange={(e) => setEditData({ ...editData, hospital_id: e.target.value })}
                    className="input w-full"
                  >
                    <option value="">Select Hospital</option>
                    {customers?.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.hospital_name} - {c.city || 'N/A'}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ) : demoRequest.hospital ? (
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-500">Hospital Name</p>
                  <p className="text-lg font-medium">{demoRequest.hospital.hospital_name}</p>
                </div>
                {demoRequest.hospital.contact_person && (
                  <div>
                    <p className="text-sm text-gray-500">Contact Person</p>
                    <p className="text-base">{demoRequest.hospital.contact_person}</p>
                  </div>
                )}
                {demoRequest.hospital.phone && (
                  <div>
                    <p className="text-sm text-gray-500">Phone</p>
                    <p className="text-base">{demoRequest.hospital.phone}</p>
                  </div>
                )}
                {demoRequest.hospital.state && (
                  <div>
                    <p className="text-sm text-gray-500">Hospital Location</p>
                    <p className="text-base">
                      {demoRequest.hospital.city && `${demoRequest.hospital.city}, `}
                      {demoRequest.hospital.state}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 italic">No hospital selected</p>
            )}
          </div>

          {/* Demo Location */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <MapPin size={20} className="text-green-600" />
              <h2 className="text-xl font-semibold">Demo Location</h2>
            </div>
            
            {isEditing ? (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  City
                </label>
                <input
                  type="text"
                  value={editData.city}
                  onChange={(e) => setEditData({ ...editData, city: e.target.value })}
                  className="input w-full"
                  placeholder="Enter city"
                />
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-500">City</p>
                <p className="text-lg font-medium">
                  {demoRequest.city ? (
                    demoRequest.city
                  ) : (
                    <span className="text-gray-400 italic">Not specified</span>
                  )}
                </p>
              </div>
            )}
          </div>

          {/* Notes */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <FileText size={20} className="text-purple-600" />
              <h2 className="text-xl font-semibold">Notes</h2>
            </div>
            
            {isEditing ? (
              <textarea
                value={editData.notes || ''}
                onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                className="input w-full"
                rows={4}
                placeholder="Additional notes..."
              />
            ) : (
              <p className="text-gray-700 whitespace-pre-wrap">
                {demoRequest.notes || 'No notes provided'}
              </p>
            )}
          </div>
        </div>

        {/* Right Column - Demo Items (top), Status & Metadata */}
        <div className="space-y-6">
          {/* Demo Items - Most Important, at top */}
          <div className="card border border-orange-200">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Package size={18} className="text-orange-500" />
                <h3 className="font-semibold text-gray-900">
                  Demo Items {demoItems && demoItems.length > 0 && `(${demoItems.length})`}
                </h3>
              </div>
              {demoRequest.state === 'requested' && canUpdate && (
                <button
                  onClick={() => setShowItemsPanel(true)}
                  className="text-orange-600 hover:text-orange-700 text-sm font-medium flex items-center gap-1"
                >
                  <Plus size={14} />
                  Add
                </button>
              )}
            </div>
            
            {demoItems && demoItems.length > 0 ? (
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {demoItems.map((item) => (
                  <div key={item.id} className="flex items-center justify-between py-2 px-2.5 bg-gray-50 rounded">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{item.inventory_item.sku}</p>
                      <p className="text-xs text-gray-400 truncate">{item.inventory_item.description}</p>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      <span className="text-sm font-medium text-gray-700">×{item.quantity}</span>
                      {demoRequest.state === 'requested' && canUpdate && (
                        <button
                          onClick={() => removeItemMutation.mutate(item.id)}
                          className="text-gray-400 hover:text-red-500 p-0.5"
                          disabled={removeItemMutation.isPending}
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm py-2">No items added</p>
            )}
          </div>

          {/* Status */}
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Status</h3>
            
            {isEditing ? (
              <select
                value={editData.state}
                onChange={(e) => setEditData({ ...editData, state: e.target.value })}
                className="input w-full"
              >
                <option value="requested">Requested</option>
                <option value="submitted">Submitted for Approval</option>
                <option value="approved">Approved</option>
                <option value="dispatched">Dispatched</option>
                <option value="complete">Complete</option>
              </select>
            ) : (
              <span className={`inline-block px-3 py-1 text-sm font-medium rounded-full ${getStateBadge(demoRequest.state)}`}>
                {getStateLabel(demoRequest.state)}
              </span>
            )}
          </div>

          {/* Created By */}
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <User size={18} className="text-gray-500" />
              <h3 className="text-sm font-medium text-gray-500">Created By</h3>
            </div>
            <div>
              <p className="font-medium">{demoRequest.creator.full_name}</p>
              <p className="text-sm text-gray-500">{demoRequest.creator.email}</p>
            </div>
          </div>

          {/* Timestamps */}
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <Calendar size={18} className="text-gray-500" />
              <h3 className="text-sm font-medium text-gray-500">Timeline</h3>
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-gray-500">Created</p>
                <p className="text-sm">
                  {new Date(demoRequest.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Last Updated</p>
                <p className="text-sm">
                  {new Date(demoRequest.updated_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Items Side Panel */}
      {showItemsPanel && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-30"
            onClick={handleCloseItemsPanel}
          />
          
          {/* Panel */}
          <div className="fixed right-0 top-0 h-full w-1/2 bg-white shadow-xl flex flex-col">
            {/* Panel Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold">Add Demo Items</h2>
              <button
                onClick={handleCloseItemsPanel}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            {/* Search */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="text"
                  value={itemSearch}
                  onChange={(e) => setItemSearch(e.target.value)}
                  placeholder="Search by catalog number..."
                  className="input w-full pl-10"
                  autoFocus
                />
              </div>
              
              {/* Search Results */}
              {itemSearch && filteredInventory.length > 0 && (
                <div className="mt-2 max-h-48 overflow-y-auto border border-gray-200 rounded-lg bg-white shadow-lg">
                  {filteredInventory.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleAddToSelection(item)}
                      className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium">{item.sku}</p>
                          <p className="text-sm text-gray-500 line-clamp-1">{item.description}</p>
                        </div>
                        <span className="text-sm text-gray-500">Stock: {item.stock_quantity}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              
              {itemSearch && debouncedSearch && filteredInventory.length === 0 && (
                <p className="mt-2 text-sm text-gray-500">No items found matching "{debouncedSearch}"</p>
              )}
            </div>

            {/* Error Display */}
            {itemError && (
              <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">{itemError}</p>
              </div>
            )}

            {/* Selected Items */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <h3 className="text-sm font-medium text-gray-500 mb-3">
                Selected Items ({selectedItems.size})
              </h3>
              
              {selectedItems.size > 0 ? (
                <div className="space-y-3">
                  {Array.from(selectedItems.entries()).map(([itemId, { item, quantity }]) => (
                    <div key={itemId} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{item.sku}</p>
                        <p className="text-sm text-gray-500 truncate">{item.description}</p>
                        <p className="text-xs text-gray-400">Available: {item.stock_quantity}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <button
                          onClick={() => handleUpdateSelectionQuantity(itemId, quantity - 1)}
                          className="p-1 rounded bg-gray-200 hover:bg-gray-300"
                        >
                          <Minus size={14} />
                        </button>
                        <input
                          type="number"
                          value={quantity}
                          onChange={(e) => handleUpdateSelectionQuantity(itemId, parseInt(e.target.value) || 1)}
                          className="w-16 text-center input input-sm"
                          min={1}
                          max={item.stock_quantity}
                        />
                        <button
                          onClick={() => handleUpdateSelectionQuantity(itemId, quantity + 1)}
                          className="p-1 rounded bg-gray-200 hover:bg-gray-300"
                          disabled={quantity >= item.stock_quantity}
                        >
                          <Plus size={14} />
                        </button>
                        <button
                          onClick={() => handleRemoveFromSelection(itemId)}
                          className="p-1 text-red-600 hover:text-red-800 ml-2"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 italic">Search and select items to add</p>
              )}

              {/* Existing Items */}
              {demoItems && demoItems.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-3">
                    Already Added ({demoItems.length})
                  </h3>
                  <div className="space-y-2">
                    {demoItems.map((item) => (
                      <div key={item.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{item.inventory_item.sku}</p>
                          <p className="text-sm text-gray-500 truncate">{item.inventory_item.description}</p>
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <span className="text-sm font-medium">Qty: {item.quantity}</span>
                          <button
                            onClick={() => removeItemMutation.mutate(item.id)}
                            className="p-1 text-red-600 hover:text-red-800"
                            disabled={removeItemMutation.isPending}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Panel Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
              <div className="flex gap-3">
                <button
                  onClick={handleCloseItemsPanel}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveItems}
                  className="btn btn-primary flex-1"
                  disabled={selectedItems.size === 0 || addItemMutation.isPending}
                >
                  {addItemMutation.isPending ? 'Adding...' : `Add ${selectedItems.size} Item${selectedItems.size !== 1 ? 's' : ''}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
