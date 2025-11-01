/**
 * Price Lists Page - Manage pricing for inventory items
 */
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Search, DollarSign, Upload, X } from 'lucide-react';
import api from '@/services/api';
import { useAuth } from '@/context/AuthContext';

interface PriceList {
  id: string;
  name: string;
  description?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

interface Inventory {
  id: string;
  sku: string;
  description?: string;
}

interface PriceListItem {
  id: string;
  price_list_id: string;
  inventory_id: string;
  inventory: Inventory;
  unit_price: number;
  tax_percentage: number;
  created_at: string;
  updated_at: string;
}

export default function PriceListsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPriceList, setSelectedPriceList] = useState<PriceList | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [priceListToDelete, setPriceListToDelete] = useState<PriceList | null>(null);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editingPrice, setEditingPrice] = useState<string>('');
  const [itemSearchTerm, setItemSearchTerm] = useState<string>('');
  const [debouncedItemSearch, setDebouncedItemSearch] = useState<string>('');
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_default: false,
  });

  // Fetch price lists
  const { data: priceLists = [], isLoading } = useQuery<PriceList[]>({
    queryKey: ['priceLists'],
    queryFn: () => api.getPriceLists(),
  });

  // Fetch items for selected price list
  const { data: priceListItems = [] } = useQuery<PriceListItem[]>({
    queryKey: ['priceListItems', selectedPriceList?.id],
    queryFn: () => api.getPriceListItems(selectedPriceList!.id),
    enabled: !!selectedPriceList,
  });

  // Create price list mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => api.createPriceList(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['priceLists'] });
      setShowCreateModal(false);
      resetForm();
    },
  });

  // Update price list mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.updatePriceList(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['priceLists'] });
      setShowEditModal(false);
      resetForm();
    },
  });

  // Delete price list mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePriceList(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['priceLists'] });
      setShowDeleteModal(false);
      setPriceListToDelete(null);
      if (selectedPriceList?.id === priceListToDelete?.id) {
        setSelectedPriceList(null);
      }
    },
  });

  // Update price list item mutation
  const updateItemMutation = useMutation({
    mutationFn: ({ priceListId, itemId, unitPrice }: { priceListId: string; itemId: string; unitPrice: number }) =>
      api.updatePriceListItem(priceListId, itemId, { unit_price: unitPrice }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['priceListItems', selectedPriceList?.id] });
      setEditingItemId(null);
      setEditingPrice('');
    },
  });

  const handleSavePrice = (item: PriceListItem) => {
    const newPrice = parseFloat(editingPrice);
    if (isNaN(newPrice) || newPrice <= 0) {
      alert('Please enter a valid price');
      return;
    }
    if (selectedPriceList) {
      updateItemMutation.mutate({
        priceListId: selectedPriceList.id,
        itemId: item.id,
        unitPrice: newPrice,
      });
    }
  };

  const handleImportExcel = async () => {
    if (!importFile || !selectedPriceList) return;

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
          const jsonData = XLSX.utils.sheet_to_json(worksheet) as any[];

          let updatedCount = 0;
          let errors: string[] = [];

          // Process each row
          for (const row of jsonData) {
            const catalogNo = row['Catalog No'] || row['Catalog no'] || row['catalog no'];
            const price = row['Price'] || row['price'];
            const taxPercent = row['Tax %'] || row['Tax%'] || row['tax %'] || row['tax%'];

            if (!catalogNo || !price) {
              errors.push(`Skipped row: Missing catalog number or price`);
              continue;
            }

            // Find matching item
            const matchingItem = priceListItems.find(
              item => item.inventory.sku.toLowerCase() === catalogNo.toString().toLowerCase()
            );

            if (matchingItem) {
              const newPrice = parseFloat(price);
              if (isNaN(newPrice) || newPrice <= 0) {
                errors.push(`Invalid price for ${catalogNo}: ${price}`);
                continue;
              }

              // Parse tax percentage (optional)
              let newTaxPercent = matchingItem.tax_percentage; // Keep existing if not provided
              if (taxPercent !== undefined && taxPercent !== null && taxPercent !== '') {
                const parsedTax = parseFloat(taxPercent);
                if (!isNaN(parsedTax) && parsedTax >= 0 && parsedTax <= 100) {
                  newTaxPercent = parsedTax;
                } else {
                  errors.push(`Invalid tax percentage for ${catalogNo}: ${taxPercent}`);
                }
              }

              // Update the price and tax
              await api.updatePriceListItem(
                selectedPriceList.id,
                matchingItem.id,
                { 
                  unit_price: newPrice,
                  tax_percentage: newTaxPercent
                }
              );
              updatedCount++;
            } else {
              errors.push(`Catalog number not found: ${catalogNo}`);
            }
          }

          // Refresh the items list
          queryClient.invalidateQueries({ queryKey: ['priceListItems', selectedPriceList.id] });

          // Show results
          let message = `Successfully updated ${updatedCount} item(s).`;
          if (errors.length > 0) {
            message += `\n\nWarnings:\n${errors.slice(0, 5).join('\n')}`;
            if (errors.length > 5) {
              message += `\n... and ${errors.length - 5} more`;
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

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      is_default: false,
    });
  };

  const handleCreate = () => {
    setShowCreateModal(true);
    resetForm();
  };

  const handleEdit = (priceList: PriceList) => {
    setSelectedPriceList(priceList);
    setFormData({
      name: priceList.name,
      description: priceList.description || '',
      is_default: priceList.is_default,
    });
    setShowEditModal(true);
  };

  const handleDelete = (priceList: PriceList) => {
    setPriceListToDelete(priceList);
    setShowDeleteModal(true);
  };

  const handleSubmitCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleSubmitEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedPriceList) {
      updateMutation.mutate({ id: selectedPriceList.id, data: formData });
    }
  };

  // Debounce item search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedItemSearch(itemSearchTerm);
    }, 250);
    return () => clearTimeout(timer);
  }, [itemSearchTerm]);

  const filteredPriceLists = priceLists.filter(pl =>
    pl.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    pl.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Filter price list items by catalog number
  const filteredItems = priceListItems.filter(item =>
    item.inventory.sku.toLowerCase().includes(debouncedItemSearch.toLowerCase())
  );

  const canEdit = user?.role_name === 'executive' || user?.role_name === 'quoter';

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading price lists...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Price Lists</h1>
          <p className="text-gray-600 mt-1">Manage pricing for inventory items</p>
        </div>
        {canEdit && (
          <button onClick={handleCreate} className="btn btn-primary">
            <Plus size={20} className="mr-2" />
            New Price List
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Price Lists */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="p-4 border-b">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search price lists..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input pl-10 w-full"
                />
              </div>
            </div>

            <div className="divide-y max-h-[600px] overflow-y-auto">
              {filteredPriceLists.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <DollarSign size={48} className="mx-auto mb-4 text-gray-300" />
                   <p>No price lists found</p>
                </div>
              ) : (
                filteredPriceLists.map((priceList) => (
                  <div
                    key={priceList.id}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedPriceList?.id === priceList.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                    }`}
                    onClick={() => setSelectedPriceList(priceList)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900">{priceList.name}</h3>
                          {priceList.is_default && (
                            <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-full">
                              Default
                            </span>
                          )}
                        </div>
                        {priceList.description && (
                          <p className="text-sm text-gray-600 mt-1">{priceList.description}</p>
                        )}
                        <p className="text-xs text-gray-500 mt-2">
                          Updated {new Date(priceList.updated_at).toLocaleDateString()}
                        </p>
                      </div>
                      {canEdit && (
                        <div className="flex gap-2 ml-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEdit(priceList);
                            }}
                            className="p-1 hover:bg-blue-100 rounded text-blue-600"
                            title="Edit"
                          >
                            <Edit size={16} />
                          </button>
                          {!priceList.is_default && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(priceList);
                              }}
                              className="p-1 hover:bg-red-100 rounded text-red-600"
                              title="Delete"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: Price List Items */}
        <div className="lg:col-span-2">
          {selectedPriceList ? (
            <div className="card">
              {/* Header with Search and Import */}
              <div className="p-4 border-b space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">{selectedPriceList.name}</h2>
                    <p className="text-sm text-gray-600 mt-1">
                      {filteredItems.length} of {priceListItems.length} item{priceListItems.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                  {canEdit && (
                    <button
                      onClick={() => setShowImportModal(true)}
                      className="btn btn-secondary btn-sm flex items-center gap-2"
                    >
                      <Upload size={16} />
                      Import from Excel
                    </button>
                  )}
                </div>
                
                {/* Search Bar */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="text"
                    placeholder="Search by catalog number..."
                    value={itemSearchTerm}
                    onChange={(e) => setItemSearchTerm(e.target.value)}
                    className="input pl-10 w-full"
                  />
                  {itemSearchTerm && (
                    <button
                      onClick={() => setItemSearchTerm('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X size={18} />
                    </button>
                  )}
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr className="border-b">
                      <th className="text-left p-3 text-sm font-semibold text-gray-700">Catalog No</th>
                      <th className="text-left p-3 text-sm font-semibold text-gray-700">Item Description</th>
                      <th className="text-right p-3 text-sm font-semibold text-gray-700">Price</th>
                      <th className="text-right p-3 text-sm font-semibold text-gray-700">Tax %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {filteredItems.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="p-8 text-center text-gray-500">
                          {itemSearchTerm ? 'No items match your search' : 'No items in this price list'}
                        </td>
                      </tr>
                    ) : (
                      filteredItems.map((item) => (
                        <tr key={item.id} className="hover:bg-gray-50">
                          <td className="p-3 text-sm font-mono text-gray-900">{item.inventory.sku}</td>
                          <td className="p-3 text-sm text-gray-700">{item.inventory.description || 'No description'}</td>
                          <td className="p-3 text-sm text-right">
                            {editingItemId === item.id && canEdit ? (
                              <div className="flex items-center justify-end gap-2">
                                <span className="text-gray-600">₹</span>
                                <input
                                  type="number"
                                  value={editingPrice}
                                  onChange={(e) => setEditingPrice(e.target.value)}
                                  onBlur={() => handleSavePrice(item)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      handleSavePrice(item);
                                    } else if (e.key === 'Escape') {
                                      setEditingItemId(null);
                                    }
                                  }}
                                  autoFocus
                                  className="input input-sm w-32 text-right"
                                  step="0.01"
                                />
                              </div>
                            ) : (
                              <button
                                onClick={() => {
                                  if (canEdit) {
                                    setEditingItemId(item.id);
                                    setEditingPrice(item.unit_price.toString());
                                  }
                                }}
                                className={`text-gray-900 font-semibold ${canEdit ? 'hover:text-blue-600 cursor-pointer' : ''}`}
                              >
                                ₹{Number(item.unit_price).toFixed(2)}
                              </button>
                            )}
                          </td>
                          <td className="p-3 text-sm text-right text-gray-600">
                            {Number(item.tax_percentage || 0).toFixed(2)}%
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="card p-12 text-center text-gray-500">
              <DollarSign size={64} className="mx-auto mb-4 text-gray-300" />
              <p className="text-lg">Select a price list to view items</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b">
              <h2 className="text-xl font-bold">Create Price List</h2>
            </div>
            <form onSubmit={handleSubmitCreate} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input w-full"
                  rows={3}
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="mr-2"
                />
                <label htmlFor="is_default" className="text-sm text-gray-700">
                  Set as default price list
                </label>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="btn btn-primary flex-1"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b">
              <h2 className="text-xl font-bold">Edit Price List</h2>
            </div>
            <form onSubmit={handleSubmitEdit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input w-full"
                  rows={3}
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="edit_is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="mr-2"
                />
                <label htmlFor="edit_is_default" className="text-sm text-gray-700">
                  Set as default price list
                </label>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="btn btn-primary flex-1"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import from Excel Modal */}
      {showImportModal && selectedPriceList && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b">
              <h2 className="text-xl font-bold">Import Prices from Excel</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <p className="text-sm text-gray-700 mb-3">
                  Upload an Excel file with the following columns:
                </p>
                <ul className="text-sm text-gray-600 list-disc list-inside space-y-1 mb-4">
                  <li><strong>Catalog No</strong> - Item SKU/Catalog number</li>
                  <li><strong>Item Description</strong> - Item description (optional)</li>
                  <li><strong>Price</strong> - New unit price</li>
                  <li><strong>Tax %</strong> - Tax percentage (optional)</li>
                </ul>
                <p className="text-xs text-gray-500 italic">
                  Only prices and tax for matching catalog numbers will be updated.
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

      {/* Delete Modal */}
      {showDeleteModal && priceListToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b">
              <h2 className="text-xl font-bold text-red-600">Delete Price List</h2>
            </div>
            <div className="p-6">
              <p className="text-gray-700 mb-4">
                Are you sure you want to delete <strong>{priceListToDelete.name}</strong>?
                This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => deleteMutation.mutate(priceListToDelete.id)}
                  disabled={deleteMutation.isPending}
                  className="btn bg-red-600 hover:bg-red-700 text-white flex-1"
                >
                  {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
