/**
 * Employees Page - Employee Management
 * Admin: Full CRUD access
 * Others: Read-only access
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { User } from '@/types';
import { Plus, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column, commonActions } from '@/components/common/DataTable';

export default function EmployeesPage() {
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<User | null>(null);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: employees, isLoading } = useQuery<User[]>({
    queryKey: ['employees', search],
    queryFn: () => api.getEmployees({ search }),
  });

  // Only executive (admin) has full access
  const isAdmin = user?.role_name === 'executive';
  const canCreate = isAdmin;
  const canUpdate = isAdmin;
  const canDelete = isAdmin;

  // Fetch roles for dropdown
  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.getRoles(),
  });

  const employeeFields: FormField[] = [
    {
      name: 'full_name',
      label: 'Full Name',
      type: 'text',
      required: true,
      placeholder: 'Enter employee full name',
    },
    {
      name: 'email',
      label: 'Email',
      type: 'email',
      required: true,
      placeholder: 'employee@company.com',
    },
    {
      name: 'password',
      label: 'Password',
      type: 'text',
      required: !editingEmployee,
      placeholder: editingEmployee ? 'Leave blank to keep current password' : 'Enter password',
    },
    {
      name: 'role_id',
      label: 'Role',
      type: 'select',
      required: true,
      options: roles?.map((role: any) => ({
        value: role.id,
        label: role.name === 'executive' ? 'Executive' : 
               role.name === 'sales_rep' ? 'Sales Representative' :
               role.name === 'decoder' ? 'Decoder' :
               role.name === 'quoter' ? 'Quoter' :
               role.name === 'inventory_admin' ? 'Inventory Admin' : role.name
      })) || [],
      defaultValue: roles?.find((r: any) => r.name === 'sales_rep')?.id,
    },
    {
      name: 'phone',
      label: 'Phone',
      type: 'text',
      placeholder: '+91 1234567890',
    },
    {
      name: 'department',
      label: 'Department',
      type: 'text',
      placeholder: 'e.g., Sales, Operations, Admin',
    },
    {
      name: 'is_active',
      label: 'Active Status',
      type: 'select',
      required: true,
      options: [
        { value: 'true', label: 'Active' },
        { value: 'false', label: 'Inactive' },
      ],
      defaultValue: 'true',
    },
  ];

  // Mutations
  const createMutation = useMutation({
    mutationFn: api.createEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      setShowForm(false);
      setEditingEmployee(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.updateEmployee(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      setShowForm(false);
      setEditingEmployee(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteEmployee(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });

  const handleSubmit = async (data: Record<string, any>) => {
    // Convert is_active string to boolean
    const processedData: any = {
      ...data,
      is_active: data.is_active === 'true' || data.is_active === true,
    };

    // Remove password if empty during edit
    if (editingEmployee && !processedData.password) {
      delete processedData.password;
    }

    if (editingEmployee) {
      await updateMutation.mutateAsync({ id: editingEmployee.id, data: processedData });
    } else {
      await createMutation.mutateAsync(processedData);
    }
  };

  const handleEdit = (employee: User) => {
    setEditingEmployee(employee);
    setShowForm(true);
  };

  const handleDelete = (employee: User) => {
    if (confirm(`Are you sure you want to delete ${employee.name}?\n\nThis action cannot be undone.`)) {
      deleteMutation.mutate(employee.id);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingEmployee(null);
  };

  // Define columns
  const columns: Column<User>[] = [
    {
      key: 'name',
      label: 'Name',
      width: '20%',
    },
    {
      key: 'email',
      label: 'Email',
      width: '20%',
    },
    {
      key: 'role_name',
      label: 'Role',
      width: '15%',
      render: (value: string) => {
        const roleLabels: Record<string, string> = {
          admin: 'Admin',
          sales_rep: 'Sales Rep',
          decoder: 'Decoder',
          quoter: 'Quoter',
          inventory_admin: 'Inventory Admin',
        };
        return roleLabels[value] || value;
      },
    },
    {
      key: 'department',
      label: 'Department',
      width: '15%',
      render: (value) => value || '-',
    },
    {
      key: 'phone',
      label: 'Phone',
      width: '15%',
      render: (value) => value || '-',
    },
    {
      key: 'is_active',
      label: 'Status',
      width: '15%',
      render: (value: boolean) => 
        value ? (
          <span className="badge badge-success">Active</span>
        ) : (
          <span className="badge badge-danger">Inactive</span>
        ),
    },
  ];

  return (
    <div>
      {/* Compact Header - Single Line */}
      <div className="flex items-center justify-between mb-4 bg-white p-4 rounded-lg shadow-sm">
        <div className="flex items-center space-x-4 flex-1">
          <div className="flex items-center space-x-3">
            <h1 className="text-xl font-bold text-gray-900">Employees</h1>
            {!isAdmin && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">Read-only</span>
            )}
          </div>
          
          {/* Search */}
          <div className="flex-1 relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder="Search name, email, role..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input input-sm pl-9 w-full"
            />
          </div>
        </div>
        
        {/* Add Button - Always Right */}
        {canCreate && (
          <button 
            onClick={() => setShowForm(true)}
            className="btn btn-primary btn-sm flex items-center whitespace-nowrap ml-4"
          >
            <Plus size={16} className="mr-1" />
            Add Employee
          </button>
        )}
      </div>

      {/* Scrollable Table Container */}
      <div className="overflow-auto max-h-[calc(100vh-200px)]">
        <DataTable
          data={employees || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No employees found. Add your first employee to get started."
          showAuditInfo={true}
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
          title="Employee"
          fields={employeeFields}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          submitLabel={editingEmployee ? 'Update Employee' : 'Add Employee'}
          initialData={editingEmployee ? {
            ...editingEmployee,
            is_active: editingEmployee.is_active ? 'true' : 'false',
            password: '', // Don't show existing password
          } : {}}
          isEdit={!!editingEmployee}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  );
}
