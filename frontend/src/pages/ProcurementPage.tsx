import React, { useState, useEffect, useCallback } from 'react';
import {
  ShoppingBag, Plus, Trash2, ChevronDown, ChevronUp,
  PackageCheck, X, Search, Save, AlertCircle, Edit2,
} from 'lucide-react';
import api from '../services/api';

// ── Types ──────────────────────────────────────────────────────────────────────

interface InventoryItem {
  id: string;
  sku: string;
  description: string | null;
  stock_quantity: number;
  unit_price: number;
}

interface ProcurementItem {
  id: string;
  procurement_id: string;
  inventory_id: string;
  quantity: number;
  unit_price: number | null;
  notes: string | null;
  inventory_item: InventoryItem | null;
}

interface Procurement {
  id: string;
  procurement_number: string;
  status: 'ordered' | 'payment_done' | 'order_received';
  supplier_name: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  items: ProcurementItem[];
}

// ── Constants ──────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  ordered: 'Ordered',
  payment_done: 'Payment Done',
  order_received: 'Order Received',
};

const STATUS_COLORS: Record<string, string> = {
  ordered: 'bg-blue-100 text-blue-800',
  payment_done: 'bg-yellow-100 text-yellow-800',
  order_received: 'bg-green-100 text-green-800',
};

// ── Sub-components ─────────────────────────────────────────────────────────────

