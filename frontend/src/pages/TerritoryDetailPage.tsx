/**
 * Territory detail page — assign/unassign multiple customers to a territory.
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Customer, Territory } from '@/types';
import { ArrowLeft, Search, MapPin, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

function useDebounced(value: string, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function CustomerCheckList({
  customers,
  isLoading,
  selected,
  onToggle,
  emptyMessage,
}: {
  customers: Customer[];
  isLoading: boolean;
  selected: Set<string>;
  onToggle: (id: string) => void;
  emptyMessage: string;
}) {
  return (
    <div className="border rounded-lg divide-y max-h-[420px] overflow-auto bg-white">
      {isLoading ? (
        <div className="p-4 text-sm text-gray-500">Loading…</div>
      ) : customers.length === 0 ? (
        <div className="p-4 text-sm text-gray-500">{emptyMessage}</div>
      ) : (
        customers.map((c) => (
          <label
            key={c.id}
            className="flex items-center gap-3 px-3 py-2 text-sm hover:bg-gray-50 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.has(c.id)}
              onChange={() => onToggle(c.id)}
              className="h-4 w-4"
            />
            <div className="min-w-0">
              <div className="font-medium text-gray-900 truncate">{c.hospital_name}</div>
              <div className="text-gray-500 truncate">
                {[c.contact_person, c.city].filter(Boolean).join(' • ') || '—'}
              </div>
            </div>
          </label>
        ))
      )}
    </div>
  );
}

export default function TerritoryDetailPage() {
  const { territoryId } = useParams<{ territoryId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [assignedSearch, setAssignedSearch] = useState('');
  const [addSearch, setAddSearch] = useState('');
  const debouncedAssignedSearch = useDebounced(assignedSearch);
  const debouncedAddSearch = useDebounced(addSearch);

  const [selectedAssigned, setSelectedAssigned] = useState<Set<string>>(new Set());
  const [selectedToAdd, setSelectedToAdd] = useState<Set<string>>(new Set());

  const canUpdate = user?.role?.permissions?.['territory:update'] === true;

  const { data: territory, isLoading: territoryLoading } = useQuery<Territory>({
    queryKey: ['territory', territoryId],
    queryFn: () => api.getTerritory(territoryId!),
    enabled: !!territoryId,
  });

  const { data: assignedCustomers, isLoading: assignedLoading } = useQuery<Customer[]>({
    queryKey: ['territory-customers', territoryId, debouncedAssignedSearch],
    queryFn: () => api.getTerritoryCustomers(territoryId!, { search: debouncedAssignedSearch || undefined, limit: 200 }),
    enabled: !!territoryId,
  });

  const { data: unassignedCustomers, isLoading: addLoading } = useQuery<Customer[]>({
    queryKey: ['customers', 'unassigned', debouncedAddSearch],
    queryFn: () => api.getCustomers({ territory_id: 'none', search: debouncedAddSearch || undefined, limit: 100 }),
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['territories'] });
    queryClient.invalidateQueries({ queryKey: ['territory', territoryId] });
    queryClient.invalidateQueries({ queryKey: ['territory-customers', territoryId] });
    queryClient.invalidateQueries({ queryKey: ['customers'] });
  };

  const addMutation = useMutation({
    mutationFn: (ids: string[]) => api.addCustomersToTerritory(territoryId!, ids),
    onSuccess: () => {
      setSelectedToAdd(new Set());
      invalidateAll();
    },
  });

  const removeMutation = useMutation({
    mutationFn: (ids: string[]) => api.removeCustomersFromTerritory(territoryId!, ids),
    onSuccess: () => {
      setSelectedAssigned(new Set());
      invalidateAll();
    },
  });

  const toggle = (set: Set<string>, setter: (s: Set<string>) => void, id: string) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setter(next);
  };

  if (territoryLoading) {
    return <div className="p-6 text-gray-500">Loading territory…</div>;
  }

  if (!territory) {
    return <div className="p-6 text-gray-500">Territory not found.</div>;
  }

  return (
    <div className="w-full">
      <div className="flex items-center gap-3 mb-4 bg-white p-4 rounded-lg shadow-sm">
        <button
          onClick={() => navigate('/territories')}
          className="btn btn-secondary btn-sm flex items-center"
        >
          <ArrowLeft size={16} className="mr-1" />
          Back
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">{territory.name}</h1>
          <div className="flex items-center gap-4 text-sm text-gray-500 mt-0.5">
            <span className="flex items-center gap-1">
              <MapPin size={13} /> {territory.city || '—'}
            </span>
            <span className="flex items-center gap-1">
              <UserIcon size={13} /> {territory.sales_person_name || 'Unassigned'}
            </span>
            <span>{territory.customer_count} customer{territory.customer_count === 1 ? '' : 's'}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Assigned customers */}
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Assigned Customers</h2>
            {canUpdate && (
              <button
                onClick={() => removeMutation.mutate(Array.from(selectedAssigned))}
                disabled={selectedAssigned.size === 0 || removeMutation.isPending}
                className="btn btn-danger btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Remove Selected ({selectedAssigned.size})
              </button>
            )}
          </div>
          <div className="relative mb-3">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={assignedSearch}
              onChange={(e) => setAssignedSearch(e.target.value)}
              placeholder="Search assigned customers…"
              className="input input-md pl-9 w-full"
            />
          </div>
          <CustomerCheckList
            customers={assignedCustomers || []}
            isLoading={assignedLoading}
            selected={selectedAssigned}
            onToggle={(id) => toggle(selectedAssigned, setSelectedAssigned, id)}
            emptyMessage="No customers assigned to this territory yet."
          />
        </div>

        {/* Add customers */}
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Add Customers</h2>
            {canUpdate && (
              <button
                onClick={() => addMutation.mutate(Array.from(selectedToAdd))}
                disabled={selectedToAdd.size === 0 || addMutation.isPending}
                className="btn btn-primary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Selected ({selectedToAdd.size})
              </button>
            )}
          </div>
          <div className="relative mb-3">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={addSearch}
              onChange={(e) => setAddSearch(e.target.value)}
              placeholder="Search unassigned customers…"
              className="input input-md pl-9 w-full"
            />
          </div>
          <CustomerCheckList
            customers={unassignedCustomers || []}
            isLoading={addLoading}
            selected={selectedToAdd}
            onToggle={(id) => toggle(selectedToAdd, setSelectedToAdd, id)}
            emptyMessage="No unassigned customers found."
          />
        </div>
      </div>
    </div>
  );
}
