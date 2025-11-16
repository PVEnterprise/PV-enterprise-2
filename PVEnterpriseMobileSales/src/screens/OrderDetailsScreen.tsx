/**
 * Order Details Screen - Complete version with download functionality
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Linking,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
// import { Ionicons } from '@expo/vector-icons';
import Icon from 'react-native-vector-icons/Ionicons';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import * as DocumentPicker from 'expo-document-picker';
import { useAppDispatch, useAppSelector } from '@/hooks/redux';
import { fetchOrderById } from '@/store/slices/ordersSlice';
import apiService from '@/services/api';
import { showSuccessToast, showErrorToast } from '@/utils/toast';
import { Invoice, Quotation, Attachment } from '@/types';

// Define Dispatch type locally since it's not in types
interface Dispatch {
  id: string;
  dispatch_number: string;
  dispatch_date?: string;
  status: string;
  tracking_number?: string;
  notes?: string;
}

interface RouteParams {
  orderId: string;
}

const OrderDetailsScreen: React.FC = () => {
  const route = useRoute();
  const dispatch = useAppDispatch();
  const { orderId } = route.params as RouteParams;
  
  const { currentOrder, isLoading } = useAppSelector(state => state.orders);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [dispatches, setDispatches] = useState<Dispatch[]>([]);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(false);

  useEffect(() => {
    dispatch(fetchOrderById(orderId));
  }, [orderId, dispatch]);

  useEffect(() => {
    if (currentOrder) {
      loadOrderDocuments();
    }
  }, [currentOrder]);

  const loadOrderDocuments = async () => {
    if (!orderId) return;
    
    setLoadingDocs(true);
    try {
      // Load all related documents
      const [invoicesData, attachmentsData, dispatchesData] = await Promise.allSettled([
        apiService.get<Invoice[]>(`/orders/${orderId}/invoices`),
        apiService.getAttachments('order', orderId),
        apiService.get<Dispatch[]>(`/dispatches/order/${orderId}`),
      ]);

      if (invoicesData.status === 'fulfilled') setInvoices(invoicesData.value);
      if (attachmentsData.status === 'fulfilled') setAttachments(attachmentsData.value);
      if (dispatchesData.status === 'fulfilled') {
        console.log('Dispatches loaded:', dispatchesData.value);
        setDispatches(dispatchesData.value);
      } else {
        console.log('Failed to load dispatches:', dispatchesData);
      }
      
      // For quotations, we check if the order status allows quotation download
      // and create a virtual quotation object for display
      console.log('Order status check:', {
        status: currentOrder?.status,
        workflow_stage: currentOrder?.workflow_stage,
        order_number: currentOrder?.order_number
      });
      
      // Show quotation for any order that's not in draft status
      // The backend endpoint will handle the actual validation
      console.log('Checking quotation condition:', {
        hasCurrentOrder: !!currentOrder,
        status: currentOrder?.status,
        workflow_stage: currentOrder?.workflow_stage,
        shouldShowQuotation: currentOrder && currentOrder.status !== 'draft' && currentOrder.workflow_stage === 'waiting_purchase_order'
      });
      
      // Show quotation only for orders in waiting_purchase_order stage (before PO approval)
      if (currentOrder && currentOrder.status !== 'draft' && currentOrder.workflow_stage === 'waiting_purchase_order') {
        console.log('Creating virtual quotation for order:', currentOrder.order_number);
        // Create a virtual quotation for display
        const virtualQuotation: Quotation = {
          id: orderId,
          quote_number: `QUO-${currentOrder.order_number}`,
          order_id: orderId,
          created_by: currentOrder.created_by || '',
          status: currentOrder.status === 'quote_sent' ? 'sent' : 'approved',
          subtotal: 0,
          gst_rate: 18,
          gst_amount: 0,
          discount_percentage: currentOrder.discount_percentage || 0,
          discount_amount: 0,
          total_amount: currentOrder.grand_total || 0,
          valid_until: new Date().toISOString().split('T')[0], // Convert to date string
          created_at: currentOrder.created_at || new Date().toISOString(),
          updated_at: currentOrder.updated_at || new Date().toISOString(),
        };
        console.log('Setting quotations array with virtual quotation:', virtualQuotation);
        setQuotations([virtualQuotation]);
      } else {
        console.log('Not showing quotation - order is draft, missing, or PO already approved');
        setQuotations([]);
      }
    } catch (error) {
      console.error('Failed to load order documents:', error);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleFileBlob = async (blob: Blob, filename: string) => {
    try {
      // For React Native, we need to handle blob differently
      let base64Data: string;
      
      // Check if blob is already a string (base64) or needs conversion
      if (typeof blob === 'string') {
        base64Data = blob;
      } else if (blob instanceof Blob) {
        // Use FileReader for proper blob conversion in React Native
        const reader = new FileReader();
        const base64Promise = new Promise<string>((resolve, reject) => {
          reader.onload = () => {
            const result = reader.result as string;
            const base64 = result.includes(',') ? result.split(',')[1] : result;
            resolve(base64);
          };
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        base64Data = await base64Promise;
      } else {
        base64Data = String(blob);
      }
      
      // Check if the file is too large (over 10MB base64 ≈ 7.5MB actual)
      if (base64Data.length > 10 * 1024 * 1024) {
        showErrorToast('File is too large to process');
        return;
      }
      
      // Save file and open with system viewer
      try {
        // Determine MIME type based on file extension
        const extension = filename.toLowerCase().split('.').pop();
        let mimeType = 'application/octet-stream';
        
        switch (extension) {
          case 'pdf':
            mimeType = 'application/pdf';
            break;
          case 'jpg':
          case 'jpeg':
            mimeType = 'image/jpeg';
            break;
          case 'png':
            mimeType = 'image/png';
            break;
          case 'gif':
            mimeType = 'image/gif';
            break;
          case 'doc':
            mimeType = 'application/msword';
            break;
          case 'docx':
            mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
            break;
          case 'xls':
            mimeType = 'application/vnd.ms-excel';
            break;
          case 'xlsx':
            mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
            break;
        }
        
        // Create data URI for the file
        const dataUri = `data:${mimeType};base64,${base64Data}`;
        
        // Try to open the file directly in the browser/viewer
        try {
          if (await Linking.canOpenURL(dataUri)) {
            await Linking.openURL(dataUri);
            showSuccessToast(`📄 ${filename} opened successfully!`);
          } else {
            throw new Error('Cannot open data URI directly');
          }
        } catch (linkError) {
          // Fallback: Save to app directory and try to share
          try {
            const fileUri = FileSystem.documentDirectory + filename;
            await FileSystem.writeAsStringAsync(fileUri, base64Data, {
              encoding: FileSystem.EncodingType.Base64,
            });
            
            // Try to share the file so user can save it
            if (await Sharing.isAvailableAsync()) {
              await Sharing.shareAsync(fileUri, {
                mimeType: mimeType,
                dialogTitle: `Save ${filename}`,
              });
              showSuccessToast(`📄 ${filename} ready to save!`);
            } else {
              showSuccessToast(`📄 ${filename} processed successfully`);
            }
          } catch (fileError) {
            throw fileError;
          }
        }
        
      } catch (saveError) {
        console.error('File save error:', saveError);
        // Fallback: provide data URI for manual access
        const extension = filename.toLowerCase().split('.').pop();
        const mimeType = extension === 'pdf' ? 'application/pdf' : 'application/octet-stream';
        const dataUri = `data:${mimeType};base64,${base64Data}`;
        showSuccessToast('File ready - check console for file link');
      }
    } catch (error) {
      console.error('PDF processing error:', error);
      showErrorToast('Failed to process PDF file');
    }
  };

  const downloadFile = async (url: string, filename: string, type: 'invoice' | 'quotation' | 'attachment' | 'dispatch' | 'delivery_challan' | 'dispatch_invoice') => {
    try {
      setDownloading(filename);
      
      let downloadUrl: string;
      // Get token from storage
      const { tokenStorage } = require('@/utils/tokenStorage');
      const token = await tokenStorage.getAccessToken();
      
      switch (type) {
        case 'invoice':
          downloadUrl = `${apiService.baseURL}/invoices/${url}/pdf`;
          break;
        case 'quotation':
          downloadUrl = `${apiService.baseURL}/orders/${url}/estimate-pdf`;
          break;
        case 'dispatch':
          downloadUrl = `${apiService.baseURL}/dispatches/${url}/pdf`;
          break;
        case 'dispatch_invoice':
          downloadUrl = `${apiService.baseURL}/dispatches/${url}/invoice/pdf`;
          break;
        case 'delivery_challan':
          downloadUrl = `${apiService.baseURL}/dispatches/${url}/dc/pdf`;
          break;
        case 'attachment':
          downloadUrl = `${apiService.baseURL}/attachments/download/${url}`;
          break;
        default:
          downloadUrl = `${apiService.baseURL}/attachments/download/${url}`;
      }

      // Use authenticated API service for all PDF downloads
      if (type === 'quotation') {
        try {
          const blob = await apiService.downloadOrderQuotationPdf(url);
          await handleFileBlob(blob, filename);
        } catch (apiError: any) {
          console.error('API quotation download error:', apiError);
          if (apiError.response?.status === 401) {
            showErrorToast('Authentication failed. Please login again.');
          } else if (apiError.response?.status === 400) {
            showErrorToast('Quotation not available for this order status');
          } else {
            showErrorToast(`Failed to download quotation: ${apiError.response?.data?.detail || apiError.message}`);
          }
          throw apiError;
        }
      } else if (type === 'dispatch_invoice') {
        // Use authenticated API service for dispatch invoice
        try {
          const blob = await apiService.downloadDispatchInvoicePdf(url);
          await handleFileBlob(blob, filename);
        } catch (apiError: any) {
          console.error('API dispatch invoice download error:', apiError);
          if (apiError.response?.status === 401) {
            showErrorToast('Authentication failed. Please login again.');
          } else if (apiError.response?.status === 404) {
            showErrorToast('Invoice not found');
          } else {
            showErrorToast(`Failed to download invoice: ${apiError.response?.data?.detail || apiError.message}`);
          }
          throw apiError;
        }
      } else if (type === 'delivery_challan') {
        // Use authenticated API service for delivery challan
        try {
          const blob = await apiService.downloadDispatchDcPdf(url);
          await handleFileBlob(blob, filename);
        } catch (apiError: any) {
          console.error('API delivery challan download error:', apiError);
          if (apiError.response?.status === 401) {
            showErrorToast('Authentication failed. Please login again.');
          } else if (apiError.response?.status === 404) {
            showErrorToast('Delivery challan not found');
          } else {
            showErrorToast(`Failed to download delivery challan: ${apiError.response?.data?.detail || apiError.message}`);
          }
          throw apiError;
        }
      } else if (type === 'attachment') {
        // Use authenticated API service for attachments
        try {
          const blob = await apiService.downloadAttachment(url);
          await handleFileBlob(blob, filename);
        } catch (apiError: any) {
          if (apiError.response?.status === 401) {
            showErrorToast('Authentication failed. Please login again.');
          } else if (apiError.response?.status === 404) {
            showErrorToast('Attachment not found');
          } else {
            showErrorToast(`Failed to download attachment: ${apiError.response?.data?.detail || apiError.message}`);
          }
          // Don't re-throw the error to prevent falling through to the else block
          return;
        }
      } else {
        // For other file types, use the direct URL approach
        const authenticatedUrl = `${downloadUrl}`;
        
        if (await Linking.canOpenURL(authenticatedUrl)) {
          await Linking.openURL(authenticatedUrl);
          showSuccessToast(`Opening ${type}...`);
        } else {
          throw new Error(`Cannot open ${type} URL`);
        }
      }
    } catch (error: any) {
      console.error('Download error:', error);
      showErrorToast('Failed to download file');
    } finally {
      setDownloading(null);
    }
  };


  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'draft': return '#6b7280';
      case 'pending_approval': return '#f59e0b';
      case 'approved': return '#10b981';
      case 'completed': return '#059669';
      case 'cancelled': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const renderOrderHeader = () => (
    <View style={styles.header}>
      <View style={styles.headerRow}>
        <Text style={styles.orderNumber}>{currentOrder?.order_number}</Text>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(currentOrder?.status || '') }]}>
          <Text style={styles.statusText}>{currentOrder?.status?.replace('_', ' ').toUpperCase()}</Text>
        </View>
      </View>
      
      <Text style={styles.customerName}>
        {currentOrder?.customer?.name || currentOrder?.customer?.hospital_name}
      </Text>
      
      <View style={styles.metaRow}>
        <View style={styles.metaItem}>
          <Icon name="flag" size={16} color="#6b7280" />
          <Text style={styles.metaText}>{currentOrder?.priority?.toUpperCase()}</Text>
        </View>
        <View style={styles.metaItem}>
          <Icon name="time" size={16} color="#6b7280" />
          <Text style={styles.metaText}>
            {currentOrder?.created_at ? new Date(currentOrder.created_at).toLocaleDateString() : ''}
          </Text>
        </View>
      </View>
    </View>
  );

  const renderOrderItems = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Order Items</Text>
      {currentOrder?.items?.map((item, index) => (
        <View key={item.id} style={styles.orderItem}>
          <View style={styles.itemHeader}>
            <Text style={styles.itemNumber}>Item {index + 1}</Text>
            <View style={[styles.itemStatusBadge, { 
              backgroundColor: item.status === 'decoded' ? '#10b981' : '#f59e0b' 
            }]}>
              <Text style={styles.itemStatusText}>
                {item.status === 'decoded' ? 'DECODED' : 'PENDING'}
              </Text>
            </View>
          </View>
          
          <Text style={styles.itemDescription}>{item.item_description}</Text>
          
          <View style={styles.itemMeta}>
            <Text style={styles.itemMetaText}>Qty: {item.quantity}</Text>
            {item.inventory && (
              <Text style={styles.itemMetaText}>Catalog No: {item.inventory.sku}</Text>
            )}
            {item.unit_price && (
              <Text style={styles.itemMetaText}>₹{item.unit_price}</Text>
            )}
          </View>
          
          {item.inventory && (
            <View style={styles.decodedInfo}>
              <Icon name="checkmark-circle" size={16} color="#10b981" />
              <Text style={styles.decodedText}>
                Decoded to: {item.inventory.description || item.inventory.sku}
              </Text>
            </View>
          )}
        </View>
      ))}
    </View>
  );

  const renderDocuments = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Documents</Text>
      
      {/* Invoices */}
      {invoices.length > 0 && (
        <View style={styles.documentGroup}>
          <Text style={styles.documentGroupTitle}>Invoices</Text>
          {invoices.map((invoice) => (
            <TouchableOpacity
              key={invoice.id}
              style={styles.documentItem}
              onPress={() => downloadFile(invoice.id, `Invoice_${invoice.invoice_number}.pdf`, 'invoice')}
              disabled={downloading === `Invoice_${invoice.invoice_number}.pdf`}
            >
              <View style={styles.documentInfo}>
                <Icon name="receipt" size={20} color="#ef4444" />
                <View style={styles.documentText}>
                  <Text style={styles.documentName}>{invoice.invoice_number}</Text>
                  <Text style={styles.documentMeta}>₹{invoice.total_amount} • {invoice.payment_status}</Text>
                </View>
              </View>
              <Icon 
                name={downloading === `Invoice_${invoice.invoice_number}.pdf` ? "hourglass" : "download"} 
                size={20} 
                color="#6b7280" 
              />
            </TouchableOpacity>
          ))}
        </View>
      )}
      
      {/* Quotations */}
      {(() => {
        console.log('Rendering quotations section, quotations.length:', quotations.length);
        return null;
      })()}
      {/* Always show quotations section for debugging */}
      <View style={styles.documentGroup}>
        <Text style={styles.documentGroupTitle}>Quotations ({quotations.length})</Text>
        {quotations.length === 0 && (
          <Text style={styles.emptyText}>No quotations available (Status: {currentOrder?.status})</Text>
        )}
        {quotations.length > 0 && (
          <>
            <Text style={styles.emptyText}>Found {quotations.length} quotation(s)</Text>
            {quotations.map((quotation) => (
              <TouchableOpacity
                key={quotation.id}
                style={styles.documentItem}
                onPress={() => downloadFile(quotation.id, `Quotation_${quotation.quote_number}.pdf`, 'quotation')}
                disabled={downloading === `Quotation_${quotation.quote_number}.pdf`}
              >
                <View style={styles.documentInfo}>
                  <Icon name="document-text" size={20} color="#3b82f6" />
                  <View style={styles.documentText}>
                    <Text style={styles.documentName}>{quotation.quote_number}</Text>
                    <Text style={styles.documentMeta}>₹{quotation.total_amount} • {quotation.status}</Text>
                  </View>
                </View>
                <Icon 
                  name={downloading === `Quotation_${quotation.quote_number}.pdf` ? "hourglass" : "download"} 
                  size={20} 
                  color="#6b7280" 
                />
              </TouchableOpacity>
            ))}
          </>
        )}
      </View>
      
    </View>
  );

  const uploadPurchaseOrder = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/*'],
        copyToCacheDirectory: true,
      });

      if (result.assets && result.assets.length > 0) {
        const file = result.assets[0];
        const formData = new FormData();
        formData.append('file', {
          uri: file.uri,
          type: file.mimeType || 'application/pdf',
          name: file.name || 'purchase_order.pdf',
        } as any);
        formData.append('description', 'Purchase Order');

        await apiService.uploadAttachment('order', orderId, formData);
        showSuccessToast('Purchase Order uploaded successfully');
        await loadOrderDocuments();
      }
    } catch (error: any) {
      console.error('Failed to upload PO:', error);
      showErrorToast('Failed to upload Purchase Order');
    }
  };

  const renderDispatchDetails = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Dispatches ({dispatches.length})</Text>
      {dispatches.length > 0 ? (
        <>
          {dispatches.map((dispatch) => (
            <View key={dispatch.id} style={styles.dispatchCard}>
              {/* Dispatch Header */}
              <View style={styles.dispatchHeader}>
                <View style={styles.dispatchInfo}>
                  <Icon name="car" size={24} color="#10b981" />
                  <View style={styles.dispatchText}>
                    <Text style={styles.dispatchNumber}>{dispatch.dispatch_number}</Text>
                    <Text style={styles.dispatchDate}>
                      {dispatch.dispatch_date ? new Date(dispatch.dispatch_date).toLocaleDateString() : 'No date'}
                    </Text>
                  </View>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: dispatch.status === 'delivered' ? '#10b981' : dispatch.status === 'in_transit' ? '#3b82f6' : '#f59e0b' }]}>
                  <Text style={styles.statusText}>{dispatch.status.replace('_', ' ').toUpperCase()}</Text>
                </View>
              </View>
              
              {/* Dispatch Details */}
              {dispatch.tracking_number && (
                <View style={styles.trackingInfo}>
                  <Icon name="location" size={16} color="#6b7280" />
                  <Text style={styles.trackingText}>Tracking: {dispatch.tracking_number}</Text>
                </View>
              )}
              
              {dispatch.notes && (
                <Text style={styles.dispatchNotes}>{dispatch.notes}</Text>
              )}
              
              {/* Download Actions */}
              <View style={styles.dispatchActions}>
                <Text style={styles.actionsTitle}>Download Documents:</Text>
                <View style={styles.actionButtons}>
                  {/* Download Invoice */}
                  <TouchableOpacity
                    style={styles.actionButton}
                    onPress={() => downloadFile(dispatch.id, `Invoice_${dispatch.dispatch_number}.pdf`, 'dispatch_invoice')}
                    disabled={downloading === `Invoice_${dispatch.dispatch_number}.pdf`}
                  >
                    <Icon name="receipt" size={18} color="#ef4444" />
                    <Text style={styles.actionButtonText}>Invoice</Text>
                    <Icon 
                      name={downloading === `Invoice_${dispatch.dispatch_number}.pdf` ? "hourglass" : "download"} 
                      size={16} 
                      color="#6b7280" 
                    />
                  </TouchableOpacity>
                  
                  {/* Download Delivery Challan */}
                  <TouchableOpacity
                    style={styles.actionButton}
                    onPress={() => downloadFile(dispatch.id, `DC_${dispatch.dispatch_number}.pdf`, 'delivery_challan')}
                    disabled={downloading === `DC_${dispatch.dispatch_number}.pdf`}
                  >
                    <Icon name="document-text" size={18} color="#f59e0b" />
                    <Text style={styles.actionButtonText}>Delivery Challan</Text>
                    <Icon 
                      name={downloading === `DC_${dispatch.dispatch_number}.pdf` ? "hourglass" : "download"} 
                      size={16} 
                      color="#6b7280" 
                    />
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          ))}
        </>
      ) : (
        <Text style={styles.emptyText}>No dispatches available</Text>
      )}
    </View>
  );

  const renderAttachments = () => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Attachments</Text>
        <TouchableOpacity onPress={uploadPurchaseOrder} style={styles.uploadButton}>
          <Icon name="cloud-upload" size={20} color="#2563eb" />
          <Text style={styles.uploadButtonText}>Upload PO</Text>
        </TouchableOpacity>
      </View>
      
      {attachments.length === 0 ? (
        <Text style={styles.emptyText}>No attachments</Text>
      ) : (
        attachments.map((attachment) => (
          <TouchableOpacity
            key={attachment.id}
            style={styles.attachmentItem}
            onPress={() => downloadFile(attachment.id, attachment.original_filename, 'attachment')}
            disabled={downloading === attachment.original_filename}
          >
            <View style={styles.attachmentInfo}>
              <Icon name="attach" size={20} color="#6b7280" />
              <View style={styles.attachmentText}>
                <Text style={styles.attachmentName}>{attachment.original_filename}</Text>
                <Text style={styles.attachmentMeta}>
                  {(attachment.file_size / 1024).toFixed(1)} KB • {attachment.file_type}
                </Text>
              </View>
            </View>
            <Icon 
              name={downloading === attachment.original_filename ? "hourglass" : "download"} 
              size={20} 
              color="#6b7280" 
            />
          </TouchableOpacity>
        ))
      )}
    </View>
  );

  const renderOrderNotes = () => (
    currentOrder?.notes || currentOrder?.sales_rep_description ? (
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notes</Text>
        {currentOrder.sales_rep_description && (
          <View style={styles.noteItem}>
            <Text style={styles.noteLabel}>Sales Rep Description:</Text>
            <Text style={styles.noteText}>{currentOrder.sales_rep_description}</Text>
          </View>
        )}
        {currentOrder.notes && (
          <View style={styles.noteItem}>
            <Text style={styles.noteLabel}>Additional Notes:</Text>
            <Text style={styles.noteText}>{currentOrder.notes}</Text>
          </View>
        )}
      </View>
    ) : null
  );

  if (isLoading || !currentOrder) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Loading order details...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {renderOrderHeader()}
      {renderOrderItems()}
      {renderDispatchDetails()}
      {renderDocuments()}
      {renderAttachments()}
      {renderOrderNotes()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  content: {
    paddingBottom: 24,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  orderNumber: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  statusText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
  customerName: {
    fontSize: 16,
    color: '#374151',
    marginBottom: 8,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaText: {
    fontSize: 14,
    color: '#6b7280',
    marginLeft: 4,
  },
  section: {
    backgroundColor: '#ffffff',
    margin: 16,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 16,
  },
  orderItem: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  itemNumber: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  itemStatusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  itemStatusText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '600',
  },
  itemDescription: {
    fontSize: 14,
    color: '#1f2937',
    marginBottom: 8,
  },
  itemMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  itemMetaText: {
    fontSize: 12,
    color: '#6b7280',
  },
  decodedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0fdf4',
    padding: 8,
    borderRadius: 6,
  },
  decodedText: {
    fontSize: 12,
    color: '#166534',
    marginLeft: 6,
  },
  documentGroup: {
    marginBottom: 16,
  },
  documentGroupTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  documentItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    marginBottom: 8,
  },
  documentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  documentText: {
    marginLeft: 12,
    flex: 1,
  },
  documentName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1f2937',
  },
  documentMeta: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 2,
  },
  uploadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: '#2563eb',
    borderRadius: 6,
  },
  uploadButtonText: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: '500',
    marginLeft: 4,
  },
  attachmentItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    marginBottom: 8,
  },
  attachmentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  attachmentText: {
    marginLeft: 12,
    flex: 1,
  },
  attachmentName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1f2937',
  },
  attachmentMeta: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 2,
  },
  emptyText: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  noteItem: {
    marginBottom: 12,
  },
  noteLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 4,
  },
  noteText: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
  },
  // Dispatch styles
  dispatchCard: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    backgroundColor: '#f9fafb',
  },
  dispatchHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  dispatchInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  dispatchText: {
    marginLeft: 12,
    flex: 1,
  },
  dispatchNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
  },
  dispatchDate: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  trackingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  trackingText: {
    fontSize: 14,
    color: '#374151',
    marginLeft: 6,
  },
  dispatchNotes: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 8,
    fontStyle: 'italic',
  },
  dispatchActions: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  actionsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 10,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 6,
  },
  actionButtonText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#374151',
    marginLeft: 6,
    flex: 1,
  },
  dispatchGroup: {
    marginBottom: 8,
  },
  subDocumentItem: {
    marginLeft: 16,
    marginTop: 4,
    backgroundColor: '#f3f4f6',
  },
});

export default OrderDetailsScreen;