const StatusBadge = ({ status }: { status: string }) => (
  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${STATUS_COLORS[status] || 'bg-gray-100 text-gray-800'}`}>
    {STATUS_LABELS[status] || status}
  </span>
);

// ── Modal: Create Procurement ──────────────────────────────────────────────────

interface CreateModalProps {
  onClose: () => void;
  onCreated: (newId: string) => void;
}

const CreateProcurementModal: React.FC<CreateModalProps> = ({ onClose, onCreated }) => {
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    setSaving(true);
    setError(null);
    try {
      const result = await api.createProcurement({
        notes: notes || null,
        items: [],
      });
      onClose();
      onCreated(result.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create procurement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">New Procurement</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          A procurement number and date will be auto-generated.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            className="input"
            rows={3}
            placeholder="Optional notes..."
            value={notes}
            onChange={e => setNotes(e.target.value)}
          />
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn btn-secondary">Cancel</button>
          <button onClick={handleCreate} disabled={saving} className="btn btn-primary flex items-center gap-2">
            {saving ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> : <Plus size={16} />}
            Create
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Modal: Manage Items (two-pane, handles add + update + remove) ─────────────

type SelectedEntry = { qty: number; procItemId?: string };

interface ManageItemsModalProps {
  procurementId: string;
  existingItems: ProcurementItem[];
  onClose: () => void;
  onSaved: () => void;
}

const ManageItemsModal: React.FC<ManageItemsModalProps> = ({ procurementId, existingItems, onClose, onSaved }) => {
  const [search, setSearch] = useState('');
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [filtered, setFiltered] = useState<InventoryItem[]>([]);
  const [selected, setSelected] = useState<Record<string, SelectedEntry>>(() => {
    const init: Record<string, SelectedEntry> = {};
    existingItems.forEach(item => {
      init[item.inventory_id] = { qty: item.quantity, procItemId: item.id };
    });
    return init;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingInventory, setLoadingInventory] = useState(true);

  useEffect(() => {
    api.getInventory({ limit: 1000, is_active: true })
      .then((data: any) => {
        const items: InventoryItem[] = Array.isArray(data) ? data : (data.items || data.data || []);
        setInventoryItems(items);
        setFiltered(items);
      })
      .catch(() => setInventoryItems([]))
      .finally(() => setLoadingInventory(false));
  }, []);

  useEffect(() => {
    const term = search.toLowerCase().trim();
    setFiltered(
      term
        ? inventoryItems.filter(i =>
            i.sku.toLowerCase().includes(term) ||
            (i.description || '').toLowerCase().includes(term)
          )
        : inventoryItems
    );
  }, [search, inventoryItems]);

  const toggleLeft = (item: InventoryItem) => {
    setSelected(prev => {
      if (prev[item.id] !== undefined) {
        const next = { ...prev };
        delete next[item.id];
        return next;
      }
      return { ...prev, [item.id]: { qty: 1 } };
    });
  };

  const setQty = (invId: string, qty: number) => {
    setSelected(prev => ({
      ...prev,
      [invId]: { ...prev[invId], qty: Math.max(1, qty || 1) },
    }));
  };

  const removeRight = (invId: string) => {
    setSelected(prev => {
      const next = { ...prev };
      delete next[invId];
      return next;
    });
  };

  const invMap = Object.fromEntries(inventoryItems.map(i => [i.id, i]));
  const selectedEntries = Object.entries(selected);
  const selectedCount = selectedEntries.length;
  const hasChanges = selectedCount > 0 || existingItems.length > 0;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const origMap: Record<string, ProcurementItem> = {};
      existingItems.forEach(i => { origMap[i.inventory_id] = i; });

      const toRemove = existingItems.filter(i => selected[i.inventory_id] === undefined);
      const toAdd = selectedEntries.filter(([invId]) => !origMap[invId]);
      const toUpdate = selectedEntries.filter(([invId, entry]) => {
        const orig = origMap[invId];
        return orig && entry.qty !== orig.quantity;
      });

      await Promise.all([
        ...toRemove.map(i => api.removeProcurementItem(procurementId, i.id)),
        ...toAdd.map(([invId, entry]) =>
          api.addProcurementItem(procurementId, { inventory_id: invId, quantity: entry.qty, unit_price: null })
        ),
        ...toUpdate.map(([invId, entry]) => {
          const orig = origMap[invId];
          return api.updateProcurementItem(procurementId, orig.id, { quantity: entry.qty });
        }),
      ]);

      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save items');
    } finally {
      setSaving(false);
    }
  };

  const isEditing = existingItems.length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl flex flex-col" style={{ maxHeight: '90vh' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-2 flex-shrink-0 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              {isEditing ? 'Edit Items' : 'Add Items'}
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">Search and select items on the left • Adjust quantities on the right</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        {error && (
          <div className="mx-6 mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-1">
            <AlertCircle size={12} /> {error}
          </div>
        )}

        {/* Two-pane body */}
        <div className="flex flex-1 min-h-0">
          {/* Left pane: search + browse */}
          <div className="w-3/5 flex flex-col border-r border-gray-100">
            <div className="px-4 pt-3 pb-2 flex-shrink-0">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  autoFocus
                  type="text"
                  className="input pl-9 text-sm"
                  placeholder="Search by catalog no. or description..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loadingInventory ? (
                <div className="text-center py-10 text-sm text-gray-400">Loading inventory...</div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-10 text-sm text-gray-400">No items found</div>
              ) : (
                filtered.map(item => {
                  const isSelected = selected[item.id] !== undefined;
                  return (
                    <div
                      key={item.id}
                      onClick={() => toggleLeft(item)}
                      className={`flex items-center gap-3 px-4 py-2.5 border-b border-gray-50 cursor-pointer transition-colors ${
                        isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-gray-900">{item.sku}</div>
                        {item.description && <div className="text-xs text-gray-500 truncate">{item.description}</div>}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right pane: selected items with qty controls */}
          <div className="w-2/5 flex flex-col">
            <div className="px-4 pt-3 pb-2 flex-shrink-0 border-b border-gray-100">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Selected ({selectedCount})
              </span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {selectedCount === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-300 text-sm gap-2 pb-8">
                  <Search size={32} />
                  <span>Select items from the left</span>
                </div>
              ) : (
                selectedEntries.map(([invId, entry]) => {
                  const inv = invMap[invId];
                  const isExisting = !!entry.procItemId;
                  return (
                    <div key={invId} className="flex items-center gap-2 px-3 py-2.5 border-b border-gray-50">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-gray-900 truncate">
                          {inv?.sku || invId.slice(0, 8)}
                        </div>
                        {isExisting && (
                          <div className="text-xs text-blue-500">existing</div>
                        )}
                      </div>
                      {/* Stepper */}
                      <div className="flex items-center gap-1 flex-shrink-0" onClick={e => e.stopPropagation()}>
                        <button
                          type="button"
                          className="w-6 h-6 rounded border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100 text-sm font-bold"
                          onClick={() => setQty(invId, entry.qty - 1)}
                        >−</button>
                        <input
                          type="number"
                          min={1}
                          className="w-12 text-center border border-gray-300 rounded px-1 py-0.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-400"
                          value={entry.qty}
                          onChange={e => setQty(invId, parseInt(e.target.value))}
                        />
                        <button
                          type="button"
                          className="w-6 h-6 rounded border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100 text-sm font-bold"
                          onClick={() => setQty(invId, entry.qty + 1)}
                        >+</button>
                      </div>
                      <button
                        onClick={() => removeRight(invId)}
                        className="text-gray-300 hover:text-red-500 transition-colors flex-shrink-0"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 border-t border-gray-200 px-6 py-3 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            {selectedCount === 0 ? 'No items selected' : `${selectedCount} item${selectedCount !== 1 ? 's' : ''}`}
          </span>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="btn btn-primary flex items-center gap-2"
            >
              {saving ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> : <Save size={15} />}
              {isEditing ? 'Save Changes' : `Add ${selectedCount > 0 ? selectedCount + ' ' : ''}Item${selectedCount !== 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Modal: Receive Order ───────────────────────────────────────────────────────

interface ReceiveModalProps {
  procurement: Procurement;
  onClose: () => void;
  onReceived: () => void;
}

const ReceiveOrderModal: React.FC<ReceiveModalProps> = ({ procurement, onClose, onReceived }) => {
  const [mode, setMode] = useState<'direct' | 'edit' | null>(null);
  const [adjustments, setAdjustments] = useState<Record<string, number>>(() => {
    const map: Record<string, number> = {};
    procurement.items.forEach(i => { map[i.id] = i.quantity; });
    return map;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleReceive = async (useAdjustments: boolean) => {
    setSaving(true);
    setError(null);
    try {
      const payload = useAdjustments
        ? { adjustments: Object.entries(adjustments).map(([id, qty]) => ({ procurement_item_id: id, quantity: qty })) }
        : { adjustments: null };
      await api.receiveProcurement(procurement.id, payload);
      onReceived();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to receive order');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">Receive Order — {procurement.procurement_number}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {mode === null && (
          <>
            <p className="text-sm text-gray-600 mb-6">Choose how to add received items to inventory:</p>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleReceive(false)}
                disabled={saving}
                className="flex flex-col items-center gap-3 p-5 border-2 border-green-300 rounded-xl hover:bg-green-50 transition-colors text-left"
              >
                <PackageCheck size={32} className="text-green-600" />
                <div>
                  <div className="font-semibold text-gray-900 text-sm">Add to Inventory</div>
                  <div className="text-xs text-gray-500 mt-1">Add original quantities directly to stock</div>
                </div>
              </button>
              <button
                onClick={() => setMode('edit')}
                disabled={saving}
                className="flex flex-col items-center gap-3 p-5 border-2 border-blue-300 rounded-xl hover:bg-blue-50 transition-colors text-left"
              >
                <Edit2 size={32} className="text-blue-600" />
                <div>
                  <div className="font-semibold text-gray-900 text-sm">Edit Before Adding</div>
                  <div className="text-xs text-gray-500 mt-1">Adjust quantities before adding to stock</div>
                </div>
              </button>
            </div>
          </>
        )}

        {mode === 'edit' && (
          <>
            <p className="text-sm text-gray-600 mb-4">Adjust received quantities for each item:</p>
            <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
              {procurement.items.map(item => (
                <div key={item.id} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{item.inventory_item?.sku || '—'}</div>
                    <div className="text-xs text-gray-500 truncate">{item.inventory_item?.description || ''}</div>
                    <div className="text-xs text-gray-400">Ordered: {item.quantity}</div>
                  </div>
                  <div className="w-24 flex-shrink-0">
                    <input
                      type="number"
                      min={0}
                      className="input text-center"
                      value={adjustments[item.id] ?? item.quantity}
                      onChange={e => setAdjustments(prev => ({ ...prev, [item.id]: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setMode(null)} className="btn btn-secondary">Back</button>
              <button
                onClick={() => handleReceive(true)}
                disabled={saving}
                className="btn btn-primary flex items-center gap-2"
              >
                {saving ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> : <Save size={16} />}
                Confirm & Add to Inventory
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ── Procurement Card ───────────────────────────────────────────────────────────

interface ProcurementCardProps {
  procurement: Procurement;
  onRefresh: () => void;
}

const ProcurementCard: React.FC<ProcurementCardProps> = ({ procurement, onRefresh }) => {
  const [expanded, setExpanded] = useState(false);
  const [showManageItems, setShowManageItems] = useState(false);
  const [showReceive, setShowReceive] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMarkPaymentDone = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await api.markProcurementPaymentDone(procurement.id);
      onRefresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update status');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteProcurement = async () => {
    if (!confirm(`Delete ${procurement.procurement_number}? This cannot be undone.`)) return;
    setActionLoading(true);
    try {
      await api.deleteProcurement(procurement.id);
      onRefresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete procurement');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-gray-900">{procurement.procurement_number}</span>
              <StatusBadge status={procurement.status} />
            </div>
            {procurement.notes && (
              <div className="text-xs text-gray-400 mt-0.5 truncate">{procurement.notes}</div>
            )}
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              <span>{procurement.items.length} item{procurement.items.length !== 1 ? 's' : ''}</span>
              {procurement.created_at && (
                <span>{new Date(procurement.created_at).toLocaleDateString('en-IN')}</span>
              )}
            </div>
          </div>

          {/* Labeled action buttons */}
          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
            {procurement.status === 'ordered' && (
              <>
                <button
                  onClick={() => setShowManageItems(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <Plus size={13} />
                  {procurement.items.length === 0 ? 'Add Items' : 'Edit Items'}
                </button>
                <button
                  onClick={handleMarkPaymentDone}
                  disabled={actionLoading || procurement.items.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Payment Done
                </button>
                <button
                  onClick={handleDeleteProcurement}
                  disabled={actionLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <Trash2 size={13} /> Delete
                </button>
              </>
            )}
            {procurement.status === 'payment_done' && (
              <button
                onClick={() => setShowReceive(true)}
                disabled={actionLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
              >
                <PackageCheck size={13} /> Order Received
              </button>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1.5 text-gray-400 hover:bg-gray-100 rounded transition-colors"
              title={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-1">
            <AlertCircle size={12} /> {error}
          </div>
        )}
      </div>

      {/* Expanded items table */}
      {expanded && (
        <div className="border-t border-gray-100">
          {procurement.items.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-gray-400">
              No items.{' '}
              {procurement.status === 'ordered' && (
                <button onClick={() => setShowManageItems(true)} className="text-blue-600 hover:underline font-medium">Add items</button>
              )}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-4 py-2 font-medium text-gray-500 text-xs">Catalog No.</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-500 text-xs">Description</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-500 text-xs">Qty</th>
                </tr>
              </thead>
              <tbody>
                {procurement.items.map(item => (
                  <tr key={item.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-2 font-semibold text-gray-900">{item.inventory_item?.sku || '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{item.inventory_item?.description || '—'}</td>
                    <td className="px-4 py-2 text-right font-bold text-gray-800">{item.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {showManageItems && (
        <ManageItemsModal
          procurementId={procurement.id}
          existingItems={procurement.items}
          onClose={() => setShowManageItems(false)}
          onSaved={() => { setShowManageItems(false); onRefresh(); }}
        />
      )}
      {showReceive && (
        <ReceiveOrderModal
          procurement={procurement}
          onClose={() => setShowReceive(false)}
          onReceived={() => { setShowReceive(false); onRefresh(); }}
        />
      )}
    </div>
  );
};

// ── Main Page ──────────────────────────────────────────────────────────────────

const ProcurementPage: React.FC = () => {
  const [procurements, setProcurements] = useState<Procurement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  // Auto-open ManageItemsModal after creation
  const [autoManageId, setAutoManageId] = useState<string | null>(null);

  const fetchProcurements = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getProcurements(statusFilter !== 'all' ? statusFilter : undefined);
      setProcurements(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load procurements');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchProcurements(); }, [fetchProcurements]);

  const handleCreated = useCallback(async (newId: string) => {
    await fetchProcurements();
    setAutoManageId(newId);
  }, [fetchProcurements]);

  const counts = {
    all: procurements.length,
    ordered: procurements.filter(p => p.status === 'ordered').length,
    payment_done: procurements.filter(p => p.status === 'payment_done').length,
    order_received: procurements.filter(p => p.status === 'order_received').length,
  };

  const filtered = statusFilter === 'all'
    ? procurements
    : procurements.filter(p => p.status === statusFilter);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <ShoppingBag className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Procurement</h1>
              <p className="text-sm text-gray-500">Manage supplier item orders</p>
            </div>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> New Procurement
          </button>
        </div>

        <div className="flex gap-1 mt-4 border-b border-gray-200">
          {[
            { key: 'all', label: 'All' },
            { key: 'ordered', label: 'Ordered' },
            { key: 'payment_done', label: 'Payment Done' },
            { key: 'order_received', label: 'Received' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
                statusFilter === tab.key
                  ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              <span className={`ml-1.5 px-1.5 py-0.5 text-xs rounded-full ${
                statusFilter === tab.key ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {counts[tab.key as keyof typeof counts]}
              </span>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
        </div>
      ) : error ? (
        <div className="card p-4 bg-red-50 border border-red-200 text-red-800 flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center">
          <ShoppingBag className="mx-auto w-12 h-12 text-gray-300 mb-3" />
          <p className="text-gray-500">
            {statusFilter === 'all' ? 'No procurements yet.' : `No procurements in "${STATUS_LABELS[statusFilter]}" state.`}
          </p>
          {statusFilter === 'all' && (
            <button onClick={() => setShowCreate(true)} className="btn btn-primary mt-4 inline-flex items-center gap-2">
              <Plus size={16} /> Create First Procurement
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(p => (
            <ProcurementCard key={p.id} procurement={p} onRefresh={fetchProcurements} />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateProcurementModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {/* Auto-open manage items after creation */}
      {autoManageId && (() => {
        const proc = procurements.find(p => p.id === autoManageId);
        if (!proc) return null;
        return (
          <ManageItemsModal
            procurementId={proc.id}
            existingItems={proc.items}
            onClose={() => setAutoManageId(null)}
            onSaved={() => { setAutoManageId(null); fetchProcurements(); }}
          />
        );
      })()}
    </div>
  );
};

export default ProcurementPage;
