/**
 * Dynamic Form Component
 * Reusable form component for creating and updating records with validation
 */
import { useState, FormEvent } from 'react';
import { X } from 'lucide-react';
import AutocompleteField from './AutocompleteField';

export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'number' | 'textarea' | 'select' | 'date' | 'checkbox' | 'autocomplete';
  required?: boolean;
  placeholder?: string;
  options?: { value: string | number; label: string }[]; // For select fields
  fetchOptions?: (searchTerm: string) => Promise<{ value: string | number; label: string }[]>; // For autocomplete fields
  validation?: {
    pattern?: RegExp;
    message?: string;
    min?: number;
    max?: number;
  };
  defaultValue?: any;
  disabled?: boolean;
}

export interface DynamicFormProps {
  title: string;
  fields: FormField[];
  onSubmit: (data: Record<string, any>) => void | Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
  isLoading?: boolean;
  initialData?: Record<string, any>;
  isEdit?: boolean;
  error?: string;
}

export default function DynamicForm({
  title,
  fields,
  onSubmit,
  onCancel,
  submitLabel = 'Submit',
  isLoading = false,
  initialData = {},
  isEdit = false,
  error = '',
}: DynamicFormProps) {
  const [formData, setFormData] = useState<Record<string, any>>(
    fields.reduce((acc, field) => {
      acc[field.name] = initialData[field.name] ?? field.defaultValue ?? '';
      return acc;
    }, {} as Record<string, any>)
  );

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateField = (field: FormField, value: any): string | null => {
    if (field.required && !value) {
      return `${field.label} is required`;
    }

    if (field.validation) {
      if (field.validation.pattern && !field.validation.pattern.test(value)) {
        return field.validation.message || `Invalid ${field.label}`;
      }

      if (field.type === 'number') {
        const numValue = Number(value);
        if (field.validation.min !== undefined && numValue < field.validation.min) {
          return `${field.label} must be at least ${field.validation.min}`;
        }
        if (field.validation.max !== undefined && numValue > field.validation.max) {
          return `${field.label} must be at most ${field.validation.max}`;
        }
      }
    }

    return null;
  };

  const handleChange = (name: string, value: any) => {
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // Validate all fields
    const newErrors: Record<string, string> = {};
    fields.forEach(field => {
      const error = validateField(field, formData[field.name]);
      if (error) {
        newErrors[field.name] = error;
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Submit form
    await onSubmit(formData);
  };

  const renderField = (field: FormField) => {
    const value = formData[field.name];
    const error = errors[field.name];

    const commonClasses = `input ${error ? 'border-red-500 focus:ring-red-500' : ''}`;

    switch (field.type) {
      case 'textarea':
        return (
          <textarea
            id={field.name}
            name={field.name}
            value={value}
            onChange={(e) => handleChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            disabled={field.disabled}
            className={commonClasses}
            rows={4}
          />
        );

      case 'select':
        // Add search functionality for selects with more than 5 options
        const hasSearch = (field.options?.length || 0) > 5;
        const [searchTerm, setSearchTerm] = useState('');
        const filteredOptions = hasSearch
          ? field.options?.filter(opt => 
              opt.label.toLowerCase().includes(searchTerm.toLowerCase())
            )
          : field.options;

        return (
          <div>
            {hasSearch && (
              <input
                type="text"
                placeholder={`Search ${field.label.toLowerCase()}...`}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input mb-2"
                disabled={field.disabled}
              />
            )}
            <select
              id={field.name}
              name={field.name}
              value={value}
              onChange={(e) => handleChange(field.name, e.target.value)}
              required={field.required}
              disabled={field.disabled}
              className={commonClasses}
            >
              <option value="">{field.placeholder || `Select ${field.label}`}</option>
              {filteredOptions?.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        );

      case 'checkbox':
        return (
          <div className="flex items-center">
            <input
              type="checkbox"
              id={field.name}
              name={field.name}
              checked={value}
              onChange={(e) => handleChange(field.name, e.target.checked)}
              disabled={field.disabled}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <label htmlFor={field.name} className="ml-2 text-sm text-gray-700">
              {field.label}
            </label>
          </div>
        );

      case 'autocomplete':
        if (!field.fetchOptions) {
          console.error(`Field ${field.name} is autocomplete but missing fetchOptions`);
          return null;
        }
        return (
          <AutocompleteField
            value={value}
            onChange={(newValue) => handleChange(field.name, newValue)}
            fetchOptions={field.fetchOptions}
            placeholder={field.placeholder}
            required={field.required}
            disabled={field.disabled}
            error={error}
          />
        );

      default:
        return (
          <input
            type={field.type}
            id={field.name}
            name={field.name}
            value={value}
            onChange={(e) => handleChange(field.name, e.target.value)}
            onWheel={(e) => field.type === 'number' && e.currentTarget.blur()}
            placeholder={field.placeholder}
            required={field.required}
            disabled={field.disabled}
            className={commonClasses}
            min={field.validation?.min}
            max={field.validation?.max}
          />
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Fixed Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
          <h2 className="text-2xl font-bold text-gray-900">
            {isEdit ? `Edit ${title}` : `Add ${title}`}
          </h2>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            disabled={isLoading}
          >
            <X size={24} className="text-gray-500" />
          </button>
        </div>

        {/* Scrollable Form Content */}
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {/* API Error Display */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800 font-medium">{error}</p>
              </div>
            )}
            
            <div className="space-y-4">
              {fields.map(field => (
                <div key={field.name}>
                  {field.type !== 'checkbox' && field.type !== 'autocomplete' && (
                    <label
                      htmlFor={field.name}
                      className="block text-sm font-medium text-gray-700 mb-1"
                    >
                      {field.label}
                      {field.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                  )}
                  {renderField(field)}
                  {errors[field.name] && (
                    <p className="mt-1 text-sm text-red-600">{errors[field.name]}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Fixed Footer */}
          <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
            <button
              type="button"
              onClick={onCancel}
              className="btn btn-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Saving...' : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
