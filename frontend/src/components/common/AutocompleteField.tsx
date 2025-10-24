/**
 * Autocomplete Field Component
 * Search and select from foreign key records with dynamic fetching
 */
import { useState, useEffect, useRef } from 'react';
import { ChevronDown, X } from 'lucide-react';

export interface AutocompleteOption {
  value: string | number;
  label: string;
}

export interface AutocompleteFieldProps {
  label?: string;
  value: string | number;
  onChange: (value: string | number) => void;
  fetchOptions: (searchTerm: string) => Promise<AutocompleteOption[]>;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
}

export default function AutocompleteField({
  label,
  value,
  onChange,
  fetchOptions,
  placeholder = 'Search...',
  required = false,
  disabled = false,
  error,
}: AutocompleteFieldProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [options, setOptions] = useState<AutocompleteOption[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('');
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch options when search term changes
  useEffect(() => {
    const fetchData = async () => {
      if (searchTerm.length === 0) {
        setOptions([]);
        return;
      }

      setIsLoading(true);
      try {
        const results = await fetchOptions(searchTerm);
        setOptions(results);
        setIsOpen(true);
      } catch (error) {
        console.error('Error fetching options:', error);
        setOptions([]);
      } finally {
        setIsLoading(false);
      }
    };

    const debounceTimer = setTimeout(fetchData, 300); // Debounce for 300ms
    return () => clearTimeout(debounceTimer);
  }, [searchTerm, fetchOptions]);

  // Load initial selected value label
  useEffect(() => {
    if (value && !selectedLabel) {
      fetchOptions('').then(results => {
        const selected = results.find(opt => opt.value === value);
        if (selected) {
          setSelectedLabel(selected.label);
        }
      });
    }
  }, [value, selectedLabel, fetchOptions]);

  const handleSelect = (option: AutocompleteOption) => {
    onChange(option.value);
    setSelectedLabel(option.label);
    setSearchTerm('');
    setIsOpen(false);
  };

  const handleClear = () => {
    onChange('');
    setSelectedLabel('');
    setSearchTerm('');
    setOptions([]);
  };

  const handleInputFocus = () => {
    if (searchTerm.length > 0) {
      setIsOpen(true);
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      {/* Selected value display or search input */}
      {selectedLabel && !isOpen ? (
        <div className="relative">
          <div className="input pr-20 flex items-center justify-between bg-white">
            <span className="text-gray-900">{selectedLabel}</span>
            <div className="flex items-center space-x-1">
              {!disabled && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-1 hover:bg-gray-100 rounded"
                  title="Clear selection"
                >
                  <X size={16} className="text-gray-400" />
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  setSelectedLabel('');
                  setIsOpen(true);
                }}
                className="p-1 hover:bg-gray-100 rounded"
                disabled={disabled}
                title="Change selection"
              >
                <ChevronDown size={16} className="text-gray-400" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onFocus={handleInputFocus}
            placeholder={placeholder}
            disabled={disabled}
            className={`input ${error ? 'border-red-500 focus:ring-red-500' : ''}`}
            autoComplete="off"
          />
          {isLoading && (
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            </div>
          )}
        </div>
      )}

      {/* Dropdown results */}
      {isOpen && options.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => handleSelect(option)}
              className="w-full text-left px-4 py-2 hover:bg-primary-50 hover:text-primary-700 focus:bg-primary-50 focus:text-primary-700 focus:outline-none"
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {/* No results message */}
      {isOpen && !isLoading && searchTerm.length > 0 && options.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg p-4 text-center text-gray-500">
          No results found for "{searchTerm}"
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}

      {/* Hidden input for form validation */}
      <input
        type="hidden"
        value={value}
        required={required}
      />
    </div>
  );
}
