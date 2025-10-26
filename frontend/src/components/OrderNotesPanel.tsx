/**
 * Order Notes Panel - Expandable sidebar showing order activity log
 */
import { useState } from 'react';
import { FileText, ChevronRight } from 'lucide-react';

interface OrderNotesPanelProps {
  notes: string | null;
}

export default function OrderNotesPanel({ notes }: OrderNotesPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!notes) {
    return null;
  }

  // Parse notes into individual actions and reverse to show newest first
  const actions = notes.split('\n\n').filter(action => action.trim()).reverse();

  return (
    <>
      {/* Collapsed Icon Button */}
      {!isExpanded && (
        <div className="fixed right-0 top-1/2 -translate-y-1/2 z-40">
          <button
            onClick={() => setIsExpanded(true)}
            className="bg-blue-600 text-white p-3 rounded-l-lg shadow-lg hover:bg-blue-700 transition-all duration-200 flex items-center gap-2 group"
            title="View Order Activity Log"
          >
            <FileText size={20} />
            <span className="text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity max-w-0 group-hover:max-w-xs overflow-hidden whitespace-nowrap">
              Activity Log
            </span>
          </button>
        </div>
      )}

      {/* Expanded Panel */}
      {isExpanded && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black bg-opacity-30 z-40 transition-opacity"
            onClick={() => setIsExpanded(false)}
          />

          {/* Panel */}
          <div className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700">
              <div className="flex items-center gap-2 text-white">
                <FileText size={20} />
                <h2 className="text-lg font-semibold">Activity Log</h2>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                className="text-white hover:bg-blue-800 p-1 rounded transition-colors"
                title="Close"
              >
                <ChevronRight size={20} />
              </button>
            </div>

            {/* Notes Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {actions.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <FileText size={48} className="mx-auto mb-2 text-gray-400" />
                  <p>No activity recorded yet</p>
                </div>
              ) : (
                actions.map((action, index) => {
                  // Parse action format: [timestamp] Action by User (role)
                  const lines = action.split('\n');
                  const headerLine = lines[0];
                  const detailLines = lines.slice(1);

                  // Extract timestamp, action, and user info
                  const timestampMatch = headerLine.match(/\[(.*?)\]/);
                  const timestamp = timestampMatch ? timestampMatch[1] : '';
                  
                  const afterTimestamp = headerLine.substring(headerLine.indexOf(']') + 1).trim();
                  const byIndex = afterTimestamp.indexOf(' by ');
                  const actionText = byIndex > -1 ? afterTimestamp.substring(0, byIndex) : afterTimestamp;
                  const userInfo = byIndex > -1 ? afterTimestamp.substring(byIndex + 4) : '';

                  return (
                    <div
                      key={index}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow"
                    >
                      {/* Action Header */}
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 text-sm">
                            {actionText}
                          </h3>
                          {userInfo && (
                            <p className="text-xs text-gray-600 mt-0.5">
                              by {userInfo}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Timestamp */}
                      {timestamp && (
                        <p className="text-xs text-gray-500 mb-2">
                          {new Date(timestamp).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      )}

                      {/* Details */}
                      {detailLines.length > 0 && detailLines.some(line => line.trim()) && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans">
                            {detailLines.join('\n').trim()}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-gray-200 bg-gray-50 text-center">
              <p className="text-xs text-gray-500">
                {actions.length} {actions.length === 1 ? 'activity' : 'activities'} recorded
              </p>
            </div>
          </div>
        </>
      )}

      {/* Add animation styles */}
      <style>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </>
  );
}
