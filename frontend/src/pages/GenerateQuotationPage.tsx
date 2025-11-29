/**
 * Generate Quotation Page - Create quotation with price list and discount
 */
import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileText, Edit2, X, Check } from 'lucide-react';
import api from '@/services/api';
import { useAuth } from '@/context/AuthContext';

interface PriceList {
  id: string;
  name: string;
  description?: string;
  is_default: boolean;
}

interface Inventory {
  id: string;
  sku: string;
  description?: string;
  hsn_code?: string;
  tax?: number;
}

interface OrderItem {
  id: string;
  inventory_id: string;
  inventory: Inventory;
  quantity: number;
  unit_price: number;
}

interface Order {
  id: string;
  order_number: string;
  customer: {
    id: string;
    name: string;
  };
  items: OrderItem[];
  status: string;
  workflow_stage: string;
}

interface PriceListItem {
  id: string;
  inventory_id: string;
  unit_price: number;
  tax_percentage?: number;
}

interface QuotationItem extends OrderItem {
  hsn_code: string;
  final_unit_price: number;
  amount: number;
  tax_percent: number;
  tax_amount: number;
  total_amount: number;
}

export default function GenerateQuotationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id');

  const [selectedPriceListId, setSelectedPriceListId] = useState<string>('');
  const [discountPercent, setDiscountPercent] = useState<number>(0);
  const [isEditingOrderNumber, setIsEditingOrderNumber] = useState(false);
  const [editedOrderNumber, setEditedOrderNumber] = useState('');
  // Store custom unit prices per item (itemId -> custom price)
  const [customUnitPrices, setCustomUnitPrices] = useState<Record<string, number>>({});

  // Check role access
  const canAccess = user?.role_name === 'quoter' || user?.role_name === 'executive';

  // Fetch order details
  const { data: order, isLoading: orderLoading } = useQuery<Order>({
    queryKey: ['order', orderId],
    queryFn: () => api.getOrder(orderId!),
    enabled: !!orderId && canAccess,
  });

  // Fetch price lists
  const { data: priceLists = [] } = useQuery<PriceList[]>({
    queryKey: ['priceLists'],
    queryFn: () => api.getPriceLists(),
    enabled: canAccess,
  });

  // Fetch price list items when price list is selected
  const { data: priceListItems = [] } = useQuery<PriceListItem[]>({
    queryKey: ['priceListItems', selectedPriceListId],
    queryFn: () => api.getPriceListItems(selectedPriceListId),
    enabled: !!selectedPriceListId,
  });

  // Calculate quotation items whenever order, price list, discount, or custom prices change
  const quotationItems = useMemo(() => {
    if (!order?.items) return [];

    return order.items.map((item) => {
      // Priority: custom price > price list > standard price
      let unitPrice = Number(item.unit_price);
      let taxPercent = Number(item.inventory.tax || 5); // Default from inventory or 5%
      
      // Check if there's a custom price for this item
      if (customUnitPrices[item.id] !== undefined) {
        unitPrice = customUnitPrices[item.id];
      } else if (selectedPriceListId && priceListItems.length > 0) {
        const priceListItem = priceListItems.find(
          (pli) => pli.inventory_id === item.inventory_id
        );
        if (priceListItem) {
          unitPrice = Number(priceListItem.unit_price);
          taxPercent = Number(priceListItem.tax_percentage || taxPercent);
        }
      }

      // Calculate amounts
      const grossAmount = unitPrice * item.quantity;
      const discountAmount = (grossAmount * discountPercent) / 100;
      const amount = grossAmount - discountAmount;
      const taxAmount = (amount * taxPercent) / 100;
      const totalAmount = amount + taxAmount;

      return {
        ...item,
        hsn_code: item.inventory.hsn_code || '',
        final_unit_price: unitPrice,
        amount,
        tax_percent: taxPercent,
        tax_amount: taxAmount,
        total_amount: totalAmount,
      };
    });
  }, [order?.items, selectedPriceListId, priceListItems, discountPercent, customUnitPrices]);

  // Calculate totals
  const subTotal = useMemo(() => 
    quotationItems.reduce((sum, item) => sum + (Number(item.final_unit_price) * item.quantity), 0),
    [quotationItems]
  );
  
  const discountAmount = useMemo(() => 
    (subTotal * discountPercent) / 100,
    [subTotal, discountPercent]
  );
  
  const totalTaxAmount = useMemo(() => 
    quotationItems.reduce((sum, item) => sum + Number(item.tax_amount), 0),
    [quotationItems]
  );
  
  const grandTotal = useMemo(() => 
    quotationItems.reduce((sum, item) => sum + Number(item.total_amount), 0),
    [quotationItems]
  );

  // Save and submit quotation mutation
  const saveQuotationMutation = useMutation({
    mutationFn: async () => {
      return await api.submitQuotation(orderId!, {
        price_list_id: selectedPriceListId || null,
        discount_percent: discountPercent,
        sub_total: subTotal,
        discount_amount: discountAmount,
        tax_amount: totalTaxAmount,
        grand_total: grandTotal,
        custom_prices: customUnitPrices, // Send custom prices to backend
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      navigate(`/orders/${orderId}`);
    },
    onError: (error) => {
      console.error('Error saving quotation:', error);
      alert('Failed to save quotation. Please try again.');
    },
  });

  // Update order number mutation
  const updateOrderNumberMutation = useMutation({
    mutationFn: ({ orderId, newOrderNumber }: { orderId: string; newOrderNumber: string }) =>
      api.updateOrderNumber(orderId, newOrderNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      setIsEditingOrderNumber(false);
      setEditedOrderNumber('');
    },
    onError: (error: any) => {
      alert(`Error updating order number: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    },
  });

  const handleEditOrderNumber = () => {
    setEditedOrderNumber(order?.order_number || '');
    setIsEditingOrderNumber(true);
  };

  const handleSaveOrderNumber = () => {
    if (!editedOrderNumber.trim()) {
      alert('Order number cannot be empty');
      return;
    }
    updateOrderNumberMutation.mutate({
      orderId: orderId!,
      newOrderNumber: editedOrderNumber.trim(),
    });
  };

  const handleCancelEditOrderNumber = () => {
    setIsEditingOrderNumber(false);
    setEditedOrderNumber('');
  };

  // Handle unit price change
  const handleUnitPriceChange = (itemId: string, newPrice: string) => {
    const price = parseFloat(newPrice);
    if (!isNaN(price) && price >= 0) {
      setCustomUnitPrices(prev => ({
        ...prev,
        [itemId]: price
      }));
    } else if (newPrice === '') {
      // Remove custom price if input is cleared
      setCustomUnitPrices(prev => {
        const updated = { ...prev };
        delete updated[itemId];
        return updated;
      });
    }
  };

  const handleSaveAndSubmit = () => {
    if (quotationItems.length === 0) {
      alert('No items to quote');
      return;
    }
    saveQuotationMutation.mutate();
  };

  if (!canAccess) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-600">Access denied. Only Quoters and Executives can generate quotations.</p>
      </div>
    );
  }

  if (orderLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading order details...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-600">Order not found</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Compact Header */}
      <div className="bg-white border-b shadow-sm">
        <div className="flex flex-col p-4">
          {/* Top bar with back button and title */}
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => navigate(`/orders/${orderId}`)}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft size={18} />
              <span className="text-sm">Back to Order</span>
            </button>
            <div className="flex items-center gap-2">
              <FileText size={20} className="text-blue-600" />
              <h1 className="text-lg font-bold text-gray-900">Generate Quotation</h1>
            </div>
          </div>

          {/* Order info and controls in single compact row */}
          <div className="flex items-center gap-4">
            {/* Order Info */}
            <div className="flex gap-4 text-xs">
              <span className="text-gray-600 flex items-center gap-2">
                Order: 
                {isEditingOrderNumber ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={editedOrderNumber}
                      onChange={(e) => setEditedOrderNumber(e.target.value)}
                      className="input input-sm w-40 text-xs font-semibold"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveOrderNumber();
                        if (e.key === 'Escape') handleCancelEditOrderNumber();
                      }}
                    />
                    <button
                      onClick={handleSaveOrderNumber}
                      disabled={updateOrderNumberMutation.isPending}
                      className="p-1 hover:bg-green-100 rounded transition-colors"
                      title="Save"
                    >
                      <Check size={14} className="text-green-600" />
                    </button>
                    <button
                      onClick={handleCancelEditOrderNumber}
                      disabled={updateOrderNumberMutation.isPending}
                      className="p-1 hover:bg-red-100 rounded transition-colors"
                      title="Cancel"
                    >
                      <X size={14} className="text-red-600" />
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="font-semibold text-gray-900">{order.order_number}</span>
                    <button
                      onClick={handleEditOrderNumber}
                      className="p-1 hover:bg-gray-100 rounded transition-colors"
                      title="Edit order number"
                    >
                      <Edit2 size={12} className="text-gray-600 hover:text-blue-600" />
                    </button>
                  </>
                )}
              </span>
              <span className="text-gray-600">
                Customer: <span className="font-semibold text-gray-900">{order.customer.name}</span>
              </span>
            </div>

            {/* Spacer */}
            <div className="flex-1"></div>

            {/* Price List Picker */}
            <div className="w-56">
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Price List
              </label>
              <select
                value={selectedPriceListId}
                onChange={(e) => setSelectedPriceListId(e.target.value)}
                className="input input-sm w-full text-xs"
              >
                <option value="">Standard Prices</option>
                {priceLists.map((pl) => (
                  <option key={pl.id} value={pl.id}>
                    {pl.name} {pl.is_default ? '(Default)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Discount Input */}
            <div className="w-32">
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Discount %
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={discountPercent}
                onChange={(e) => setDiscountPercent(Math.max(0, Math.min(100, parseFloat(e.target.value) || 0)))}
                className="input input-sm w-full text-xs"
                placeholder="0"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Body Container with Fixed Height */}
      <div className="px-4 py-6">
        <div className="flex gap-6" style={{ height: 'calc(100vh - 280px)' }}>
          {/* Left Section - Items Table (85%) */}
          <div className="w-[85%] overflow-auto">
            <div className="bg-white rounded-lg shadow overflow-hidden h-full">
            <table className="w-full">
              <thead className="bg-gray-50 sticky top-0">
                <tr className="border-b">
                  <th className="text-left p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Sr No</th>
                  <th className="text-left p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Catalog No</th>
                  <th className="text-left p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Description</th>
                  <th className="text-left p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">HSN Code</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Unit Price</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Qty</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Disc %</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Amount</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Tax %</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Tax Amt</th>
                  <th className="text-right p-3 text-xs font-semibold text-gray-700 whitespace-nowrap">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {quotationItems.map((item, index) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="p-3 text-xs text-gray-900 whitespace-nowrap">{index + 1}</td>
                    <td className="p-3 text-xs font-mono text-gray-900 whitespace-nowrap">{item.inventory.sku}</td>
                    <td className="p-3 text-xs text-gray-700 max-w-[200px]">
                      <div className="truncate" title={item.inventory.description || 'No description'}>
                        {item.inventory.description || 'No description'}
                      </div>
                    </td>
                    <td className="p-3 text-xs text-gray-600 whitespace-nowrap">{item.hsn_code || '-'}</td>
                    <td className="p-3 text-xs text-right font-semibold text-gray-900 whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <span className="text-gray-600">₹</span>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.final_unit_price}
                          onChange={(e) => handleUnitPriceChange(item.id, e.target.value)}
                          className={`w-24 text-right border rounded px-2 py-1 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            customUnitPrices[item.id] !== undefined 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'border-gray-300'
                          }`}
                          title={customUnitPrices[item.id] !== undefined ? 'Custom price (edited)' : 'Click to edit price'}
                        />
                      </div>
                    </td>
                    <td className="p-3 text-xs text-right text-gray-900 whitespace-nowrap">{item.quantity}</td>
                    <td className="p-3 text-xs text-right text-gray-600 whitespace-nowrap">{discountPercent}%</td>
                    <td className="p-3 text-xs text-right font-semibold text-gray-900 whitespace-nowrap">₹{Number(item.amount).toFixed(2)}</td>
                    <td className="p-3 text-xs text-right text-gray-600 whitespace-nowrap">{item.tax_percent}%</td>
                    <td className="p-3 text-xs text-right text-gray-900 whitespace-nowrap">₹{Number(item.tax_amount).toFixed(2)}</td>
                    <td className="p-3 text-xs text-right font-bold text-gray-900 whitespace-nowrap">₹{Number(item.total_amount).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Section - Summary (15%) */}
        <div className="w-[15%] bg-white rounded-lg shadow p-4 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-2">Summary</h3>
            <div className="space-y-2">
              <div className="flex justify-between items-center py-1 border-b">
                <span className="text-xs font-medium text-gray-700">Sub Total:</span>
                <span className="text-xs font-semibold text-gray-900">₹{subTotal.toFixed(2)}</span>
              </div>
              
              {discountPercent > 0 && (
                <>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-xs text-gray-600">Disc ({discountPercent}%):</span>
                    <span className="text-xs font-medium text-red-600">-₹{discountAmount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-xs text-gray-600">After Disc:</span>
                    <span className="text-xs font-medium text-gray-900">₹{(subTotal - discountAmount).toFixed(2)}</span>
                  </div>
                </>
              )}
              
              <div className="flex justify-between items-center py-1">
                <span className="text-xs text-gray-600">Total Tax:</span>
                <span className="text-xs font-medium text-gray-900">₹{totalTaxAmount.toFixed(2)}</span>
              </div>
              
              <div className="flex justify-between items-center py-2 border-t-2 border-gray-300 mt-2">
                <span className="text-sm font-bold text-gray-900">Grand Total:</span>
                <span className="text-sm font-bold text-blue-600">₹{grandTotal.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2 mt-4">
            <button
              onClick={handleSaveAndSubmit}
              className="btn btn-primary btn-sm w-full text-xs py-2"
            >
              Save & Submit
            </button>
            <button
              onClick={async () => {
                try {
                  // Generate PDF preview with custom prices
                  const blob = await api.generateQuotationPreviewPDF(orderId!, {
                    price_list_id: selectedPriceListId || null,
                    discount_percent: discountPercent,
                    custom_prices: customUnitPrices,
                  });
                  
                  // Download the PDF
                  const blobUrl = window.URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = blobUrl;
                  link.download = `Quotation_Preview_${order.order_number}.pdf`;
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                  window.URL.revokeObjectURL(blobUrl);
                } catch (error) {
                  console.error('Error generating PDF:', error);
                  alert('Failed to generate PDF. Please try again.');
                }
              }}
              className="btn btn-secondary btn-sm w-full text-xs py-2"
            >
              <FileText size={14} className="mr-1" />
              Generate PDF
            </button>
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
