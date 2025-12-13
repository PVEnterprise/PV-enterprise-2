/**
 * Demos page for managing demo requests.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '@/services/api';
import { DemoRequest } from '@/types';
import { Plus, Search, Eye } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DemoRequestModal from '@/components/DemoRequestModal';
import DataTable, { Column, commonActions } from '@/components/common/DataTable';

export default function DemosPage() {
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState<string>('');
  const [showForm, setShowForm] = useState(false);
  const [editingDemo, setEditingDemo] = useState<DemoRequest | null>(null);
  const [formError, setFormError] = useState<string>('');
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: demoRequests, isLoading } = useQuery<DemoRequest[]>({
    queryKey: ['demo-requests', search, stateFilter],
    queryFn: () => api.getDemoRequests({ search, state: stateFilter || undefined }),
  });

  // Check permissions
  const canCreate = user?.role?.permissions?.['inventory:create'] === true;
  const canUpdate = user?.role?.permissions?.['inventory:update'] === true;
  const canDelete = user?.role?.permissions?.['inventory:delete'] === true;

  // Mutations
  const createMutation = useMutation({
    mutationFn: api.createDemoRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-requests'] });
      setShowForm(false);
      setEditingDemo(null);
      setFormError('');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create demo request';
      setFormError(errorMessage);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.updateDemoRequest(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-requests'] });
      setShowForm(false);
      setEditingDemo(null);
      setFormError('');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to update demo request';
      setFormError(errorMessage);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDemoRequest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-requests'] });
    },
  });

  const handleSubmit = async (data: Record<string, any>) => {
    if (editingDemo) {
      await updateMutation.mutateAsync({ id: editingDemo.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleEdit = (demo: DemoRequest) => {
    setEditingDemo(demo);
    setShowForm(true);
    setFormError('');
  };

  const handleDelete = (demo: DemoRequest) => {
    if (confirm(`Are you sure you want to delete demo request ${demo.number}?`)) {
      deleteMutation.mutate(demo.id);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingDemo(null);
    setFormError('');
  };
  
  const handleAddNew = () => {
    setShowForm(true);
    setEditingDemo(null);
    setFormError('');
  };

  const handleViewDetails = (demo: DemoRequest) => {
    navigate(`/demos/${demo.id}`);
  };

  const getStateBadge = (state: string) => {
    const colors: Record<string, string> = {
      requested: 'bg-blue-100 text-blue-800',
      submitted: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      dispatched: 'bg-purple-100 text-purple-800',
      complete: 'bg-gray-100 text-gray-800',
    };
    return colors[state] || 'bg-gray-100 text-gray-800';
  };

  const getStateLabel = (state: string) => {
    const labels: Record<string, string> = {
      requested: 'Requested',
      submitted: 'Pending Approval',
      approved: 'Approved',
      dispatched: 'Dispatched',
      complete: 'Complete',
    };
    return labels[state] || state;
  };

  // Define columns
  const columns: Column<DemoRequest>[] = [
    {
      key: 'number',
      label: 'Demo Number',
      width: '12%',
      render: (value, row) => (
        <button
          onClick={() => handleViewDetails(row)}
          className="text-blue-600 hover:text-blue-800 font-medium"
        >
          {value}
        </button>
      ),
    },
    {
      key: 'hospital',
      label: 'Hospital',
      width: '25%',
      render: (value: any) => (
        <div>
          {value ? (
            <>
              <div className="font-medium">{value.hospital_name}</div>
              {value.contact_person && (
                <div className="text-xs text-gray-500">{value.contact_person}</div>
              )}
            </>
          ) : (
            <span className="text-gray-400 italic">No hospital</span>
          )}
        </div>
      ),
    },
    {
      key: 'city',
      label: 'City',
      width: '12%',
      render: (value: string) => value ? value : <span className="text-gray-400 italic">-</span>,
    },
    {
      key: 'state',
      label: 'Status',
      width: '12%',
      render: (value: string) => (
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStateBadge(value)}`}>
          {getStateLabel(value)}
        </span>
      ),
    },
    {
      key: 'creator',
      label: 'Created By',
      width: '15%',
      render: (value: any) => value?.full_name || '-',
    },
    {
      key: 'created_at',
      label: 'Created',
      width: '12%',
      render: (value: string) => new Date(value).toLocaleDateString(),
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 bg-white p-4 rounded-lg shadow-sm">
        <div className="flex items-center space-x-4 flex-1">
          <h1 className="text-xl font-bold text-gray-900">Demo Requests</h1>
          
          {/* Search */}
          <div className="flex-1 relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder="Search demo number, hospital, city..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input input-sm pl-9 w-full"
            />
          </div>
          
          {/* State Filter */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="input input-sm"
          >
            <option value="">All States</option>
            <option value="requested">Requested</option>
            <option value="dispatched">Dispatched</option>
            <option value="returned">Returned</option>
          </select>
        </div>
        
        {/* Action Buttons */}
        {canCreate && (
          <div className="flex items-center space-x-2 ml-4">
            <button 
              onClick={handleAddNew}
              className="btn btn-primary btn-sm flex items-center whitespace-nowrap"
            >
              <Plus size={16} className="mr-1" />
              New Demo Request
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-auto max-h-[calc(100vh-200px)]">
        <DataTable
          data={demoRequests || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No demo requests found. Create your first demo request to get started."
          showAuditInfo={false}
          actions={[
            {
              icon: <Eye size={16} />,
              label: 'View Details',
              onClick: handleViewDetails,
              variant: 'primary',
            },
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
        <DemoRequestModal
          initialData={editingDemo}
          onClose={handleCancel}
          onSubmit={handleSubmit}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
          error={formError}
        />
      )}
    </div>
  );
}
