/**
 * Orders page for managing orders.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Order } from '@/types';
import { Plus } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column } from '@/components/common/DataTable';
import { useNavigate } from 'react-router-dom';

export default function OrdersPage() {
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [showForm, setShowForm] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: orders, isLoading } = useQuery<Order[]>({
    queryKey: ['orders', selectedStatus],
    queryFn: () => api.getOrders({ status: selectedStatus || undefined }),
  });

  // Check if user has permission to create orders
  const canCreateOrder = user?.role?.permissions?.['order:create'] === true;

  // Fetch customers based on search term
  const fetchCustomers = async (searchTerm: string) => {
    try {
      const customers = await api.getCustomers({ search: searchTerm });
      return customers.map((c: any) => ({
        value: c.id,
        label: c.hospital_name,
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

  const handleSubmit = async (data: Record<string, any>) => {
    // Transform form data to match backend schema
    // Sales describes requirements in words, decoder will map to inventory items later
    const orderData = {
      customer_id: data.customer_id,
      priority: data.priority,
      notes: data.notes,
      items: [
        {
          item_description: data.requirements,
          quantity: 1, // Placeholder - decoder will create actual items with quantities
          notes: 'Pending decoder review - items need to be mapped to inventory',
        },
      ],
    };
    await createMutation.mutateAsync(orderData);
  };

  const columns: Column<Order>[] = [
    {
      key: 'order_number',
      label: 'Order #',
      width: '15%',
      render: (value: string, row: Order) => (
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
      ),
    },
    {
      key: 'customer.name',
      label: 'Customer Name',
      width: '25%',
      render: (value: any, row: Order) => row.customer?.name || row.customer?.hospital_name || '-',
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
              onChange={(e) => setSelectedStatus(e.target.value)}
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
      <div className="overflow-auto max-h-[calc(100vh-200px)]">
        <DataTable
          data={orders || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No orders found. Create your first order to get started."
          showAuditInfo={true}
          onRowClick={handleRowClick}
        />
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
    </div>
  );
}
