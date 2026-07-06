/**
 * Log Visit page — data entry's primary page for keying in WhatsApp-shared
 * field visit locations (and leave/holiday attendance) on behalf of sales reps.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { FieldVisit } from '@/types';
import AutocompleteField, { AutocompleteOption } from '@/components/common/AutocompleteField';
import { MapPin, Plus, CalendarOff } from 'lucide-react';

type Target = 'customer' | 'lead';

export default function LogVisitPage() {
  const queryClient = useQueryClient();

  const [salesRepId, setSalesRepId] = useState('');
  const [visitDate, setVisitDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [city, setCity] = useState('');
  const [target, setTarget] = useState<Target>('customer');
  const [customerId, setCustomerId] = useState<string | number>('');
  const [leadId, setLeadId] = useState<string | number>('');
  const [inTime, setInTime] = useState('');
  const [outTime, setOutTime] = useState('');
  const [notes, setNotes] = useState('');

  const [showNewLead, setShowNewLead] = useState(false);
  const [newLeadName, setNewLeadName] = useState('');

  const [attendanceStatus, setAttendanceStatus] = useState<'leave' | 'holiday'>('leave');

  const { data: salesReps = [] } = useQuery({
    queryKey: ['field-visit-sales-reps'],
    queryFn: () => api.getSalesRepsForVisitLogging(),
  });

  const { data: todaysVisits = [] } = useQuery<FieldVisit[]>({
    queryKey: ['field-visits', salesRepId, visitDate],
    queryFn: () => api.getFieldVisits({ sales_rep_id: salesRepId, date_from: visitDate, date_to: visitDate }),
    enabled: !!salesRepId,
  });

  const fetchCustomers = async (search: string): Promise<AutocompleteOption[]> => {
    const customers = await api.getCustomers({ search });
    return customers.map((c: any) => ({ value: c.id, label: c.hospital_name, subtitle: c.address }));
  };

  const fetchLeads = async (search: string): Promise<AutocompleteOption[]> => {
    if (!city) return [];
    const leads = await api.getLeads({ city, search });
    return leads.map((l: any) => ({ value: l.id, label: l.name, subtitle: l.hospital_name }));
  };

  const createVisitMutation = useMutation({
    mutationFn: api.createFieldVisit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['field-visits'] });
      setCustomerId('');
      setLeadId('');
      setInTime('');
      setOutTime('');
      setNotes('');
    },
  });

  const createLeadMutation = useMutation({
    mutationFn: api.createLead,
    onSuccess: (lead: any) => {
      setLeadId(lead.id);
      setShowNewLead(false);
      setNewLeadName('');
    },
  });

  const createAttendanceMutation = useMutation({
    mutationFn: api.createAttendance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['field-visits'] });
    },
  });

  const canSubmitVisit = !!salesRepId && !!visitDate && (target === 'customer' ? !!customerId : !!leadId);

  const handleSubmitVisit = () => {
    createVisitMutation.mutate({
      sales_rep_id: salesRepId,
      visit_date: visitDate,
      customer_id: target === 'customer' ? customerId : undefined,
      lead_id: target === 'lead' ? leadId : undefined,
      in_time: inTime || undefined,
      out_time: outTime || undefined,
      notes: notes || undefined,
    });
  };

  const handleCreateLead = () => {
    if (!newLeadName.trim() || !city) return;
    createLeadMutation.mutate({ name: newLeadName.trim(), city });
  };

  const handleMarkAttendance = () => {
    if (!salesRepId || !visitDate) return;
    createAttendanceMutation.mutate({
      sales_rep_id: salesRepId,
      attendance_date: visitDate,
      status: attendanceStatus,
    });
  };

  return (
    <div className="w-full max-w-3xl">
      <div className="flex items-center gap-3 mb-4 bg-white p-4 rounded-lg shadow-sm">
        <MapPin size={18} className="text-primary-600" />
        <h1 className="text-xl font-bold text-gray-900">Log Visit</h1>
      </div>

      <div className="card space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sales Rep <span className="text-red-500">*</span>
            </label>
            <select
              className="input"
              value={salesRepId}
              onChange={(e) => setSalesRepId(e.target.value)}
            >
              <option value="">Select sales rep...</option>
              {salesReps.map((r: any) => (
                <option key={r.id} value={r.id}>{r.full_name}{r.city ? ` (${r.city})` : ''}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              className="input"
              value={visitDate}
              onChange={(e) => setVisitDate(e.target.value)}
            />
          </div>
        </div>

        <div className="border-t pt-4">
          <div className="flex items-center gap-2 mb-3">
            <button
              type="button"
              onClick={() => setTarget('customer')}
              className={`btn btn-sm ${target === 'customer' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Existing Hospital
            </button>
            <button
              type="button"
              onClick={() => setTarget('lead')}
              className={`btn btn-sm ${target === 'lead' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Lead
            </button>
          </div>

          {target === 'customer' ? (
            <AutocompleteField
              label="Hospital"
              value={customerId}
              onChange={setCustomerId}
              fetchOptions={fetchCustomers}
              placeholder="Search customer..."
              required
            />
          ) : (
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  City <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="input"
                  value={city}
                  onChange={(e) => { setCity(e.target.value); setLeadId(''); }}
                  placeholder="Enter city first..."
                />
              </div>
              <AutocompleteField
                label="Lead"
                value={leadId}
                onChange={setLeadId}
                fetchOptions={fetchLeads}
                placeholder={city ? 'Search lead...' : 'Select a city first'}
                disabled={!city}
                required
              />
              {city && !showNewLead && (
                <button
                  type="button"
                  onClick={() => setShowNewLead(true)}
                  className="text-sm text-primary-600 hover:underline flex items-center gap-1"
                >
                  <Plus size={14} /> Create new lead in {city}
                </button>
              )}
              {showNewLead && (
                <div className="flex items-center gap-2 bg-gray-50 p-3 rounded-md">
                  <input
                    type="text"
                    className="input flex-1"
                    placeholder="Lead name"
                    value={newLeadName}
                    onChange={(e) => setNewLeadName(e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={!newLeadName.trim() || createLeadMutation.isLoading}
                    onClick={handleCreateLead}
                  >
                    Create
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setShowNewLead(false)}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">In Time</label>
            <input type="time" className="input" value={inTime} onChange={(e) => setInTime(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Out Time</label>
            <input type="time" className="input" value={outTime} onChange={(e) => setOutTime(e.target.value)} />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <button
          type="button"
          className="btn btn-primary"
          disabled={!canSubmitVisit || createVisitMutation.isLoading}
          onClick={handleSubmitVisit}
        >
          {createVisitMutation.isLoading ? 'Saving...' : 'Log Visit'}
        </button>
      </div>

      <div className="card mt-4">
        <div className="flex items-center gap-2 mb-3">
          <CalendarOff size={16} className="text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-700">Mark Leave / Holiday</h3>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="input w-40"
            value={attendanceStatus}
            onChange={(e) => setAttendanceStatus(e.target.value as 'leave' | 'holiday')}
          >
            <option value="leave">Leave</option>
            <option value="holiday">Holiday</option>
          </select>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!salesRepId || !visitDate || createAttendanceMutation.isLoading}
            onClick={handleMarkAttendance}
          >
            Mark for {visitDate}
          </button>
        </div>
      </div>

      {salesRepId && (
        <div className="card mt-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Already logged on {visitDate}</h3>
          {todaysVisits.length === 0 ? (
            <p className="text-xs text-gray-400 italic">No visits logged yet</p>
          ) : (
            <ul className="space-y-1">
              {todaysVisits.map((v) => (
                <li key={v.id} className="text-sm text-gray-700 flex justify-between border-b border-gray-50 py-1">
                  <span>{v.customer_name || v.lead_name}</span>
                  <span className="text-gray-400">{v.in_time || ''}{v.out_time ? ` - ${v.out_time}` : ''}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
