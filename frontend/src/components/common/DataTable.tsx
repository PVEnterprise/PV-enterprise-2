/**
 * Data Table Component
 * Reusable table component for displaying lists of records with actions
 * Supports sorting and multi-level grouping
 */
import React, { ReactNode, useState, useMemo } from 'react';
import { Edit, Trash2, Eye, MoreVertical, ArrowUp, ArrowDown, X, GripVertical, ChevronDown, ChevronRight } from 'lucide-react';

export interface Column<T> {
  key: keyof T | string;
  label: string;
  render?: (value: any, row: T) => ReactNode;
  sortable?: boolean;
  width?: string;
}

export interface Action<T> {
  label: string;
  icon?: ReactNode;
  onClick: (row: T) => void;
  show?: (row: T) => boolean;
  variant?: 'primary' | 'secondary' | 'danger';
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  actions?: Action<T>[];
  isLoading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  showAuditInfo?: boolean;
  enableSorting?: boolean;
  enableGrouping?: boolean;
  maxGroupLevels?: number;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortState {
  key: string;
  direction: SortDirection;
}

export default function DataTable<T extends Record<string, any>>({
  data,
  columns,
  actions = [],
  isLoading = false,
  emptyMessage = 'No data available',
  onRowClick,
  showAuditInfo = true,
  enableSorting = true,
  enableGrouping = true,
  maxGroupLevels = 3,
}: DataTableProps<T>) {
  const [sortState, setSortState] = useState<SortState>({ key: '', direction: null });
  const [groupByColumns, setGroupByColumns] = useState<string[]>([]);
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  
  const getValue = (row: T, key: string): any => {
    if (key.includes('.')) {
      const keys = key.split('.');
      let value: any = row;
      for (const k of keys) {
        value = value?.[k];
      }
      return value;
    }
    return row[key];
  };

  const formatAuditInfo = (row: T) => {
    const createdAt = row.created_at ? new Date(row.created_at).toLocaleString() : '-';
    const updatedAt = row.updated_at ? new Date(row.updated_at).toLocaleString() : '-';
    const createdBy = row.created_by_name || row.created_by || '-';
    const updatedBy = row.updated_by_name || row.updated_by || '-';

    return (
      <div className="text-xs text-gray-500 mt-1">
        <div>Created: {createdAt} by {createdBy}</div>
        {row.updated_at !== row.created_at && (
          <div>Updated: {updatedAt} by {updatedBy}</div>
        )}
      </div>
    );
  };

  // Sorting logic
  const handleSort = (columnKey: string) => {
    if (!enableSorting) return;
    
    setSortState(prev => {
      if (prev.key !== columnKey) {
        return { key: columnKey, direction: 'desc' };
      }
      if (prev.direction === 'desc') {
        return { key: columnKey, direction: 'asc' };
      }
      return { key: '', direction: null };
    });
  };

  // Grouping logic
  const handleDragStart = (columnKey: string) => {
    setDraggedColumn(columnKey);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedColumn && !groupByColumns.includes(draggedColumn) && groupByColumns.length < maxGroupLevels) {
      setGroupByColumns([...groupByColumns, draggedColumn]);
    }
    setDraggedColumn(null);
  };

  const removeGrouping = (columnKey: string) => {
    setGroupByColumns(groupByColumns.filter(key => key !== columnKey));
  };

