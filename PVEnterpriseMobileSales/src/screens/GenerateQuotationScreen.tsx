/**
 * Generate Quotation Screen — executive-only direct quotation flow.
 *
 * Lets an executive pick a customer, add priced inventory items, and submit.
 * The backend creates the order and a finalized, already-approved quotation
 * for it in one step (see POST /orders/quotation-direct).
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { useAppSelector } from '@/hooks/redux';
import apiService from '@/services/api';
import { showSuccessToast, showErrorToast } from '@/utils/toast';
import { Customer, Inventory, PriceList, PriceListItem, DirectQuotationRequest } from '@/types';

interface QuotationLineItem {
  key: string;
  inventory: Inventory;
  description: string;
  quantity: string;
  unitPrice: string;
  gstPercentage: string;
}

const todayIso = () => new Date().toISOString().split('T')[0];

const formatINR = (amount: number) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);

const GenerateQuotationScreen: React.FC = () => {
  const navigation = useNavigation();
  const { user } = useAppSelector(state => state.auth);

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filteredCustomers, setFilteredCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [customerSearch, setCustomerSearch] = useState('');
  const [showCustomerPicker, setShowCustomerPicker] = useState(false);

  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [selectedPriceListId, setSelectedPriceListId] = useState<string>('');
  const [priceListItems, setPriceListItems] = useState<PriceListItem[]>([]);
  const [showPriceListPicker, setShowPriceListPicker] = useState(false);

  const [subject, setSubject] = useState('');
  const [quotationDate, setQuotationDate] = useState(todayIso());
  const [discountPercent, setDiscountPercent] = useState('0');

  const [items, setItems] = useState<QuotationLineItem[]>([]);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Inventory[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);

  const [submitting, setSubmitting] = useState(false);

  const canAccess = user?.role_name === 'executive';

  useEffect(() => {
    if (!canAccess) return;
    (async () => {
      try {
        const [customerList, priceListList] = await Promise.all([
          apiService.getCustomers(),
          apiService.getPriceLists(),
        ]);
        setCustomers(customerList);
        setFilteredCustomers(customerList);
        setPriceLists(priceListList);
      } catch (error) {
        console.error('Failed to load quotation setup data:', error);
        showErrorToast('Failed to load customers / price lists');
      }
    })();
  }, [canAccess]);

  useEffect(() => {
    if (!selectedPriceListId) {
      setPriceListItems([]);
      return;
    }
    apiService.getPriceListItems(selectedPriceListId)
      .then(setPriceListItems)
      .catch((error) => {
        console.error('Failed to load price list items:', error);
        setPriceListItems([]);
      });
  }, [selectedPriceListId]);

  useEffect(() => {
    if (!catalogSearch.trim()) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    setSearching(true);
    const debounce = setTimeout(async () => {
      try {
        const results = await apiService.searchInventory(catalogSearch.trim());
        setSearchResults(results);
        setShowDropdown(true);
      } catch (error) {
        console.error('Inventory search failed:', error);
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(debounce);
  }, [catalogSearch]);

  const handleCustomerSearch = (text: string) => {
    setCustomerSearch(text);
    if (!text.trim()) {
      setFilteredCustomers(customers);
    } else {
      const t = text.toLowerCase();
      setFilteredCustomers(customers.filter(c =>
        (c.name || c.hospital_name || '').toLowerCase().includes(t) ||
        (c.city || '').toLowerCase().includes(t)
      ));
    }
  };

  const defaultPriceFor = (inv: Inventory) => {
    const pli = priceListItems.find(p => p.inventory_id === inv.id);
    return {
      unitPrice: pli ? String(pli.unit_price) : String(inv.unit_price ?? 0),
      gstPercentage: pli?.tax_percentage != null ? String(pli.tax_percentage) : String(inv.tax ?? 5),
    };
  };

  const addItem = (inv: Inventory) => {
    const { unitPrice, gstPercentage } = defaultPriceFor(inv);
    setItems(prev => [
      ...prev,
      {
        key: `${inv.id}-${Date.now()}`,
        inventory: inv,
        description: inv.description || inv.sku,
        quantity: '1',
        unitPrice,
        gstPercentage,
      },
    ]);
    setCatalogSearch('');
    setSearchResults([]);
    setShowDropdown(false);
  };

  const updateItem = (key: string, patch: Partial<QuotationLineItem>) => {
    setItems(prev => prev.map(it => (it.key === key ? { ...it, ...patch } : it)));
  };

  const removeItem = (key: string) => {
    setItems(prev => prev.filter(it => it.key !== key));
  };

  const parsedItems = items.map(it => {
    const quantity = Math.max(1, parseInt(it.quantity, 10) || 0);
    const unitPrice = Math.max(0, parseFloat(it.unitPrice) || 0);
    const gstPercentage = Math.max(0, parseFloat(it.gstPercentage) || 0);
    const grossAmount = unitPrice * quantity;
    return { ...it, quantity, unitPrice, gstPercentage, grossAmount };
  });

  const discountPct = Math.max(0, Math.min(100, parseFloat(discountPercent) || 0));
  const subTotal = parsedItems.reduce((sum, it) => sum + it.grossAmount, 0);
  const discountAmount = (subTotal * discountPct) / 100;
  const taxAmount = parsedItems.reduce((sum, it) => {
    const amountAfterDiscount = it.grossAmount - (it.grossAmount * discountPct) / 100;
    return sum + (amountAfterDiscount * it.gstPercentage) / 100;
  }, 0);
  const grandTotal = Math.round(subTotal - discountAmount + taxAmount);

  const handleSubmit = async () => {
    if (!selectedCustomer) {
      showErrorToast('Please select a customer');
      return;
    }
    if (parsedItems.length === 0) {
      showErrorToast('Add at least one item');
      return;
    }
    const invalidItem = parsedItems.find(it => it.quantity <= 0 || it.unitPrice < 0);
    if (invalidItem) {
      showErrorToast('Check item quantities and prices');
      return;
    }

    setSubmitting(true);
    try {
      const payload: DirectQuotationRequest = {
        customer_id: selectedCustomer.id,
        items: parsedItems.map(it => ({
          inventory_id: it.inventory.id,
          quantity: it.quantity,
          unit_price: it.unitPrice,
          gst_percentage: it.gstPercentage,
          item_description: it.description,
        })),
        price_list_id: selectedPriceListId || null,
        discount_percentage: discountPct,
        subject: subject || undefined,
        quotation_date: quotationDate || undefined,
      };

      const newOrder = await apiService.createDirectQuotation(payload);
      showSuccessToast(
        newOrder.quotation_number
          ? `Quotation #${newOrder.quotation_number} generated successfully!`
          : 'Quotation generated successfully!'
      );
      navigation.goBack();
      navigation.navigate('OrderDetails' as never, { orderId: newOrder.id } as never);
    } catch (error: any) {
      console.error('Failed to generate quotation:', error);
      showErrorToast(error.response?.data?.detail || 'Failed to generate quotation');
    } finally {
      setSubmitting(false);
    }
  };

  if (!canAccess) {
    return (
      <View style={styles.deniedContainer}>
        <Icon name="lock" size={48} color="#d1d5db" />
        <Text style={styles.deniedText}>Only executives can generate quotations directly.</Text>
      </View>
    );
  }

  const selectedPriceListName = selectedPriceListId
    ? priceLists.find(p => p.id === selectedPriceListId)?.name
    : 'Standard Prices';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Customer */}
      <View style={styles.section}>
        <Text style={styles.label}>Customer *</Text>
        {!selectedCustomer ? (
          <>
            <TextInput
              style={styles.input}
              placeholder="Search customers..."
              value={customerSearch}
              onChangeText={handleCustomerSearch}
              onFocus={() => setShowCustomerPicker(true)}
            />
            {showCustomerPicker && filteredCustomers.length > 0 && (
              <View style={styles.dropdownList}>
                {filteredCustomers.map((customer) => (
                  <TouchableOpacity
                    key={customer.id}
                    style={styles.dropdownItem}
                    onPress={() => {
                      setSelectedCustomer(customer);
                      setCustomerSearch(customer.name || customer.hospital_name || '');
                      setShowCustomerPicker(false);
                    }}
                  >
                    <Text style={styles.dropdownItemTitle}>{customer.name || customer.hospital_name}</Text>
                    {customer.city && <Text style={styles.dropdownItemSubtitle}>{customer.city}</Text>}
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </>
        ) : (
          <View style={styles.selectedRow}>
            <View style={styles.flex1}>
              <Text style={styles.selectedTitle}>{selectedCustomer.name || selectedCustomer.hospital_name}</Text>
              {selectedCustomer.city && <Text style={styles.selectedSubtitle}>{selectedCustomer.city}</Text>}
            </View>
            <TouchableOpacity
              onPress={() => { setSelectedCustomer(null); setCustomerSearch(''); }}
              style={styles.changeButton}
            >
              <Icon name="edit" size={18} color="#2563eb" />
              <Text style={styles.changeButtonText}>Change</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Price list */}
      <View style={styles.section}>
        <Text style={styles.label}>Price List</Text>
        <TouchableOpacity style={styles.input} onPress={() => setShowPriceListPicker(!showPriceListPicker)}>
          <Text>{selectedPriceListName}</Text>
        </TouchableOpacity>
        {showPriceListPicker && (
          <View style={styles.dropdownList}>
            <TouchableOpacity
              style={styles.dropdownItem}
              onPress={() => { setSelectedPriceListId(''); setShowPriceListPicker(false); }}
            >
              <Text style={styles.dropdownItemTitle}>Standard Prices</Text>
            </TouchableOpacity>
            {priceLists.map((pl) => (
              <TouchableOpacity
                key={pl.id}
                style={styles.dropdownItem}
                onPress={() => { setSelectedPriceListId(pl.id); setShowPriceListPicker(false); }}
              >
                <Text style={styles.dropdownItemTitle}>{pl.name}{pl.is_default ? ' (Default)' : ''}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      {/* Subject + Date + Discount */}
      <View style={styles.section}>
        <Text style={styles.label}>Subject</Text>
        <TextInput style={styles.input} placeholder="Optional subject" value={subject} onChangeText={setSubject} />
      </View>
      <View style={styles.row}>
        <View style={[styles.section, styles.flex1, { marginRight: 8 }]}>
          <Text style={styles.label}>Quotation Date</Text>
          <TextInput
            style={styles.input}
            placeholder="YYYY-MM-DD"
            value={quotationDate}
            onChangeText={setQuotationDate}
          />
        </View>
        <View style={[styles.section, styles.flex1]}>
          <Text style={styles.label}>Discount %</Text>
          <TextInput
            style={styles.input}
            keyboardType="decimal-pad"
            value={discountPercent}
            onChangeText={setDiscountPercent}
          />
        </View>
      </View>

      {/* Item search */}
      <View style={styles.section}>
        <Text style={styles.label}>Add Item</Text>
        <TextInput
          style={styles.input}
          placeholder="Search catalog no or description..."
          value={catalogSearch}
          onChangeText={setCatalogSearch}
        />
        {searching && <ActivityIndicator style={{ marginTop: 8 }} size="small" color="#2563eb" />}
        {showDropdown && searchResults.length > 0 && (
          <View style={styles.dropdownList}>
            {searchResults.map((inv) => (
              <TouchableOpacity key={inv.id} style={styles.dropdownItem} onPress={() => addItem(inv)}>
                <Text style={styles.dropdownItemTitle}>{inv.sku}</Text>
                <Text style={styles.dropdownItemSubtitle} numberOfLines={1}>{inv.description}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      {/* Items list */}
      <View style={styles.section}>
        <Text style={styles.label}>Items ({items.length})</Text>
        {items.length === 0 && <Text style={styles.emptyHint}>No items added yet</Text>}
        {parsedItems.map((it) => (
          <View key={it.key} style={styles.itemCard}>
            <View style={styles.itemCardHeader}>
              <Text style={styles.itemSku}>{it.inventory.sku}</Text>
              <TouchableOpacity onPress={() => removeItem(it.key)}>
                <Icon name="close" size={18} color="#ef4444" />
              </TouchableOpacity>
            </View>
            <TextInput
              style={styles.itemDescriptionInput}
              value={it.description}
              onChangeText={(v) => updateItem(it.key, { description: v })}
              placeholder="Description"
            />
            <View style={styles.itemFieldsRow}>
              <View style={styles.itemField}>
                <Text style={styles.itemFieldLabel}>Qty</Text>
                <TextInput
                  style={styles.itemFieldInput}
                  keyboardType="number-pad"
                  value={it.quantity}
                  onChangeText={(v) => updateItem(it.key, { quantity: v })}
                />
              </View>
              <View style={styles.itemField}>
                <Text style={styles.itemFieldLabel}>Price ₹</Text>
                <TextInput
                  style={styles.itemFieldInput}
                  keyboardType="decimal-pad"
                  value={it.unitPrice}
                  onChangeText={(v) => updateItem(it.key, { unitPrice: v })}
                />
              </View>
              <View style={styles.itemField}>
                <Text style={styles.itemFieldLabel}>Tax %</Text>
                <TextInput
                  style={styles.itemFieldInput}
                  keyboardType="decimal-pad"
                  value={it.gstPercentage}
                  onChangeText={(v) => updateItem(it.key, { gstPercentage: v })}
                />
              </View>
            </View>
            <Text style={styles.itemLineTotal}>Amount: ₹{formatINR(it.grossAmount)}</Text>
          </View>
        ))}
      </View>

      {/* Summary */}
      {items.length > 0 && (
        <View style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Sub Total</Text>
            <Text style={styles.summaryValue}>₹{formatINR(subTotal)}</Text>
          </View>
          {discountPct > 0 && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Discount ({discountPct}%)</Text>
              <Text style={styles.summaryValueNegative}>-₹{formatINR(discountAmount)}</Text>
            </View>
          )}
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Tax</Text>
            <Text style={styles.summaryValue}>₹{formatINR(taxAmount)}</Text>
          </View>
          <View style={[styles.summaryRow, styles.summaryTotalRow]}>
            <Text style={styles.summaryTotalLabel}>Grand Total</Text>
            <Text style={styles.summaryTotalValue}>₹{formatINR(grandTotal)}</Text>
          </View>
        </View>
      )}

      <TouchableOpacity
        style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
      >
        <Text style={styles.submitButtonText}>
          {submitting ? 'Generating…' : 'Generate Quotation'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 16, paddingBottom: 40 },
  section: { marginBottom: 20 },
  row: { flexDirection: 'row' },
  flex1: { flex: 1 },
  label: { fontSize: 16, fontWeight: '600', color: '#374151', marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: '#ffffff',
  },
  dropdownList: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    backgroundColor: '#ffffff',
    marginTop: 4,
    maxHeight: 220,
  },
  dropdownItem: { padding: 12, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  dropdownItemTitle: { fontSize: 15, color: '#1f2937', fontWeight: '500' },
  dropdownItemSubtitle: { fontSize: 13, color: '#6b7280', marginTop: 2 },
  selectedRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#10b981',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: '#f0fdf4',
  },
  selectedTitle: { fontSize: 16, color: '#1f2937', fontWeight: '600' },
  selectedSubtitle: { fontSize: 14, color: '#6b7280', marginTop: 2 },
  changeButton: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, paddingVertical: 4 },
  changeButtonText: { fontSize: 14, color: '#2563eb', fontWeight: '500', marginLeft: 4 },
  emptyHint: { fontSize: 14, color: '#9ca3af', fontStyle: 'italic' },
  itemCard: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  itemCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  itemSku: { fontSize: 14, fontWeight: '700', color: '#1f2937' },
  itemDescriptionInput: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 6,
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
  },
  itemFieldsRow: { flexDirection: 'row', justifyContent: 'space-between' },
  itemField: { flex: 1, marginRight: 8 },
  itemFieldLabel: { fontSize: 11, color: '#6b7280', marginBottom: 2 },
  itemFieldInput: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 6,
    fontSize: 14,
    color: '#1f2937',
  },
  itemLineTotal: { fontSize: 13, fontWeight: '600', color: '#374151', marginTop: 8, textAlign: 'right' },
  summaryCard: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  summaryLabel: { fontSize: 14, color: '#6b7280' },
  summaryValue: { fontSize: 14, fontWeight: '500', color: '#1f2937' },
  summaryValueNegative: { fontSize: 14, fontWeight: '500', color: '#ef4444' },
  summaryTotalRow: { borderTopWidth: 1, borderTopColor: '#e5e7eb', marginTop: 6, paddingTop: 10 },
  summaryTotalLabel: { fontSize: 16, fontWeight: '700', color: '#1f2937' },
  summaryTotalValue: { fontSize: 16, fontWeight: '700', color: '#2563eb' },
  submitButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
  },
  submitButtonDisabled: { backgroundColor: '#9ca3af' },
  submitButtonText: { color: '#ffffff', fontSize: 16, fontWeight: '600' },
  deniedContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, backgroundColor: '#f8fafc' },
  deniedText: { marginTop: 16, fontSize: 15, color: '#6b7280', textAlign: 'center' },
});

export default GenerateQuotationScreen;
