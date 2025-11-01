/**
 * Decode Page - View attachments and decode items
 */
import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Search, X, Plus, Save } from 'lucide-react';
import api from '@/services/api';
import { Inventory } from '@/types';

interface DecodedItem {
  catalog_no: string;
  quantity: number;
  description?: string;
  inventory_id: string;
  unit_price: number;
  tax: number;
}

interface Attachment {
  id: string;
  original_filename: string;
  file_type: string;
  file_path: string;
}

export default function DecodePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const orderId = searchParams.get('order_id');
  
  // Attachment state
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [currentAttachmentIndex, setCurrentAttachmentIndex] = useState(0);
  
  // Decoded items state
  const [decodedItems, setDecodedItems] = useState<DecodedItem[]>([]);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Inventory[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedCatalog, setSelectedCatalog] = useState<Inventory | null>(null);
  const [quantity, setQuantity] = useState<number>(1);

  // Fetch attachments and existing decoded items for the order
  useEffect(() => {
    if (orderId) {
      fetchAttachments();
      fetchExistingDecodedItems();
    }
  }, [orderId]);

  const fetchAttachments = async () => {
    try {
      const response = await api.getAttachments(orderId!);
      setAttachments(response);
    } catch (error) {
      console.error('Error fetching attachments:', error);
    }
  };

  const fetchExistingDecodedItems = async () => {
    try {
      const order = await api.getOrder(orderId!);
      if (order.items && order.items.length > 0) {
        // Filter only decoded items (items with inventory_id)
        const existingDecoded = order.items
          .filter((item: any) => item.inventory_id && item.inventory)
          .map((item: any) => ({
            catalog_no: item.inventory.sku,
            quantity: item.quantity,
            description: item.inventory.description,
            inventory_id: item.inventory.id,
            unit_price: item.unit_price || item.inventory.unit_price,
            tax: item.gst_percentage || item.inventory.tax,
          }));
        setDecodedItems(existingDecoded);
      }
    } catch (error) {
      console.error('Error fetching existing decoded items:', error);
    }
  };

  // Search inventory items
  useEffect(() => {
    const searchInventory = async () => {
      if (catalogSearch.length > 0 && !selectedCatalog) {
        try {
          const results = await api.getInventory({ search: catalogSearch });
          // Filter out items that are already in the decoded list
          const addedCatalogNos = decodedItems.map((item: DecodedItem) => item.catalog_no);
          const filteredResults = results.filter((item: Inventory) => !addedCatalogNos.includes(item.sku));
          setSearchResults(filteredResults);
          setShowDropdown(true);
        } catch (error) {
          console.error('Error searching inventory:', error);
          setSearchResults([]);
        }
      } else {
        setSearchResults([]);
        setShowDropdown(false);
      }
    };

    const debounce = setTimeout(searchInventory, 250);
    return () => clearTimeout(debounce);
  }, [catalogSearch, decodedItems, selectedCatalog]);

  const currentAttachment = attachments[currentAttachmentIndex];
  const isImage = currentAttachment?.file_type?.startsWith('image/');
  const isPdf = currentAttachment?.file_type === 'application/pdf';
  
  // State for image blob URL
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  
  // Load image/PDF with authentication
  useEffect(() => {
    if (!currentAttachment) {
      setImageUrl(null);
      setPdfUrl(null);
      return;
    }
    
    const loadAttachment = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/v1/attachments/download/${currentAttachment.id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to load attachment');
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        if (isImage) {
          setImageUrl(url);
          setPdfUrl(null);
        } else if (isPdf) {
          setPdfUrl(url);
          setImageUrl(null);
        }
      } catch (error) {
        console.error('Error loading attachment:', error);
        setImageUrl(null);
        setPdfUrl(null);
      }
    };
    
    loadAttachment();
    
    // Cleanup blob URLs
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [currentAttachment]);

  const handlePreviousAttachment = () => {
    if (currentAttachmentIndex > 0) {
      setCurrentAttachmentIndex(currentAttachmentIndex - 1);
    }
  };

  const handleNextAttachment = () => {
    if (currentAttachmentIndex < attachments.length - 1) {
      setCurrentAttachmentIndex(currentAttachmentIndex + 1);
    }
  };

  const handleSelectCatalog = (item: Inventory) => {
    setSelectedCatalog(item);
    setCatalogSearch(item.sku);
    setShowDropdown(false);
    setSearchResults([]);
  };

  const handleAddItem = () => {
    if (selectedCatalog && quantity > 0) {
      const newItem: DecodedItem = {
        catalog_no: selectedCatalog.sku,
        quantity: quantity,
        description: selectedCatalog.description,
        inventory_id: selectedCatalog.id,
        unit_price: selectedCatalog.unit_price,
        tax: selectedCatalog.tax,
      };
      
      setDecodedItems([newItem, ...decodedItems]);
      
      // Reset form
      setSelectedCatalog(null);
      setCatalogSearch('');
      setQuantity(1);
    }
  };

  const handleSaveDecodedItems = async () => {
    if (!orderId || decodedItems.length === 0) return;

    try {
      const items = decodedItems.map(item => ({
        inventory_id: item.inventory_id,
        quantity: item.quantity,
        unit_price: item.unit_price,
        gst_percentage: item.tax,
      }));

      await api.updateDecodedItems(orderId, items);
      
      // Invalidate the order cache to force a refresh
      await queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      
      // Navigate back
      navigate(`/orders/${orderId}`, { replace: true });
    } catch (error) {
      console.error('Error saving decoded items:', error);
      alert('Failed to save decoded items. Please try again.');
    }
  };

  const handleRemoveItem = (index: number) => {
    const reversedIndex = decodedItems.length - 1 - index;
    setDecodedItems(decodedItems.filter((_, i) => i !== reversedIndex));
  };

  const handleUpdateQuantity = (index: number, newQuantity: number) => {
    const reversedIndex = decodedItems.length - 1 - index;
    const updated = [...decodedItems];
    updated[reversedIndex].quantity = newQuantity;
    setDecodedItems(updated);
  };

  return (
    <div className="h-[calc(100vh-80px)] flex gap-4">
      {/* Left Section - Attachment Viewer (80%) */}
      <div className="w-[80%] bg-white rounded-lg shadow-sm flex flex-col">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {currentAttachment?.original_filename || 'No attachments'}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePreviousAttachment}
              disabled={currentAttachmentIndex === 0}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={20} />
            </button>
            <span className="text-sm text-gray-600">
              {attachments.length > 0 ? `${currentAttachmentIndex + 1} / ${attachments.length}` : '0 / 0'}
            </span>
            <button
              onClick={handleNextAttachment}
              disabled={currentAttachmentIndex === attachments.length - 1}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>

        {/* Viewer */}
        <div className="flex-1 overflow-auto bg-gray-50 flex items-center justify-center p-4">
          {!currentAttachment ? (
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium">No attachments available</p>
              <p className="text-sm mt-2">Upload attachments to the order to view them here</p>
            </div>
          ) : isImage && imageUrl ? (
            <img
              src={imageUrl}
              alt={currentAttachment.original_filename}
              className="max-w-full max-h-full object-contain shadow-lg"
            />
          ) : isPdf && pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0 rounded shadow-lg"
              title={currentAttachment.original_filename}
            />
          ) : (
            <div className="text-center text-gray-500 bg-white p-8 rounded-lg shadow">
              <p className="text-lg font-medium mb-2">Preview not available</p>
              <p className="text-sm text-gray-600 mb-1">
                File: <span className="font-mono">{currentAttachment.original_filename}</span>
              </p>
              <p className="text-sm text-gray-600 mb-4">
                Type: <span className="font-mono">{currentAttachment.file_type}</span>
              </p>
              <p className="text-xs text-gray-500">
                This format cannot be viewed in the browser.
                <br />
                Only images (PNG, JPG, GIF, etc.) and PDF files are supported.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Right Section - Decoded Items (20%) */}
      <div className="w-[20%] bg-white rounded-lg shadow-sm flex flex-col">
        {/* Header */}
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Decoded Items</h2>
        </div>

        {/* Add Item Form - Compact Single Row */}
        <div className="p-4 border-b">
          <div className="flex items-center gap-1">
            {/* Catalog Search - 60% */}
            <div className="relative w-[60%]">
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Catalog No
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)}
                  onFocus={() => catalogSearch && setShowDropdown(true)}
                  placeholder="Search..."
                  className="input input-sm w-full pr-6"
                />
                <Search className="absolute right-1 top-1/2 transform -translate-y-1/2 text-gray-400" size={12} />
              </div>

              {/* Dropdown */}
              {showDropdown && searchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                  {searchResults.map((item, index) => (
                    <button
                      key={item.id}
                      onClick={() => handleSelectCatalog(item)}
                      className={`w-full text-left px-2 py-1.5 hover:bg-primary-50 focus:bg-primary-50 focus:outline-none transition-colors ${
                        index % 2 === 0 ? 'bg-white' : 'bg-gray-100'
                      }`}
                    >
                      <div className="font-medium text-xs text-gray-900">{item.sku}</div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        Stock: {item.stock_quantity}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Quantity - 30% */}
            <div className="w-[30%]">
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Qty
              </label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                min="1"
                disabled={!selectedCatalog}
                className="input input-sm w-full text-center px-1"
              />
            </div>

            {/* Add Button - Small */}
            <div className="pt-5">
              <button
                onClick={handleAddItem}
                disabled={!selectedCatalog || quantity <= 0}
                className="btn btn-primary px-1.5 py-1 text-xs rounded"
                title="Add item"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Items List - Compact Format */}
        <div className="flex-1 overflow-auto p-4">
          {decodedItems.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <p className="text-sm">No items added yet</p>
            </div>
          ) : (
            <div className="space-y-1">
              {[...decodedItems].reverse().map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded border-b border-gray-100"
                >
                  <div className="font-mono text-sm font-medium text-gray-900">
                    {item.catalog_no}
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      type="number"
                      value={item.quantity}
                      onChange={(e) => handleUpdateQuantity(index, Number(e.target.value))}
                      min="1"
                      className="input input-sm w-16 text-center font-medium"
                    />
                    <button
                      onClick={() => handleRemoveItem(index)}
                      className="p-1 hover:bg-red-100 rounded text-red-600"
                      title="Remove"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {decodedItems.length > 0 && (
          <div className="p-4 border-t bg-gray-50">
            <div className="text-sm text-gray-600 mb-3">
              Total Items: <span className="font-semibold">{decodedItems.length}</span>
            </div>
            <button 
              onClick={handleSaveDecodedItems}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Save size={16} />
              Save Decoded Items
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
