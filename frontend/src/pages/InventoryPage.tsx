/**
 * Inventory page for managing stock.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Inventory } from '@/types';
import { Plus, Search, Upload, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column, commonActions } from '@/components/common/DataTable';

export default function InventoryPage() {
  const [search, setSearch] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<Inventory | null>(null);
  const [formError, setFormError] = useState<string>('');
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: inventory, isLoading } = useQuery<Inventory[]>({
    queryKey: ['inventory', search, lowStockOnly],
    queryFn: () => api.getInventory({ search, low_stock: lowStockOnly, limit: 10000 }),
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

  const handleImportExcel = async () => {
    if (!importFile) return;

    try {
      // Dynamically import xlsx library
      const XLSX = await import('xlsx');
      
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const data = e.target?.result;
          const workbook = XLSX.read(data, { type: 'binary' });
          const sheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[sheetName];
          
          // Read with defval to handle empty cells
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
            defval: null,
            raw: false // Convert all values to strings first
          }) as any[];

          console.log('Total rows read:', jsonData.length);
          console.log('First row keys:', Object.keys(jsonData[0] || {}));
          console.log('First 3 rows from Excel:', jsonData.slice(0, 3));

          let successCount = 0;
          let errors: string[] = [];
          let skippedCount = 0;

          // Process each row
          for (const row of jsonData) {
            const sku = row['Catalog No'] || row['SKU'] || row['sku'];
            const description = row['Description'] || row['description'];
            const batchNo = row['Batch No'] || row['Batch no'] || row['batch_no'];
            const unitPrice = row['Unit Price'] || row['unit_price'] || row['Price'];
            const stockQuantity = row['Stock Quantity'] || row['stock_quantity'] || row['Stock'];
            const hsnCode = row['HSN Code'] || row['hsn_code'] || row['HSN'];
            const tax = row['Tax %'] || row['Tax'] || row['tax'];
            
            console.log('Processing row:', { sku, description, unitPrice, stockQuantity, hsnCode, tax });

            // Skip completely empty rows
            if (!sku && !description && !unitPrice && !hsnCode && tax === undefined) {
              skippedCount++;
              continue;
            }

            if (!sku || !unitPrice || !hsnCode || tax === undefined) {
              if (errors.length < 10) { // Only show first 10 detailed errors
                errors.push(`Row with SKU "${sku || 'N/A'}": Missing ${!sku ? 'Catalog No' : !unitPrice ? 'Unit Price' : !hsnCode ? 'HSN Code' : 'Tax %'}`);
              }
              skippedCount++;
              continue;
            }

            // Validate HSN code
            const hsnStr = String(hsnCode).padStart(8, '0');
            if (!/^[0-9]{8}$/.test(hsnStr)) {
              errors.push(`Invalid HSN code for ${sku}: ${hsnCode}`);
              continue;
            }

            // Validate tax
            const taxNum = parseFloat(tax);
            if (isNaN(taxNum) || taxNum < 0 || taxNum > 100) {
              errors.push(`Invalid tax for ${sku}: ${tax}`);
              continue;
            }

            try {
              await api.createInventoryItem({
                sku: String(sku),
                description: description ? String(description) : undefined,
                batch_no: batchNo ? String(batchNo) : undefined,
                unit_price: parseFloat(unitPrice),
                stock_quantity: stockQuantity ? parseInt(stockQuantity) : 0,
                hsn_code: hsnStr,
                tax: taxNum,
              });
              successCount++;
            } catch (error: any) {
              const errorMsg = error.response?.data?.detail || error.message;
              errors.push(`Failed to import ${sku}: ${errorMsg}`);
            }
          }

          // Refresh the inventory list
          queryClient.invalidateQueries({ queryKey: ['inventory'] });

          // Show results
          let message = `Successfully imported ${successCount} item(s).`;
          if (skippedCount > 0) {
            message += `\nSkipped ${skippedCount} row(s) (empty or missing required fields).`;
          }
          if (errors.length > 0) {
            message += `\n\nErrors:\n${errors.slice(0, 10).join('\n')}`;
            if (errors.length > 10) {
              message += `\n... and ${errors.length - 10} more`;
            }
          }
          alert(message);

          setShowImportModal(false);
          setImportFile(null);
        } catch (error) {
          console.error('Error processing Excel file:', error);
          alert('Error processing Excel file. Please check the format and try again.');
        }
      };

      reader.readAsBinaryString(importFile);
    } catch (error) {
      console.error('Error importing Excel:', error);
      alert('Error importing Excel file. Please make sure the file is valid.');
    }
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
        
        {/* Action Buttons - Always Right */}
        {canCreate && (
          <div className="flex items-center space-x-2 ml-4">
            <button 
              onClick={() => setShowImportModal(true)}
              className="btn btn-secondary btn-sm flex items-center whitespace-nowrap"
            >
              <Upload size={16} className="mr-1" />
              Import Excel
            </button>
            <button 
              onClick={handleAddNew}
              className="btn btn-primary btn-sm flex items-center whitespace-nowrap"
            >
              <Plus size={16} className="mr-1" />
              Add Item
            </button>
          </div>
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

      {/* Import from Excel Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">Import Inventory from Excel</h2>
              <button
                onClick={() => {
                  setShowImportModal(false);
                  setImportFile(null);
                }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <p className="text-sm text-gray-700 mb-3">
                  Upload an Excel file with the following columns:
                </p>
                <ul className="text-sm text-gray-600 list-disc list-inside space-y-1 mb-4">
                  <li><strong>Catalog No</strong> - Unique SKU (required)</li>
                  <li><strong>Description</strong> - Item description (optional)</li>
                  <li><strong>Batch No</strong> - Batch number (optional)</li>
                  <li><strong>Unit Price</strong> - Price in rupees (required)</li>
                  <li><strong>Stock Quantity</strong> - Current stock (optional, default 0)</li>
                  <li><strong>HSN Code</strong> - 8-digit HSN code (required)</li>
                  <li><strong>Tax %</strong> - Tax percentage 0-100 (required)</li>
                </ul>
                <p className="text-xs text-gray-500 italic">
                  Items with duplicate SKUs will be skipped.
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Excel File
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-50 file:text-blue-700
                    hover:file:bg-blue-100"
                />
                {importFile && (
                  <p className="text-sm text-gray-600 mt-2">
                    Selected: {importFile.name}
                  </p>
                )}
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setShowImportModal(false);
                    setImportFile(null);
                  }}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImportExcel}
                  disabled={!importFile}
                  className="btn btn-primary flex-1"
                >
                  Import
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
