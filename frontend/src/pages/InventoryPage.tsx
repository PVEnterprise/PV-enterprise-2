/**
 * Inventory page for managing stock.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Inventory } from '@/types';
import { Plus, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column, commonActions } from '@/components/common/DataTable';

export default function InventoryPage() {
  const [search, setSearch] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<Inventory | null>(null);
  const [formError, setFormError] = useState<string>('');
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: inventory, isLoading } = useQuery<Inventory[]>({
    queryKey: ['inventory', search, lowStockOnly],
    queryFn: () => api.getInventory({ search, low_stock: lowStockOnly }),
  });

  // Check permissions
  const canCreate = user?.role?.permissions?.['inventory:create'] === true;
  const canUpdate = user?.role?.permissions?.['inventory:update'] === true;
  const canDelete = user?.role?.permissions?.['inventory:delete'] === true;

  const inventoryFields: FormField[] = [
    {
      name: 'sku',
      label: 'Catalog No',
      type: 'text',
      required: true,
      placeholder: 'Enter unique catalog number',
    },
    {
      name: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Enter item description',
    },
    {
      name: 'batch_no',
      label: 'Batch No',
      type: 'text',
      placeholder: 'Enter batch number',
    },
    {
      name: 'unit_price',
      label: 'Unit Price (₹)',
      type: 'number',
      required: true,
      validation: {
        min: 0,
      },
    },
    {
      name: 'stock_quantity',
      label: 'Stock Quantity',
      type: 'number',
      required: true,
      validation: {
        min: 0,
      },
      defaultValue: 0,
    },
    {
      name: 'hsn_code',
      label: 'HSN Code',
      type: 'text',
      required: true,
      placeholder: 'Enter 8-digit HSN code',
      validation: {
        pattern: /^[0-9]{8}$/,
        message: 'HSN code must be exactly 8 digits',
      },
    },
    {
      name: 'tax',
      label: 'Tax (%)',
      type: 'number',
      required: true,
      placeholder: 'Enter tax percentage',
      validation: {
        min: 0,
        max: 100,
      },
    },
  ];

  // Mutations
  const createMutation = useMutation({
    mutationFn: api.createInventoryItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      setShowForm(false);
      setEditingItem(null);
      setFormError('');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create item';
      setFormError(errorMessage);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.updateInventoryItem(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      setShowForm(false);
      setEditingItem(null);
      setFormError('');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to update item';
      setFormError(errorMessage);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteInventoryItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });

  const handleSubmit = async (data: Record<string, any>) => {
    if (editingItem) {
      await updateMutation.mutateAsync({ id: editingItem.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleEdit = (item: Inventory) => {
    setEditingItem(item);
    setShowForm(true);
    setFormError(''); // Clear any previous errors
  };

  const handleDelete = (item: Inventory) => {
    if (confirm(`Are you sure you want to delete ${item.sku}${item.description ? ` - ${item.description}` : ''}?`)) {
      deleteMutation.mutate(item.id);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingItem(null);
    setFormError(''); // Clear errors when closing
  };
  
  const handleAddNew = () => {
    setShowForm(true);
    setEditingItem(null);
    setFormError(''); // Clear any previous errors
  };

  // Define columns
  const columns: Column<Inventory>[] = [
    {
      key: 'sku',
      label: 'Catalog No',
      width: '8%',
    },
    {
      key: 'description',
      label: 'Description',
      width: '29%',
      render: (value) => (
        <div className="break-words whitespace-normal line-clamp-2">
          {value || '-'}
        </div>
      ),
    },
    {
      key: 'batch_no',
      label: 'Batch No',
      width: '10%',
      render: (value) => value || '-',
    },
    {
      key: 'hsn_code',
      label: 'HSN Code',
      width: '9%',
    },
    {
      key: 'stock_quantity',
      label: 'Stock',
      width: '8%',
      render: (value: number) => (
        <span className="text-gray-900">{value}</span>
      ),
    },
    {
      key: 'unit_price',
      label: 'Unit Price',
      width: '10%',
      render: (value: number) => `₹${value.toLocaleString()}`,
    },
    {
      key: 'tax',
      label: 'Tax',
      width: '2%',
      render: (value: number) => `${value}%`,
    },
  ];

  return (
    <div>
      {/* Compact Header - Single Line */}
      <div className="flex items-center justify-between mb-4 bg-white p-4 rounded-lg shadow-sm">
        <div className="flex items-center space-x-4 flex-1">
          <h1 className="text-xl font-bold text-gray-900">Inventory</h1>
          
          {/* Search */}
          <div className="flex-1 relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder="Search catalog no, description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input input-sm pl-9 w-full"
            />
          </div>
          
          {/* Low Stock Filter */}
          <label className="flex items-center space-x-2 whitespace-nowrap">
            <input
              type="checkbox"
              checked={lowStockOnly}
              onChange={(e) => setLowStockOnly(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm font-medium text-gray-700">Low Stock</span>
          </label>
        </div>
        
        {/* Add Button - Always Right */}
        {canCreate && (
          <button 
            onClick={handleAddNew}
            className="btn btn-primary btn-sm flex items-center whitespace-nowrap ml-4"
          >
            <Plus size={16} className="mr-1" />
            Add Item
          </button>
        )}
      </div>

      {/* Scrollable Table Container */}
      <div className="overflow-auto max-h-[calc(100vh-200px)]">
        <DataTable
          data={inventory || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No inventory items found. Add your first item to get started."
          showAuditInfo={false}
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
          title="Inventory Item"
          fields={inventoryFields}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          submitLabel={editingItem ? 'Update Item' : 'Add Item'}
          initialData={editingItem || {}}
          isEdit={!!editingItem}
          isLoading={createMutation.isPending || updateMutation.isPending}
          error={formError}
        />
      )}
    </div>
  );
}
