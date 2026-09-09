/**
 * Executive/quoter view of sales reps' location check-ins, submitted from the
 * sreedevi-sales PWA's four daily reminders (10:00, 12:00, 2:30pm, 5:00pm).
 * Lets a reviewer verify or reject each check-in, and trigger the reminder
 * push on demand — to nudge a rep who hasn't checked in, or to test the push
 * pipeline without waiting for the scheduled time.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ExternalLink, MapPin, Send, X } from 'lucide-react';
import clsx from 'clsx';
import { format, parseISO } from 'date-fns';
import api from '@/services/api';
import { LocationCheckin, LocationCheckinStatus, User } from '@/types';
import DataTable, { Action, Column } from '@/components/common/DataTable';

const STATUS_STYLES: Record<LocationCheckinStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  verified: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
};

function StatusBadge({ status }: { status: LocationCheckinStatus }) {
  return (
    <span className={clsx('inline-block rounded-full px-2.5 py-1 text-xs font-medium capitalize', STATUS_STYLES[status])}>
      {status}
    </span>
  );
}

const SLOT_LABELS: Record<string, string> = {
  '10:00': '10:00 AM',
  '12:00': '12:00 PM',
  '14:30': '2:30 PM',
  '17:00': '5:00 PM',
};

export default function LocationTrackingPage() {
  const today = format(new Date(), 'yyyy-MM-dd');
  const [checkinDate, setCheckinDate] = useState(today);
  const [salesRepId, setSalesRepId] = useState('');
  const [reminderSlot, setReminderSlot] = useState<keyof typeof SLOT_LABELS>('10:00');
  const [reminderResult, setReminderResult] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: salesReps } = useQuery<User[]>({
    queryKey: ['employees', 'sales_rep'],
    queryFn: () => api.getEmployees({ role: 'sales_rep' }),
  });

  const { data: checkins, isLoading } = useQuery<LocationCheckin[]>({
    queryKey: ['location-checkins', checkinDate, salesRepId],
    queryFn: () =>
      api.getLocationCheckins({
        checkin_date: checkinDate,
        ...(salesRepId ? { user_id: salesRepId } : {}),
      }),
  });

  const sendReminder = useMutation({
    mutationFn: () => api.sendLocationReminder({ slot: reminderSlot, user_id: salesRepId || undefined }),
    onSuccess: (result) => {
      setReminderResult(
        result.total === 0
          ? 'No subscribed devices found for that selection.'
          : `Sent to ${result.sent}/${result.total} device(s).`,
      );
      queryClient.invalidateQueries({ queryKey: ['location-checkins'] });
    },
    onError: (err: any) => {
      setReminderResult(err?.response?.data?.detail ?? 'Failed to send reminder.');
    },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'verified' | 'rejected' }) =>
      api.updateLocationCheckinStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['location-checkins'] });
    },
  });

  const columns: Column<LocationCheckin>[] = [
    { key: 'user.full_name', label: 'Sales Rep', sortable: true },
    {
      key: 'slot',
      label: 'Slot',
      sortable: true,
      render: (value: string) => SLOT_LABELS[value] ?? value,
    },
    {
      key: 'recorded_at',
      label: 'Time',
      sortable: true,
      render: (value: string) => format(parseISO(value), 'h:mm a'),
    },
    { key: 'hospital_name', label: 'Hospital', sortable: true },
    {
      key: 'latitude',
      label: 'Location',
      render: (_value: number, row: LocationCheckin) => (
        <a
          href={`https://www.google.com/maps?q=${row.latitude},${row.longitude}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-emerald-700 hover:underline"
        >
          {row.latitude.toFixed(5)}, {row.longitude.toFixed(5)}
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      ),
    },
    {
      key: 'accuracy',
      label: 'Accuracy',
      render: (value: number | null) => (value != null ? `±${Math.round(value)}m` : '—'),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (value: LocationCheckinStatus) => <StatusBadge status={value} />,
    },
  ];

  const rowActions: Action<LocationCheckin>[] = [
    {
      label: 'Verify',
      icon: <Check size={16} />,
      onClick: (row) => updateStatus.mutate({ id: row.id, status: 'verified' }),
      show: (row) => row.status !== 'verified',
      variant: 'primary',
    },
    {
      label: 'Reject',
      icon: <X size={16} />,
      onClick: (row) => updateStatus.mutate({ id: row.id, status: 'rejected' }),
      show: (row) => row.status !== 'rejected',
      variant: 'danger',
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-3">
        <MapPin className="h-6 w-6 text-emerald-700" />
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Location Tracking</h1>
          <p className="text-sm text-gray-500">
            Sales reps' check-ins from the field sales app's four daily reminders.
          </p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="date"
          value={checkinDate}
          max={today}
          onChange={(e) => setCheckinDate(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <select
          value={salesRepId}
          onChange={(e) => setSalesRepId(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All sales reps</option>
          {salesReps?.map((rep) => (
            <option key={rep.id} value={rep.id}>
              {rep.full_name || rep.name}
            </option>
          ))}
        </select>

        <div className="ml-auto flex items-center gap-2">
          <select
            value={reminderSlot}
            onChange={(e) => setReminderSlot(e.target.value as keyof typeof SLOT_LABELS)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            {Object.entries(SLOT_LABELS).map(([slot, label]) => (
              <option key={slot} value={slot}>
                {label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => {
              setReminderResult(null);
              sendReminder.mutate();
            }}
            disabled={sendReminder.isPending}
            className="flex items-center gap-2 rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {sendReminder.isPending
              ? 'Sending…'
              : `Send reminder now${salesRepId ? '' : ' (all reps)'}`}
          </button>
        </div>
      </div>

      {reminderResult && <p className="mb-4 text-sm text-gray-600">{reminderResult}</p>}

      <DataTable
        data={checkins ?? []}
        columns={columns}
        actions={rowActions}
        isLoading={isLoading}
        emptyMessage="No check-ins for this day."
        tableId="location-checkins"
        defaultGroupBy={['user.full_name']}
      />
    </div>
  );
}
