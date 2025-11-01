/**
 * Generic Attachment Manager Component
 * Can be used for any entity type (orders, customers, inventory, etc.)
 */
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Upload, File, Image, FileText, Download, Trash2 } from 'lucide-react';

interface Attachment {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  file_size_mb: number;
  description?: string;
  is_image: boolean;
  is_pdf: boolean;
  is_document: boolean;
  created_at: string;
}

interface AttachmentManagerProps {
  entityType: string;  // 'order', 'customer', 'inventory', etc.
  entityId: string;
  canUpload?: boolean;
  canDelete?: boolean;
}

export default function AttachmentManager({
  entityType,
  entityId,
  canUpload = true,
  canDelete = true,
}: AttachmentManagerProps) {
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const queryClient = useQueryClient();

  // Get auth token
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`,
    };
  };

  // Fetch attachments
  const { data: attachments, isLoading } = useQuery<Attachment[]>({
    queryKey: ['attachments', entityType, entityId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/attachments/${entityType}/${entityId}`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to fetch attachments');
      return response.json();
    },
  });

  // Upload handler
  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (description) formData.append('description', description);

      const response = await fetch(`/api/v1/attachments/${entityType}/${entityId}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      queryClient.invalidateQueries({ queryKey: ['attachments', entityType, entityId] });
      setShowUpload(false);
      setSelectedFile(null);
      setDescription('');
    } catch (error: any) {
      alert(error.message);
    } finally {
      setUploading(false);
    }
  };

  // Delete handler
  const handleDelete = async (attachmentId: string) => {
    if (!confirm('Are you sure you want to delete this attachment?')) return;

    try {
      const response = await fetch(`/api/v1/attachments/${attachmentId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (!response.ok) throw new Error('Delete failed');

      queryClient.invalidateQueries({ queryKey: ['attachments', entityType, entityId] });
    } catch (error: any) {
      alert(error.message);
    }
  };

  // Download handler - use fetch with Authorization header and arrayBuffer
  const handleDownload = async (attachmentId: string, filename: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/attachments/download/${attachmentId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }
      
      // Use arrayBuffer instead of blob to avoid any encoding issues
      const arrayBuffer = await response.arrayBuffer();
      const contentType = response.headers.get('content-type') || 'application/octet-stream';
      
      // Create blob from arrayBuffer with correct type
      const blob = new Blob([arrayBuffer], { type: contentType });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      console.error('Download failed:', error);
      alert(`Failed to download file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Get file icon
  const getFileIcon = (attachment: Attachment) => {
    if (attachment.is_image) return <Image size={20} className="text-blue-600" />;
    if (attachment.is_pdf) return <FileText size={20} className="text-red-600" />;
    if (attachment.is_document) return <FileText size={20} className="text-green-600" />;
    return <File size={20} className="text-gray-600" />;
  };

  if (isLoading) {
    return <div className="text-sm text-gray-500">Loading attachments...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          Attachments ({attachments?.length || 0})
        </h3>
        {canUpload && (
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="btn btn-sm btn-secondary flex items-center"
          >
            <Upload size={14} className="mr-1" />
            Upload
          </button>
        )}
      </div>

      {/* Upload Form */}
      {showUpload && (
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select File
              </label>
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt,.json"
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
              />
              <p className="mt-1 text-xs text-gray-500">
                Supported: Images, PDF, Word, Excel, PowerPoint, CSV, TXT, JSON (Max 10MB)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description (Optional)
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add a description..."
                className="input input-sm w-full"
              />
            </div>

            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowUpload(false);
                  setSelectedFile(null);
                  setDescription('');
                }}
                className="btn btn-sm"
                disabled={uploading}
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className="btn btn-sm btn-primary"
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Attachments List */}
      {attachments && attachments.length > 0 ? (
        <div className="space-y-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                {getFileIcon(attachment)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {attachment.original_filename}
                  </p>
                  <div className="flex items-center space-x-2 text-xs text-gray-500">
                    <span>{attachment.file_size_mb} MB</span>
                    {attachment.description && (
                      <>
                        <span>•</span>
                        <span className="truncate">{attachment.description}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleDownload(attachment.id, attachment.original_filename)}
                  className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded"
                  title="Download"
                >
                  <Download size={16} />
                </button>
                {canDelete && (
                  <button
                    onClick={() => handleDelete(attachment.id)}
                    className="p-2 text-gray-600 hover:text-red-600 hover:bg-gray-100 rounded"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500 text-sm">
          No attachments yet. {canUpload && 'Click Upload to add files.'}
        </div>
      )}
    </div>
  );
}
