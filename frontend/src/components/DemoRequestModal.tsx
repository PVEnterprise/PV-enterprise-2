/**
 * Demo Request Modal with searchable hospital field
 */
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/services/api';
import { Customer, DemoRequest } from '@/types';
import { X } from 'lucide-react';

interface DemoRequestModalProps {
  initialData?: DemoRequest | null;
  onClose: () => void;
  onSubmit: (data: any) => void;
  isSubmitting: boolean;
  error?: string;
}

export default function DemoRequestModal({
  initialData,
  onClose,
  onSubmit,
  isSubmitting,
  error
}: DemoRequestModalProps) {
  const [hospitalSearch, setHospitalSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedHospital, setSelectedHospital] = useState<Customer | null>(null);
  const [formData, setFormData] = useState({
    hospital_id: initialData?.hospital_id,
    city: initialData?.city || '',
    state: initialData?.state || 'requested',
    notes: initialData?.notes || '',
  });

  // Debounce search with 200ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(hospitalSearch);
    }, 200);
    return () => clearTimeout(timer);
  }, [hospitalSearch]);

  // Fetch customers for search
  const { data: customers } = useQuery<Customer[]>({
    queryKey: ['customers', debouncedSearch],
    queryFn: () => api.getCustomers({ search: debouncedSearch, limit: 50 }),
    enabled: debouncedSearch.length > 0,
  });

  // Set initial hospital if editing
  useEffect(() => {
    if (initialData?.hospital) {
      setSelectedHospital(initialData.hospital as Customer);
    }
  }, [initialData]);

  const filteredCustomers = customers || [];

  const handleSubmit = () => {
    onSubmit(formData);
  };

  const isEdit = !!initialData;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <h2 className="text-2xl font-bold">
            {isEdit ? 'Edit Demo Request' : 'Add Demo Request'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isSubmitting}
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          <div className="space-y-4">
            {/* Hospital Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hospital
              </label>
              <input
                type="text"
                value={hospitalSearch}
                onChange={(e) => setHospitalSearch(e.target.value)}
                placeholder="Search hospital..."
                className="input w-full"
              />
              {hospitalSearch && filteredCustomers.length > 0 && (
                <div className="mt-1 max-h-48 overflow-y-auto border border-gray-300 rounded-md bg-white shadow-lg">
                  {filteredCustomers.map((customer) => (
                    <button
                      key={customer.id}
                      onClick={() => {
                        setFormData({ ...formData, hospital_id: customer.id });
                        setSelectedHospital(customer);
                        setHospitalSearch('');
                      }}
                      className="w-full text-left px-4 py-2 hover:bg-gray-100 border-b border-gray-200 last:border-b-0"
                    >
                      <div className="font-medium">{customer.hospital_name}</div>
                      <div className="text-sm text-gray-500">
                        {customer.city && `${customer.city}, `}
                        {customer.state}
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {selectedHospital && (
                <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{selectedHospital.hospital_name}</div>
                    <div className="text-xs text-gray-600">
                      {selectedHospital.city && `${selectedHospital.city}, `}
                      {selectedHospital.state}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setFormData({ ...formData, hospital_id: undefined });
                      setSelectedHospital(null);
                    }}
                    className="text-red-600 hover:text-red-800"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>

            {/* City */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                City
              </label>
              <input
                type="text"
                value={formData.city || ''}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                placeholder="Enter city"
                className="input w-full"
              />
            </div>

            {/* State */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                State <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value as any })}
                className="input w-full"
                required
              >
                <option value="requested">Requested</option>
                <option value="dispatched">Dispatched</option>
                <option value="returned">Returned</option>
              </select>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes
              </label>
              <textarea
                value={formData.notes || ''}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes"
                rows={4}
                className="input w-full"
              />
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex gap-3 justify-end flex-shrink-0">
          <button
            onClick={onClose}
            className="btn btn-secondary"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="btn btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving...' : isEdit ? 'Update Demo Request' : 'Create Demo Request'}
          </button>
        </div>
      </div>
    </div>
  );
}