  const toggleGroupCollapse = (groupPath: string) => {
    setCollapsedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupPath)) {
        newSet.delete(groupPath);
      } else {
        newSet.add(groupPath);
      }
      return newSet;
    });
  };

  // Sort and group data
  const processedData = useMemo(() => {
    let result = [...data];

    // Apply sorting
    if (sortState.key && sortState.direction) {
      result.sort((a, b) => {
        const aVal = getValue(a, sortState.key);
        const bVal = getValue(b, sortState.key);
        
        if (aVal === bVal) return 0;
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        
        const comparison = aVal < bVal ? -1 : 1;
        return sortState.direction === 'asc' ? comparison : -comparison;
      });
    }

    return result;
  }, [data, sortState]);

  // Group data by columns
  const groupedData = useMemo(() => {
    if (groupByColumns.length === 0) return null;

    const groups: any = {};
    
    processedData.forEach(row => {
      let currentLevel = groups;
      
      groupByColumns.forEach((colKey, index) => {
        const value = String(getValue(row, colKey) || 'N/A');
        
        if (!currentLevel[value]) {
          currentLevel[value] = {
            key: value,
            items: index === groupByColumns.length - 1 ? [] : {},
          };
        }
        
        if (index === groupByColumns.length - 1) {
          currentLevel[value].items.push(row);
        } else {
          currentLevel = currentLevel[value].items;
        }
      });
    });

    return groups;
  }, [processedData, groupByColumns]);

  const getActionButton = (action: Action<T>, row: T) => {
    if (action.show && !action.show(row)) {
      return null;
    }

    const variantClasses = {
      primary: 'text-primary-600 hover:text-primary-700',
      secondary: 'text-gray-600 hover:text-gray-700',
      danger: 'text-red-600 hover:text-red-700',
    };

    return (
      <button
        key={action.label}
        onClick={(e) => {
          e.stopPropagation();
          action.onClick(row);
        }}
        className={`p-2 rounded hover:bg-gray-100 transition-colors ${
          variantClasses[action.variant || 'secondary']
        }`}
        title={action.label}
      >
        {action.icon || <MoreVertical size={16} />}
      </button>
    );
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="card">
        <div className="text-center py-12 text-gray-500">
          {emptyMessage}
        </div>
      </div>
    );
  }

  // Render grouped rows recursively
  const renderGroupedRows = (groups: any, level: number = 0, parentPath: string = ''): React.ReactNode => {
    return Object.entries(groups).map(([groupKey, groupData]: [string, any]) => {
      const isLastLevel = Array.isArray(groupData.items);
      const groupPath = parentPath ? `${parentPath}>${groupKey}` : groupKey;
      const isCollapsed = collapsedGroups.has(groupPath);
      const itemCount = isLastLevel ? groupData.items.length : Object.keys(groupData.items).length;
      
      return (
        <React.Fragment key={`${level}-${groupKey}`}>
          <tr className={`bg-gray-${Math.min(100 + level * 50, 200)} hover:bg-gray-${Math.min(150 + level * 50, 250)} cursor-pointer`}>
            <td 
              colSpan={columns.length + (actions.length > 0 ? 1 : 0)} 
              className="px-6 py-3"
              onClick={() => toggleGroupCollapse(groupPath)}
            >
              <div className="flex items-center font-semibold text-gray-900" style={{ paddingLeft: `${level * 20}px` }}>
                {isCollapsed ? (
                  <ChevronRight size={16} className="mr-2 text-gray-600" />
                ) : (
                  <ChevronDown size={16} className="mr-2 text-gray-600" />
                )}
                <span className="text-sm">{columns.find(c => String(c.key) === groupByColumns[level])?.label}: {groupKey}</span>
                <span className="ml-2 text-xs text-gray-500">({itemCount} {itemCount === 1 ? 'item' : 'items'})</span>
              </div>
            </td>
          </tr>
          {!isCollapsed && (
            isLastLevel ? (
              groupData.items.map((row: T, rowIndex: number) => renderRow(row, rowIndex, level + 1))
            ) : (
              renderGroupedRows(groupData.items, level + 1, groupPath)
            )
          )}
        </React.Fragment>
      );
    });
  };

  // Render a single row
  const renderRow = (row: T, rowIndex: number, indentLevel: number = 0) => (
    <tr
      key={row.id || rowIndex}
      onClick={() => onRowClick?.(row)}
      className={onRowClick ? 'hover:bg-gray-50 cursor-pointer' : ''}
    >
      {columns.map((column, colIndex) => {
        const value = getValue(row, String(column.key));
        return (
          <td key={String(column.key)} className="px-6 py-4 whitespace-nowrap">
            <div style={{ paddingLeft: colIndex === 0 ? `${indentLevel * 20}px` : '0' }}>
              {column.render ? column.render(value, row) : (
                <span className="text-sm text-gray-900">{value || '-'}</span>
              )}
              {showAuditInfo && column.key === columns[0].key && formatAuditInfo(row)}
            </div>
          </td>
        );
      })}
      {actions.length > 0 && (
        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
          <div className="flex justify-end space-x-1">
            {actions.map((action) => getActionButton(action, row))}
          </div>
        </td>
      )}
    </tr>
  );

  const dataToRender = groupedData ? null : processedData;

  return (
    <div className="card overflow-hidden">
      {/* Grouping Lane */}
      {enableGrouping && (
        <div 
          className="bg-blue-50 border-b border-blue-200 p-3"
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 font-medium">Group by:</span>
            {groupByColumns.length === 0 ? (
              <span className="text-sm text-gray-400 italic">Drag column headers here to group (max {maxGroupLevels})</span>
            ) : (
              groupByColumns.map((colKey, index) => {
                const column = columns.find(c => String(c.key) === colKey);
                return (
                  <div key={colKey} className="flex items-center gap-1 bg-blue-100 px-3 py-1 rounded-full">
                    <span className="text-sm font-medium text-blue-800">{index + 1}. {column?.label}</span>
                    <button
                      onClick={() => removeGrouping(colKey)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <X size={14} />
                    </button>
                  </div>
                );
              })
            )}
            {groupByColumns.length > 0 && (
              <button
                onClick={() => setGroupByColumns([])}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                Clear all
              </button>
            )}
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                    enableSorting || enableGrouping ? 'cursor-pointer select-none' : ''
                  }`}
                  style={{ width: column.width }}
                  draggable={enableGrouping}
                  onDragStart={() => handleDragStart(String(column.key))}
                  onClick={() => handleSort(String(column.key))}
                >
                  <div className="flex items-center gap-2">
                    {enableGrouping && <GripVertical size={14} className="text-gray-400" />}
                    <span>{column.label}</span>
                    {enableSorting && sortState.key === String(column.key) && (
                      sortState.direction === 'desc' ? <ArrowDown size={14} /> : <ArrowUp size={14} />
                    )}
                  </div>
                </th>
              ))}
              {actions.length > 0 && (
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {groupedData ? renderGroupedRows(groupedData) : dataToRender?.map((row, rowIndex) => renderRow(row, rowIndex))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Common action helpers
export const commonActions = {
  view: <T,>(onClick: (row: T) => void): Action<T> => ({
    label: 'View',
    icon: <Eye size={16} />,
    onClick,
    variant: 'secondary',
  }),
  
  edit: <T,>(onClick: (row: T) => void, canEdit?: (row: T) => boolean): Action<T> => ({
    label: 'Edit',
    icon: <Edit size={16} />,
    onClick,
    show: canEdit,
    variant: 'primary',
  }),
  
  delete: <T,>(onClick: (row: T) => void, canDelete?: (row: T) => boolean): Action<T> => ({
    label: 'Delete',
    icon: <Trash2 size={16} />,
    onClick,
    show: canDelete,
    variant: 'danger',
  }),
};
