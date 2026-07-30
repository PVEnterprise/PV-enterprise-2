/**
 * Generate Quotation Page - Create quotation with price list and discount
 */
import { Fragment, useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileText, Edit2, X, Check, Plus, Search, ChevronUp, ChevronDown } from 'lucide-react';
import api from '@/services/api';
import { useAuth } from '@/context/AuthContext';
import { Inventory as InventoryFull } from '@/types';
import QuotationPDFModal, { QuotationPDFFormData } from '@/components/QuotationPDFModal';

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
  gst_percentage?: number;
  section_name?: string;
}

interface Order {
  id: string;
  order_number: string;
  customer: {
    id: string;
    name: string;
    bank_account_name?: string;
    bank_account_number?: string;
    bank_name?: string;
    bank_ifsc?: string;
    bank_branch?: string;
    terms_and_conditions?: string;
  };
  items: OrderItem[];
  status: string;
  workflow_stage: string;
  price_list_id?: string | null;
  discount_percentage?: number | null;
  subject?: string | null;
  quotation_date?: string | null;
  created_at: string;
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

const formatINR = (amount: number) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);

export default function GenerateQuotationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id');

  const [selectedPriceListId, setSelectedPriceListId] = useState<string>('');
  const [discountPercent, setDiscountPercent] = useState<number>(0);
  const [quotationDate, setQuotationDate] = useState<string>('');
  const [expiryDate, setExpiryDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split('T')[0];
  });
  const [isEditingOrderNumber, setIsEditingOrderNumber] = useState(false);
  const [editedOrderNumber, setEditedOrderNumber] = useState('');
  const [draftSavedMsg, setDraftSavedMsg] = useState<string | null>(null);
  const draftMsgTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initializedFromOrder = useRef(false);
  // Store custom unit prices per item (itemId -> custom price)
  const [customUnitPrices, setCustomUnitPrices] = useState<Record<string, number>>({});
  const [rawPriceInputs, setRawPriceInputs] = useState<Record<string, string>>({});
  const [subject, setSubject] = useState<string>('');
  const [showPDFModal, setShowPDFModal] = useState(false);
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

  // Add item state — addItemAt holds the index (within order.items) the new
  // item should be inserted before; null means the inline form is closed.
  const [addItemAt, setAddItemAt] = useState<number | null>(null);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [searchResults, setSearchResults] = useState<InventoryFull[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedCatalog, setSelectedCatalog] = useState<InventoryFull | null>(null);
  const [addQuantity, setAddQuantity] = useState<number>(1);

  // Check role access
  const canAccess = user?.role_name === 'quoter' || user?.role_name === 'executive';

  // Fetch order details
  const { data: order, isLoading: orderLoading } = useQuery<Order>({
    queryKey: ['order', orderId],
    queryFn: () => api.getOrder(orderId!),
    enabled: !!orderId && canAccess,
  });

  // Initialise price list + discount from previously saved draft when order loads
  useEffect(() => {
    if (order && !initializedFromOrder.current) {
      initializedFromOrder.current = true;
      if (order.price_list_id) setSelectedPriceListId(String(order.price_list_id));
      if (order.discount_percentage != null) setDiscountPercent(Number(order.discount_percentage));
      if (order.subject) setSubject(order.subject);
      // Quotation date defaults to the order's creation date until the user changes it
      const defaultQuotationDate = order.quotation_date
        ? order.quotation_date.split('T')[0]
        : order.created_at.split('T')[0];
      setQuotationDate(defaultQuotationDate);
    }
  }, [order]);

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

  // Search inventory for the Add Item form
  useEffect(() => {
    const searchInventory = async () => {
      if (catalogSearch.length > 0 && !selectedCatalog) {
        try {
          const data = await api.getInventory({ search: catalogSearch });
          setSearchResults((data as any).items ?? data);
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
  }, [catalogSearch, selectedCatalog]);

  // Calculate quotation items whenever order, price list, discount, or custom prices change
  const quotationItems = useMemo(() => {
    if (!order?.items) return [];

    return order.items.map((item) => {
      // Priority: custom price > price list > standard price
      let unitPrice = Number(item.unit_price);
      // Use order item's GST percentage (already set when item was decoded)
      let taxPercent = Number(item.gst_percentage || item.inventory.tax || 5);
      
      // Check if there's a custom price for this item
      if (customUnitPrices[item.id] !== undefined) {
        unitPrice = customUnitPrices[item.id];
      } else if (selectedPriceListId && priceListItems.length > 0) {
        // Use price list price if available
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
  
  const preRoundGrandTotal = useMemo(() =>
    quotationItems.reduce((sum, item) => sum + Number(item.total_amount), 0),
    [quotationItems]
  );

  // Round to the nearest whole rupee, matching Zoho's "Round Off" behaviour on the PDF.
  // Snap to paise first so floating-point drift doesn't produce a fake non-zero round off.
  const preRoundGrandTotalPaise = Math.round(preRoundGrandTotal * 100) / 100;
  const grandTotal = Math.round(preRoundGrandTotalPaise);
  const roundOff = Math.round((grandTotal - preRoundGrandTotalPaise) * 100) / 100;

  // Update quotation date mutation — saves immediately when the user changes the date,
  // independent of Save as Draft / Save & Submit
  const updateQuotationDateMutation = useMutation({
    mutationFn: (newDate: string) => api.updateQuotationDate(orderId!, newDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(`Error updating quotation date: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    },
  });

  const handleQuotationDateChange = (newDate: string) => {
    setQuotationDate(newDate);
    if (newDate) {
      updateQuotationDateMutation.mutate(newDate);
    }
  };

  // Save as draft mutation — persists data, stays on page
  const saveDraftMutation = useMutation({
    mutationFn: async () => {
      return await api.saveQuotationDraft(orderId!, {
        price_list_id: selectedPriceListId || null,
        discount_percent: discountPercent,
        subject,
        quotation_date: quotationDate || null,
        sub_total: subTotal,
        discount_amount: discountAmount,
        tax_amount: totalTaxAmount,
        grand_total: grandTotal,
        custom_prices: customUnitPrices,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      if (draftMsgTimer.current) clearTimeout(draftMsgTimer.current);
      setDraftSavedMsg('Draft saved successfully');
      draftMsgTimer.current = setTimeout(() => setDraftSavedMsg(null), 3000);
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || 'Failed to save draft';
      if (draftMsgTimer.current) clearTimeout(draftMsgTimer.current);
      setDraftSavedMsg(`Error: ${detail}`);
      draftMsgTimer.current = setTimeout(() => setDraftSavedMsg(null), 4000);
    },
  });

  // Save and submit quotation mutation
  const saveQuotationMutation = useMutation({
    mutationFn: async () => {
      return await api.submitQuotation(orderId!, {
        price_list_id: selectedPriceListId || null,
        discount_percent: discountPercent,
        subject,
        quotation_date: quotationDate || null,
        sub_total: subTotal,
        discount_amount: discountAmount,
        tax_amount: totalTaxAmount,
        grand_total: grandTotal,
        custom_prices: customUnitPrices,
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

  // Add/remove items — persists the full item list immediately via the same
  // endpoint the Decode screen uses.
  const updateItemsMutation = useMutation({
    mutationFn: (items: any[]) => api.updateDecodedItems(orderId!, items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to update items');
    },
  });

  const buildItemsPayload = (opts: {
    removeId?: string;
    addItem?: { inventory_id: string; quantity: number; unit_price: number; gst_percentage: number };
    addAtIndex?: number;
  } = {}) => {
    const kept = (order?.items || [])
      .filter((item) => item.id !== opts.removeId)
      .map((item) => ({
        inventory_id: item.inventory_id,
        quantity: item.quantity,
        unit_price: customUnitPrices[item.id] !== undefined ? customUnitPrices[item.id] : item.unit_price,
        gst_percentage: item.gst_percentage,
        section_name: item.section_name || null,
      }));
    if (opts.addItem) {
      const insertAt = opts.addAtIndex !== undefined ? opts.addAtIndex : kept.length;
      kept.splice(insertAt, 0, { ...opts.addItem, section_name: null });
    }
    return kept;
  };

  const handleDeleteItem = (item: OrderItem) => {
    if (quotationItems.length <= 1) {
      alert('A quotation must have at least one item.');
      return;
    }
    if (!window.confirm(`Remove ${item.inventory.sku} from this quotation?`)) return;
    updateItemsMutation.mutate(buildItemsPayload({ removeId: item.id }));
  };

  const handleSelectCatalog = (item: InventoryFull) => {
    setSelectedCatalog(item);
    setCatalogSearch(item.sku);
    setShowDropdown(false);
    setSearchResults([]);
  };

  const handleCancelAddItem = () => {
    setAddItemAt(null);
    setSelectedCatalog(null);
    setCatalogSearch('');
    setAddQuantity(1);
  };

  const handleAddItem = () => {
    if (!selectedCatalog || addQuantity <= 0) return;

    let unitPrice = Number(selectedCatalog.unit_price);
    let taxPercent = Number(selectedCatalog.tax || 5);
    if (selectedPriceListId && priceListItems.length > 0) {
      const pli = priceListItems.find((p) => p.inventory_id === selectedCatalog.id);
      if (pli) {
        unitPrice = Number(pli.unit_price);
        taxPercent = Number(pli.tax_percentage || taxPercent);
      }
    }

    updateItemsMutation.mutate(
      buildItemsPayload({
        addAtIndex: addItemAt ?? undefined,
        addItem: {
          inventory_id: selectedCatalog.id,
          quantity: addQuantity,
          unit_price: unitPrice,
          gst_percentage: taxPercent,
        },
      }),
      { onSuccess: handleCancelAddItem }
    );
  };

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

  // Handle unit price change — allow clearing all digits (stored as raw string)
  const handleUnitPriceChange = (itemId: string, rawValue: string) => {
    setRawPriceInputs(prev => ({ ...prev, [itemId]: rawValue }));
    if (rawValue === '' || rawValue === '.') {
      setCustomUnitPrices(prev => ({ ...prev, [itemId]: 0 }));
    } else {
      const price = parseFloat(rawValue);
      if (!isNaN(price) && price >= 0) {
        setCustomUnitPrices(prev => ({ ...prev, [itemId]: price }));
      }
    }
  };

  const handleUnitPriceBlur = (itemId: string) => {
    setRawPriceInputs(prev => {
      const updated = { ...prev };
      delete updated[itemId];
      return updated;
    });
  };

  const handleSaveAndSubmit = () => {
    if (quotationItems.length === 0) {
      alert('No items to quote');
      return;
    }
    saveQuotationMutation.mutate();
  };

  const handleGeneratePDF = async (formData: QuotationPDFFormData) => {
    setIsGeneratingPDF(true);
    try {
      const blob = await api.generateQuotationPreviewPDF(orderId!, {
        price_list_id: selectedPriceListId || null,
        discount_percent: discountPercent,
        custom_prices: customUnitPrices,
        expiry_date: formData.valid_till || null,
        bank_details: formData.bank_details,
        terms_and_conditions: formData.terms_and_conditions,
      });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `Quotation_Preview_${order?.order_number || 'quotation'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      setShowPDFModal(false);
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setIsGeneratingPDF(false);
    }
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

  const addItemForm = (
    <div className="flex items-center gap-2">
      <div className="relative w-64">
        <div className="relative">
          <input
            type="text"
            value={catalogSearch}
            onChange={(e) => { setCatalogSearch(e.target.value); setSelectedCatalog(null); }}
            onFocus={() => catalogSearch && !selectedCatalog && setShowDropdown(true)}
            placeholder="Search catalog no or description…"
            autoFocus
            className="input input-sm w-full text-xs pr-7"
          />
          <Search className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" size={13} />
        </div>
        {showDropdown && searchResults.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-56 overflow-auto">
            {searchResults.map((inv, i) => (
              <button
                key={inv.id}
                onClick={() => handleSelectCatalog(inv)}
                className={`w-full text-left px-2 py-1.5 hover:bg-blue-50 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}
              >
                <div className="font-mono text-xs font-medium text-gray-900">{inv.sku}</div>
                <div className="text-xs text-gray-500 truncate">{inv.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>
      <input
        type="number"
        min={1}
        value={addQuantity}
        onChange={(e) => setAddQuantity(Math.max(1, parseInt(e.target.value) || 1))}
        className="input input-sm w-16 text-xs text-center"
        title="Quantity"
      />
      <button
        onClick={handleAddItem}
        disabled={!selectedCatalog || updateItemsMutation.isPending}
        className="btn btn-primary btn-sm text-xs px-3 py-1.5 disabled:opacity-40"
      >
        <Check size={13} className="mr-1" />
        {updateItemsMutation.isPending ? 'Adding…' : 'Add'}
      </button>
      <button
        onClick={handleCancelAddItem}
        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
        title="Cancel"
      >
        <X size={14} />
      </button>
    </div>
  );

  return (
    <div className="-m-6 h-[calc(100vh-4rem)] flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm px-4 pt-3 pb-2">
        {/* Row 1: Back + Title */}
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={() => navigate(`/orders/${orderId}`)}
            className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft size={16} />
            Back to Order
          </button>
          <div className="flex items-center gap-2 text-blue-700 font-bold text-base">
            <FileText size={18} />
            Generate Quotation
          </div>
        </div>

        {/* Row 2: Order/Customer (left) + Subject + controls (right) */}
        <div className="flex items-center gap-3">
          {/* Left: order number + customer */}
          <div className="flex items-center gap-3 text-sm min-w-0">
            <span className="text-gray-600 whitespace-nowrap">
              Order:{' '}
              {isEditingOrderNumber ? (
                <span className="inline-flex items-center gap-1">
                  <input
                    type="text"
                    value={editedOrderNumber}
                    onChange={(e) => setEditedOrderNumber(e.target.value)}
                    className="input input-sm w-32 text-xs font-semibold"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveOrderNumber();
                      if (e.key === 'Escape') handleCancelEditOrderNumber();
                    }}
                  />
                  <button onClick={handleSaveOrderNumber} disabled={updateOrderNumberMutation.isPending} className="p-0.5 hover:bg-green-100 rounded" title="Save">
                    <Check size={13} className="text-green-600" />
                  </button>
                  <button onClick={handleCancelEditOrderNumber} disabled={updateOrderNumberMutation.isPending} className="p-0.5 hover:bg-red-100 rounded" title="Cancel">
                    <X size={13} className="text-red-600" />
                  </button>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1">
                  <span className="font-semibold text-gray-900">{order.order_number}</span>
                  <button onClick={handleEditOrderNumber} className="p-0.5 hover:bg-gray-100 rounded" title="Edit order number">
                    <Edit2 size={11} className="text-gray-500 hover:text-blue-600" />
                  </button>
                </span>
              )}
            </span>
            <span className="text-gray-600 flex items-center gap-1 min-w-0">
              <span className="whitespace-nowrap">Customer:</span>
              <span
                className="font-semibold text-gray-900 truncate max-w-[180px]"
                title={order.customer.name}
              >
                {order.customer.name}
              </span>
            </span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Subject */}
          <div className="flex items-center gap-1 w-52">
            <label className="text-xs font-medium text-gray-500 whitespace-nowrap">Subject:</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Optional subject"
              className="input input-sm text-xs flex-1 min-w-0"
            />
          </div>

          {/* Quotation Date */}
          <div className="flex items-center gap-1">
            <label className="text-xs font-medium text-gray-600 whitespace-nowrap">Date</label>
            <input
              type="date"
              value={quotationDate}
              onChange={(e) => handleQuotationDateChange(e.target.value)}
              className="input input-sm text-xs w-32"
              title="Quotation date — defaults to order creation date, saved automatically when changed"
            />
          </div>

          {/* Price List */}
          <div className="flex items-center gap-1">
            <label className="text-xs font-medium text-gray-600 whitespace-nowrap">Price List</label>
            <select
              value={selectedPriceListId}
              onChange={(e) => setSelectedPriceListId(e.target.value)}
              className="input input-sm text-xs w-40"
            >
              <option value="">Standard Prices</option>
              {priceLists.map((pl) => (
                <option key={pl.id} value={pl.id}>{pl.name}{pl.is_default ? ' (Default)' : ''}</option>
              ))}
            </select>
          </div>

          {/* Valid Until */}
          <div className="flex items-center gap-1">
            <label className="text-xs font-medium text-gray-600 whitespace-nowrap">Valid Until</label>
            <input
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
              className="input input-sm text-xs w-32"
            />
          </div>

          {/* Discount */}
          <div className="flex items-center gap-1">
            <label className="text-xs font-medium text-gray-600 whitespace-nowrap">Disc %</label>
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={discountPercent}
              onChange={(e) => setDiscountPercent(Math.max(0, Math.min(100, parseFloat(e.target.value) || 0)))}
              className="input input-sm text-xs w-16"
              placeholder="0"
            />
          </div>
        </div>
      </div>

      {/* Body Container with Fixed Height */}
      <div className="flex-1 overflow-hidden px-4 py-4">
        <div className="flex gap-6 h-full">
          {/* Left Section - Items Table (85%) */}
          <div className="w-[85%] flex flex-col min-h-0">
            <div className="bg-white rounded-lg shadow flex-1 overflow-auto">
            <table className="w-full">
              <thead className="bg-gray-50 sticky top-0 z-10">
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
                  <th className="p-3 w-8"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {quotationItems.map((item, index) => (
                  <Fragment key={item.id}>
                    {addItemAt === index && (
                      <tr className="bg-gray-50/50">
                        <td colSpan={12} className="p-2">{addItemForm}</td>
                      </tr>
                    )}
                    <tr className="hover:bg-gray-50 group">
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
                            type="text"
                            inputMode="decimal"
                            value={rawPriceInputs[item.id] !== undefined ? rawPriceInputs[item.id] : String(item.final_unit_price)}
                            onChange={(e) => handleUnitPriceChange(item.id, e.target.value)}
                            onBlur={() => handleUnitPriceBlur(item.id)}
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
                      <td className="p-3 text-xs text-right font-semibold text-gray-900 whitespace-nowrap">₹{formatINR(Number(item.amount))}</td>
                      <td className="p-3 text-xs text-right text-gray-600 whitespace-nowrap">{item.tax_percent}%</td>
                      <td className="p-3 text-xs text-right text-gray-900 whitespace-nowrap">₹{formatINR(Number(item.tax_amount))}</td>
                      <td className="p-3 text-xs text-right font-bold text-gray-900 whitespace-nowrap">₹{formatINR(Number(item.total_amount))}</td>
                      <td className="p-1 text-center">
                        <div className="flex items-center justify-center">
                          <button
                            onClick={() => setAddItemAt(index)}
                            disabled={updateItemsMutation.isPending}
                            className="p-0.5 rounded text-gray-300 group-hover:text-blue-500 hover:bg-blue-50 transition-colors"
                            title="Insert item above"
                          >
                            <ChevronUp size={13} />
                          </button>
                          <button
                            onClick={() => setAddItemAt(index + 1)}
                            disabled={updateItemsMutation.isPending}
                            className="p-0.5 rounded text-gray-300 group-hover:text-blue-500 hover:bg-blue-50 transition-colors"
                            title="Insert item below"
                          >
                            <ChevronDown size={13} />
                          </button>
                          <button
                            onClick={() => handleDeleteItem(item)}
                            disabled={updateItemsMutation.isPending}
                            className="p-0.5 rounded text-gray-300 group-hover:text-red-500 hover:bg-red-50 transition-colors"
                            title="Remove item"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  </Fragment>
                ))}

                {/* Add Item row — also hosts the insert form when appending at the end */}
                <tr className="bg-gray-50/50">
                  <td colSpan={12} className="p-2">
                    {addItemAt === quotationItems.length ? addItemForm : (
                      <button
                        onClick={() => setAddItemAt(quotationItems.length)}
                        className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 px-2 py-1.5 rounded hover:bg-blue-50 transition-colors"
                      >
                        <Plus size={14} />
                        Add Item
                      </button>
                    )}
                  </td>
                </tr>
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
                <span className="text-xs font-semibold text-gray-900">₹{formatINR(subTotal)}</span>
              </div>
              
              {discountPercent > 0 && (
                <>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-xs text-gray-600">Disc ({discountPercent}%):</span>
                    <span className="text-xs font-medium text-red-600">-₹{formatINR(discountAmount)}</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-xs text-gray-600">After Disc:</span>
                    <span className="text-xs font-medium text-gray-900">₹{formatINR(subTotal - discountAmount)}</span>
                  </div>
                </>
              )}
              
              <div className="flex justify-between items-center py-1">
                <span className="text-xs text-gray-600">Total Tax:</span>
                <span className="text-xs font-medium text-gray-900">₹{formatINR(totalTaxAmount)}</span>
              </div>

              {roundOff !== 0 && (
                <div className="flex justify-between items-center py-1">
                  <span className="text-xs text-gray-600">Rounding:</span>
                  <span className="text-xs font-medium text-gray-900">{roundOff < 0 ? '-' : '+'}₹{formatINR(Math.abs(roundOff))}</span>
                </div>
              )}

              <div className="flex justify-between items-center py-2 border-t-2 border-gray-300 mt-2">
                <span className="text-sm font-bold text-gray-900">Grand Total:</span>
                <span className="text-sm font-bold text-blue-600">₹{formatINR(grandTotal)}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2 mt-4">
            {draftSavedMsg && (
              <p className={`text-xs text-center px-2 py-1 rounded ${
                draftSavedMsg.startsWith('Error') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'
              }`}>
                {draftSavedMsg}
              </p>
            )}
            <button
              onClick={() => {
                if (quotationItems.length === 0) { alert('No items to save'); return; }
                saveDraftMutation.mutate();
              }}
              disabled={saveDraftMutation.isPending}
              className="btn btn-secondary btn-sm w-full text-xs py-2"
            >
              {saveDraftMutation.isPending ? 'Saving…' : 'Save as Draft'}
            </button>
            <button
              onClick={handleSaveAndSubmit}
              disabled={saveQuotationMutation.isPending}
              className="btn btn-primary btn-sm w-full text-xs py-2"
            >
              {saveQuotationMutation.isPending ? 'Submitting…' : 'Save & Submit'}
            </button>
            <button
              onClick={() => setShowPDFModal(true)}
              className="btn btn-secondary btn-sm w-full text-xs py-2"
            >
              <FileText size={14} className="mr-1" />
              Generate PDF
            </button>
          </div>
        </div>
        </div>
      </div>
      {/* Quotation PDF Modal */}
      {showPDFModal && (
        <QuotationPDFModal
          onClose={() => setShowPDFModal(false)}
          onSubmit={handleGeneratePDF}
          isSubmitting={isGeneratingPDF}
          title="Generate Quotation PDF"
          initialBankDetails={{
            bank_account_name: order?.customer.bank_account_name,
            bank_account_number: order?.customer.bank_account_number,
            bank_name: order?.customer.bank_name,
            bank_ifsc: order?.customer.bank_ifsc,
            bank_branch: order?.customer.bank_branch,
          }}
          initialTerms={order?.customer.terms_and_conditions}
        />
      )}
    </div>
  );
}
