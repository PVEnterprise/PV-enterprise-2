/**
 * Customers page for managing hospital clients.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Customer } from '@/types';
import { Plus } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column, commonActions } from '@/components/common/DataTable';

const customerFields: FormField[] = [
  {
    name: 'hospital_name',
    label: 'Hospital Name',
    type: 'text',
    required: true,
    placeholder: 'Enter hospital name',
  },
  {
    name: 'contact_person',
    label: 'Contact Person',
    type: 'text',
    required: true,
    placeholder: 'Enter contact person name',
  },
  {
    name: 'email',
    label: 'Email',
    type: 'email',
    required: true,
    placeholder: 'contact@hospital.com',
    validation: {
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      message: 'Please enter a valid email address',
    },
  },
  {
    name: 'phone',
    label: 'Phone',
    type: 'text',
    required: true,
    placeholder: '1234567890',
    validation: {
      pattern: /^\d{10}$/,
      message: 'Phone must be 10 digits',
    },
  },
  {
    name: 'address',
    label: 'Address',
    type: 'textarea',
    placeholder: 'Enter complete address',
  },
  {
    name: 'city',
    label: 'City',
    type: 'text',
    required: true,
    placeholder: 'Enter city',
  },
  {
    name: 'state',
    label: 'State',
    type: 'text',
    required: true,
    placeholder: 'Enter state',
  },
  {
    name: 'pincode',
    label: 'Pincode',
    type: 'text',
    placeholder: 'Enter pincode',
    validation: {
      pattern: /^\d{6}$/,
      message: 'Pincode must be 6 digits',
    },
  },
  {
    name: 'gst_number',
    label: 'GST Number',
    type: 'text',
    placeholder: 'Enter GST number (optional)',
  },
];

const columns: Column<Customer>[] = [
  {
    key: 'name',
    label: 'Customer Name',
    width: '20%',
  },
  {
    key: 'hospital_name',
    label: 'Hospital Name',
    width: '20%',
  },
  {
    key: 'contact_person',
    label: 'Contact Person',
    width: '15%',
  },
  {
    key: 'email',
    label: 'Email',
    width: '15%',
  },
  {
    key: 'phone',
    label: 'Phone',
    width: '12%',
  },
  {
    key: 'city',
    label: 'City',
    width: '10%',
  },
];

export default function CustomersPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: customers, isLoading } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: () => api.getCustomers({}),
  });

  const createMutation = useMutation({
    mutationFn: api.createCustomer,
    onSuccess: () => {
      queryClient.invalidateQueries(['customers']);
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.updateCustomer(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['customers']);
      setShowForm(false);
      setEditingCustomer(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteCustomer,
    onSuccess: () => {
      queryClient.invalidateQueries(['customers']);
    },
  });

  const canCreate = user?.role?.permissions?.['customer:create'] === true;
  const canUpdate = user?.role?.permissions?.['customer:update'] === true;
  const canDelete = user?.role?.permissions?.['customer:delete'] === true;

  const handleSubmit = async (data: Record<string, any>) => {
    if (editingCustomer) {
      await updateMutation.mutateAsync({ id: editingCustomer.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleEdit = (customer: Customer) => {
    setEditingCustomer(customer);
    setShowForm(true);
  };

  const handleDelete = (customer: Customer) => {
    if (confirm(`Are you sure you want to delete ${customer.hospital_name}?`)) {
      deleteMutation.mutate(customer.id);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingCustomer(null);
  };

  return (
    <div className="w-full">
      {/* Compact Header - Single Line */}
      <div className="flex items-center justify-between mb-4 bg-white p-4 rounded-lg shadow-sm">
        <h1 className="text-xl font-bold text-gray-900">Customers</h1>
        
        {/* Add Button - Always Right */}
        {canCreate && (
          <button 
            onClick={() => setShowForm(true)}
            className="btn btn-primary btn-sm flex items-center whitespace-nowrap ml-4"
          >
            <Plus size={16} className="mr-1" />
            Add Customer
          </button>
        )}
      </div>

      {/* Scrollable Table Container - Full Width */}
      <div className="w-full overflow-auto max-h-[calc(100vh-200px)]">
        <DataTable
          data={customers || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No customers found. Add your first customer to get started."
          showAuditInfo={true}
          actions={[
            commonActions.edit(
              handleEdit,
              () => canUpdate
            ),
            commonActions.delete(
              handleDelete,
              () => canDelete
            ),
          ]}
        />
      </div>

      {showForm && (
        <DynamicForm
          title="Customer"
          fields={customerFields}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          submitLabel={editingCustomer ? 'Update Customer' : 'Create Customer'}
          initialData={editingCustomer || {}}
          isEdit={!!editingCustomer}
          isLoading={createMutation.isLoading || updateMutation.isLoading}
        />
      )}
    </div>
  );
}
