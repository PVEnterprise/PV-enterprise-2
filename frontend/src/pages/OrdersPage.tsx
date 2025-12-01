/**
 * Orders page for managing orders.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Order } from '@/types';
import { Plus, Edit2, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column } from '@/components/common/DataTable';
import { useNavigate } from 'react-router-dom';

export default function OrdersPage() {
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [showForm, setShowForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [newOrderNumber, setNewOrderNumber] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(100); // Match backend default
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: orders, isLoading } = useQuery<Order[]>({
    queryKey: ['orders', selectedStatus, currentPage],
    queryFn: () => api.getOrders({ 
      status: selectedStatus || undefined,
      skip: (currentPage - 1) * itemsPerPage,
      limit: itemsPerPage,
    }),
  });

  // Reset to page 1 when status filter changes
  const handleStatusChange = (newStatus: string) => {
    setSelectedStatus(newStatus);
    setCurrentPage(1);
  };

  // Check if user has permission to create orders
  const canCreateOrder = user?.role?.permissions?.['order:create'] === true;

  // Fetch customers based on search term
  const fetchCustomers = async (searchTerm: string) => {
    try {
      const customers = await api.getCustomers({ search: searchTerm });
      return customers.map((c: any) => ({
        value: c.id,
        label: c.hospital_name,
        subtitle: c.address || undefined,
      }));
    } catch (error) {
      console.error('Error fetching customers:', error);
      return [];
    }
  };

  // Generate fields dynamically
  const getOrderFields = (): FormField[] => [
    {
      name: 'customer_id',
      label: 'Customer',
      type: 'autocomplete',
      required: true,
      fetchOptions: fetchCustomers,
      placeholder: 'Search customer...',
    },
    {
      name: 'requirements',
      label: 'Requirements',
      type: 'textarea',
      required: true,
      placeholder: 'Describe all items needed in detail:\n\nExample:\n- 100 boxes of surgical gloves (size M)\n- 2 units of X-ray machines\n- 50 pieces of surgical masks\n\nThe decoder will map these to inventory items later.',
    },
    {
      name: 'priority',
      label: 'Priority',
      type: 'select',
      required: true,
      options: [
        { value: 'low', label: 'Low' },
        { value: 'medium', label: 'Medium' },
        { value: 'high', label: 'High' },
        { value: 'urgent', label: 'Urgent' },
      ],
      defaultValue: 'medium',
    },
    {
      name: 'notes',
      label: 'Additional Notes',
      type: 'textarea',
      placeholder: 'Any special requirements, delivery instructions, or other notes...',
    },
    {
      name: 'attachments',
      label: 'Attachments',
      type: 'file',
      multiple: true,
      accept: '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png',
      placeholder: 'Upload supporting documents (PDF, Word, Excel, Images)',
    },
  ];

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: api.createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setShowForm(false);
    },
    onError: (error: any) => {
      alert(`Error creating order: ${error.message || 'Unknown error'}`);
    },
  });

  // Update order number mutation
  const updateOrderNumberMutation = useMutation({
    mutationFn: ({ orderId, newOrderNumber }: { orderId: string; newOrderNumber: string }) =>
      api.updateOrderNumber(orderId, newOrderNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setEditingOrder(null);
      setNewOrderNumber('');
    },
    onError: (error: any) => {
      alert(`Error updating order number: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    },
  });

  // Check if user can edit order numbers (quoter or executive)
  const canEditOrderNumber = user?.role_name === 'quoter' || user?.role_name === 'executive';

  const handleEditOrderNumber = (order: Order, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent row click
    setEditingOrder(order);
    setNewOrderNumber(order.order_number);
  };

  const handleSaveOrderNumber = () => {
    if (!editingOrder || !newOrderNumber.trim()) {
      alert('Order number cannot be empty');
      return;
    }
    updateOrderNumberMutation.mutate({
      orderId: editingOrder.id,
      newOrderNumber: newOrderNumber.trim(),
    });
  };

  const handleCancelEdit = () => {
    setEditingOrder(null);
    setNewOrderNumber('');
  };

  const handleSubmit = async (data: Record<string, any>) => {
    try {
      console.log('Form data received:', data);
      console.log('Attachments:', data.attachments);
      console.log('Attachments type:', typeof data.attachments);
      console.log('Attachments length:', data.attachments?.length);
      
      // Transform form data to match backend schema
      // Sales describes requirements in words, decoder will create items later
      const orderData = {
        customer_id: data.customer_id,
        priority: data.priority,
        sales_rep_description: data.requirements, // Store requirements at order level
        notes: data.notes,
      };
      
      // Create the order first
      const newOrder = await createMutation.mutateAsync(orderData);
      
      console.log('Order created:', newOrder);
      console.log('Checking attachments...');
      
      // Upload attachments if any
      if (data.attachments && data.attachments.length > 0) {
        console.log('Attachments found, starting upload...');
        // data.attachments is already an array of File objects
        for (const file of data.attachments) {
          console.log('Uploading file:', file);
          console.log('File type:', file instanceof File);
          console.log('File name:', file.name);
          console.log('File size:', file.size, 'bytes');
          console.log('File last modified:', file.lastModified);
          
          if (file.size === 0 || file.size < 10) {
            console.error('ERROR: File is empty or too small!', file);
            alert(`File "${file.name}" appears to be empty or corrupted (${file.size} bytes). Please select a valid file.`);
            continue; // Skip this file
          }
          
          const formData = new FormData();
          formData.append('file', file);
          formData.append('description', file.name);
          
          // Debug: Log FormData contents
          for (let pair of formData.entries()) {
            console.log(pair[0], pair[1]);
            if (pair[1] instanceof File) {
              console.log('  -> File size in FormData:', pair[1].size);
            }
          }
          
          await api.uploadAttachment('order', newOrder.id, formData);
        }
      }
      
      // Refresh and close
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setShowForm(false);
    } catch (error: any) {
      console.error('Error creating order:', error);
      alert(`Error creating order: ${error.message || 'Unknown error'}`);
    }
  };

  const columns: Column<Order>[] = [
    {
      key: 'order_number',
      label: 'Order #',
      width: '20%',
      render: (value: string, row: Order) => (
        <div className="flex items-center gap-2">
          <a
            href={`/orders/${row.id}`}
            onClick={(e) => {
              e.preventDefault();
              window.location.href = `/orders/${row.id}`;
            }}
            className="text-primary-600 hover:text-primary-800 font-medium hover:underline"
          >
            {value}
          </a>
          {canEditOrderNumber && (
            <button
              onClick={(e) => handleEditOrderNumber(row, e)}
              className="p-1 hover:bg-gray-100 rounded transition-colors"
              title="Edit order number"
            >
              <Edit2 size={14} className="text-gray-600 hover:text-primary-600" />
            </button>
          )}
        </div>
      ),
    },
    {
      key: 'customer.name',
      label: 'Customer Name',
      width: '25%',
      render: (_value: any, row: Order) => row.customer?.name || row.customer?.hospital_name || '-',
    },
    {
      key: 'status',
      label: 'Status',
      width: '15%',
      render: (value: string) => (
        <span className={`badge ${
          value === 'draft' ? 'badge-info' :
          value === 'pending_approval' ? 'badge-warning' :
          value === 'approved' ? 'badge-success' :
          value === 'completed' ? 'badge-success' :
          value === 'cancelled' ? 'badge-danger' : 'badge-info'
        }`}>
          {value.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'priority',
      label: 'Priority',
      width: '15%',
      render: (value: string) => (
        <span className={`badge ${
          value === 'low' ? 'badge-info' :
          value === 'medium' ? 'badge-warning' :
          value === 'high' || value === 'urgent' ? 'badge-danger' : 'badge-info'
        }`}>
          {value}
        </span>
      ),
    },
    {
      key: 'workflow_stage',
      label: 'Stage',
      width: '15%',
      render: (value: string) => value?.replace('_', ' ') || '-',
    },
    {
      key: 'created_at',
      label: 'Date',
      width: '15%',
      render: (value: string) => new Date(value).toLocaleDateString(),
    },
  ];

  const handleRowClick = (order: Order) => {
    navigate(`/orders/${order.id}`);
  };

  return (
    <div>
      {/* Compact Header - Single Line */}
      <div className="flex items-center justify-between mb-4 bg-white p-4 rounded-lg shadow-sm">
        <div className="flex items-center space-x-4 flex-1">
          <h1 className="text-xl font-bold text-gray-900">Orders</h1>
          
          {/* Filter */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Status:</label>
            <select
              value={selectedStatus}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="input input-sm"
            >
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="pending_approval">Pending Approval</option>
              <option value="approved">Approved</option>
              <option value="completed">Completed</option>
            </select>
          </div>
        </div>
        
        {/* New Button - Always Right */}
        {canCreateOrder && (
          <button 
            onClick={() => setShowForm(true)}
            className="btn btn-primary btn-sm flex items-center whitespace-nowrap ml-4"
          >
            <Plus size={16} className="mr-1" />
            New Order
          </button>
        )}
      </div>

      {/* Scrollable Table Container */}
      <div className="overflow-auto max-h-[calc(100vh-260px)]">
        <DataTable
          data={orders || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No orders found. Create your first order to get started."
          showAuditInfo={true}
          onRowClick={handleRowClick}
        />
      </div>

      {/* Pagination Controls */}
      <div className="bg-white p-4 rounded-lg shadow-sm mt-4 flex items-center justify-between">
        <div className="text-sm text-gray-600">
          Page {currentPage} • Showing {orders?.length || 0} orders
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1 || isLoading}
            className="btn btn-secondary btn-sm flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} className="mr-1" />
            Previous
          </button>
          <button
            onClick={() => setCurrentPage(prev => prev + 1)}
            disabled={!orders || orders.length < itemsPerPage || isLoading}
            className="btn btn-secondary btn-sm flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight size={16} className="ml-1" />
          </button>
        </div>
      </div>

      {showForm && (
        <DynamicForm
          title="Order"
          fields={getOrderFields()}
          onSubmit={handleSubmit}
          onCancel={() => setShowForm(false)}
          submitLabel="Create Order"
          isLoading={createMutation.isPending}
        />
      )}

      {/* Edit Order Number Modal */}
      {editingOrder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Edit Order Number</h2>
              <button
                onClick={handleCancelEdit}
                className="text-gray-400 hover:text-gray-600"
                disabled={updateOrderNumberMutation.isPending}
              >
                <X size={24} />
              </button>
            </div>
            <div className="px-6 py-4">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Current Order Number
                </label>
                <p className="text-gray-600 font-mono bg-gray-50 p-2 rounded">
                  {editingOrder.order_number}
                </p>
              </div>
              <div>
                <label htmlFor="newOrderNumber" className="block text-sm font-medium text-gray-700 mb-2">
                  New Order Number <span className="text-red-500">*</span>
                </label>
                <input
                  id="newOrderNumber"
                  type="text"
                  value={newOrderNumber}
                  onChange={(e) => setNewOrderNumber(e.target.value)}
                  className="input w-full"
                  placeholder="Enter new order number"
                  disabled={updateOrderNumberMutation.isPending}
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1">
                  This will update the order number in the database and audit trail.
                </p>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end space-x-3">
              <button
                onClick={handleCancelEdit}
                className="btn btn-secondary"
                disabled={updateOrderNumberMutation.isPending}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveOrderNumber}
                className="btn btn-primary flex items-center"
                disabled={updateOrderNumberMutation.isPending || !newOrderNumber.trim()}
              >
                {updateOrderNumberMutation.isPending ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Updating...
                  </>
                ) : (
                  'Update Order Number'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
