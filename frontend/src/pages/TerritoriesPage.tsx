/**
 * Territories page for managing hospital groupings and their assigned sales person.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { Territory, User } from '@/types';
import { Plus, Search, X, Users as UsersIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column, Action, commonActions } from '@/components/common/DataTable';

export default function TerritoriesPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingTerritory, setEditingTerritory] = useState<Territory | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 350);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const { data: territories, isLoading } = useQuery<Territory[]>({
    queryKey: ['territories', debouncedSearch],
    queryFn: () => api.getTerritories({ search: debouncedSearch || undefined }),
  });

  const { data: salesReps } = useQuery<User[]>({
    queryKey: ['employees', 'sales_rep'],
    queryFn: () => api.getEmployees({ role: 'sales_rep' }),
  });

  const createMutation = useMutation({
    mutationFn: api.createTerritory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['territories'] });
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.updateTerritory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['territories'] });
      setShowForm(false);
      setEditingTerritory(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteTerritory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['territories'] });
    },
  });

  const canCreate = user?.role?.permissions?.['territory:create'] === true;
  const canUpdate = user?.role?.permissions?.['territory:update'] === true;
  const canDelete = user?.role?.permissions?.['territory:delete'] === true;

  const territoryFields: FormField[] = [
    {
      name: 'name',
      label: 'Territory Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., North Chennai',
    },
    {
      name: 'city',
      label: 'City',
      type: 'text',
      placeholder: 'Enter city',
    },
    {
      name: 'sales_person_id',
      label: 'Sales Person',
      type: 'select',
      options: (salesReps || []).map((rep) => ({ value: rep.id, label: rep.name || rep.full_name || rep.email })),
    },
  ];

  const handleSubmit = async (data: Record<string, any>) => {
    const payload = {
      ...data,
      sales_person_id: data.sales_person_id || null,
    };
    if (editingTerritory) {
      // Explicitly signal clearing the sales person when the field is left blank.
      await updateMutation.mutateAsync({
        id: editingTerritory.id,
        data: { ...payload, clear_sales_person: !payload.sales_person_id },
      });
    } else {
      await createMutation.mutateAsync(payload);
    }
  };

  const handleEdit = (territory: Territory) => {
    setEditingTerritory(territory);
    setShowForm(true);
  };

  const handleDelete = (territory: Territory) => {
    if (confirm(`Delete territory "${territory.name}"? Its customers will become unassigned.`)) {
      deleteMutation.mutate(territory.id);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingTerritory(null);
  };

  const columns: Column<Territory>[] = [
    {
      key: 'name',
      label: 'Territory Name',
      width: '30%',
      render: (v, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/territories/${row.id}`);
          }}
          className="text-primary-600 hover:text-primary-700 hover:underline font-medium text-left"
        >
          {v}
        </button>
      ),
    },
    { key: 'city', label: 'City', width: '20%', render: (v) => v || '—' },
    { key: 'sales_person_name', label: 'Sales Person', width: '25%', render: (v) => v || 'Unassigned' },
    { key: 'customer_count', label: 'Customers', width: '15%' },
  ];

  const actions: Action<Territory>[] = [
    {
      label: 'Manage Customers',
      icon: <UsersIcon size={16} />,
      onClick: (t) => navigate(`/territories/${t.id}`),
      variant: 'secondary',
    },
    commonActions.edit(handleEdit, () => canUpdate),
    commonActions.delete(handleDelete, () => canDelete),
  ];

  return (
    <div className="w-full">
      <div className="flex items-center gap-3 mb-4 bg-white p-4 rounded-lg shadow-sm">
        <h1 className="text-xl font-bold text-gray-900 whitespace-nowrap">Territories</h1>

        <div className="relative flex-1">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search territory name or city…"
            className="input input-md pl-9 w-full"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {canCreate && (
          <button
            onClick={() => setShowForm(true)}
            className="btn btn-primary btn-sm flex items-center whitespace-nowrap"
          >
            <Plus size={16} className="mr-1" />
            Add Territory
          </button>
        )}
      </div>

      <div className="w-full overflow-auto max-h-[calc(100vh-260px)]">
        <DataTable
          data={territories || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No territories found. Add your first territory to get started."
          showAuditInfo={false}
          onRowClick={(t) => navigate(`/territories/${t.id}`)}
          actions={actions}
        />
      </div>

      {showForm && (
        <DynamicForm
          title="Territory"
          fields={territoryFields}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          submitLabel={editingTerritory ? 'Update Territory' : 'Create Territory'}
          initialData={editingTerritory || {}}
          isEdit={!!editingTerritory}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  );
}
