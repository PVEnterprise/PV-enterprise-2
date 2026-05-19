/**
 * QuotationPDFModal - Shared modal for generating estimate/quotation PDFs.
 * Allows user to set Valid Until date and bank details before downloading.
 */
import { useState } from 'react';
import { X, FileText } from 'lucide-react';

export interface QuotationPDFFormData {
  valid_till: string;
  bank_details: {
    bank_account_name: string;
    bank_account_number: string;
    bank_name: string;
    bank_ifsc: string;
    bank_branch: string;
  };
  terms_and_conditions: string;
}

interface QuotationPDFModalProps {
  onClose: () => void;
  onSubmit: (data: QuotationPDFFormData) => void;
  isSubmitting?: boolean;
  title?: string;
}

const DEFAULT_TERMS = `1) Delivery within 10-12 weeks after receiving the confirmed Purchase Order and payment.
2) Prices are mentioned in the Quote.
3) Payment shall be made 100% in advance along with Purchase Order.
4) 3 years warranty.
5) Freight Included.`;

const DEFAULT_BANK = {
  bank_account_name: 'Sreedevi Life Sciences',
  bank_account_number: '42285740549',
  bank_name: 'State Bank of India',
  bank_ifsc: 'SBIN0021790',
  bank_branch: 'Manikonda, Hyderabad',
};

function defaultValidTill() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().split('T')[0];
}

export default function QuotationPDFModal({
  onClose,
  onSubmit,
  isSubmitting = false,
  title = 'Generate Estimate PDF',
}: QuotationPDFModalProps) {
  const [validTill, setValidTill] = useState(defaultValidTill());
  const [bankAccountName, setBankAccountName] = useState(DEFAULT_BANK.bank_account_name);
  const [bankAccountNumber, setBankAccountNumber] = useState(DEFAULT_BANK.bank_account_number);
  const [bankName, setBankName] = useState(DEFAULT_BANK.bank_name);
  const [bankIfsc, setBankIfsc] = useState(DEFAULT_BANK.bank_ifsc);
  const [bankBranch, setBankBranch] = useState(DEFAULT_BANK.bank_branch);
  const [termsAndConditions, setTermsAndConditions] = useState(DEFAULT_TERMS);

  const handleSubmit = () => {
    onSubmit({
      valid_till: validTill,
      bank_details: {
        bank_account_name: bankAccountName,
        bank_account_number: bankAccountNumber,
        bank_name: bankName,
        bank_ifsc: bankIfsc,
        bank_branch: bankBranch,
      },
      terms_and_conditions: termsAndConditions,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-blue-600" />
            <h2 className="text-base font-bold text-gray-900">{title}</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={isSubmitting}>
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="px-4 py-3 space-y-4 overflow-y-auto">
          {/* Valid Until */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Valid Until
            </label>
            <input
              type="date"
              value={validTill}
              onChange={(e) => setValidTill(e.target.value)}
              className="input w-full text-sm"
            />
          </div>

          {/* Terms & Conditions */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Terms &amp; Conditions
            </label>
            <textarea
              value={termsAndConditions}
              onChange={(e) => setTermsAndConditions(e.target.value)}
              rows={5}
              className="input w-full text-xs py-1.5 resize-y font-mono leading-relaxed"
            />
          </div>

          {/* Bank Details */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Bank Details</h3>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Account Name</label>
                <input
                  type="text"
                  value={bankAccountName}
                  onChange={(e) => setBankAccountName(e.target.value)}
                  className="input w-full text-xs py-1"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Account Number</label>
                <input
                  type="text"
                  value={bankAccountNumber}
                  onChange={(e) => setBankAccountNumber(e.target.value)}
                  className="input w-full text-xs py-1"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Bank Name</label>
                <input
                  type="text"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  className="input w-full text-xs py-1"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">IFSC Code</label>
                <input
                  type="text"
                  value={bankIfsc}
                  onChange={(e) => setBankIfsc(e.target.value)}
                  className="input w-full text-xs py-1"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-0.5">Branch</label>
                <input
                  type="text"
                  value={bankBranch}
                  onChange={(e) => setBankBranch(e.target.value)}
                  className="input w-full text-xs py-1"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex gap-2 justify-end flex-shrink-0">
          <button onClick={onClose} className="btn btn-secondary btn-sm" disabled={isSubmitting}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="btn btn-primary btn-sm flex items-center gap-1.5"
            disabled={isSubmitting}
          >
            {isSubmitting && (
              <svg className="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}
            {isSubmitting ? 'Generating...' : 'Download PDF'}
          </button>
        </div>
      </div>
    </div>
  );
}
