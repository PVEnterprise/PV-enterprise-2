/**
 * Create Order Screen with file upload support
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { useAppDispatch, useAppSelector } from '@/hooks/redux';
import { createOrder } from '@/store/slices/ordersSlice';
import { addOfflineOrder } from '@/store/slices/offlineSlice';
import { showSuccessToast, showErrorToast } from '@/utils/toast';
import apiService from '@/services/api';
import { Customer, CreateOrderRequest, CreateOrderItemRequest, FileUpload } from '@/types';

// Import file picker and image picker
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';

const CreateOrderScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  const { isNetworkConnected } = useAppSelector(state => state.ui);
  
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filteredCustomers, setFilteredCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [customerSearch, setCustomerSearch] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'urgent'>('medium');
  const [requirements, setRequirements] = useState('');
  const [notes, setNotes] = useState('');
  const [attachments, setAttachments] = useState<FileUpload[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCustomerPicker, setShowCustomerPicker] = useState(false);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      const customerList = await apiService.getCustomers();
      setCustomers(customerList);
      setFilteredCustomers(customerList);
    } catch (error) {
      console.error('Failed to load customers:', error);
      showErrorToast('Failed to load customers');
    }
  };

  const handleCustomerSearch = (text: string) => {
    setCustomerSearch(text);
    if (text.trim() === '') {
      setFilteredCustomers(customers);
    } else {
      const filtered = customers.filter(customer => 
        (customer.name || customer.hospital_name || '').toLowerCase().includes(text.toLowerCase()) ||
        (customer.city || '').toLowerCase().includes(text.toLowerCase())
      );
      setFilteredCustomers(filtered);
    }
  };


  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/*', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        copyToCacheDirectory: true,
      });

      if (result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        const file: FileUpload = {
          uri: asset.uri,
          type: asset.mimeType || 'application/octet-stream',
          name: asset.name || 'document',
          size: asset.size,
        };
        setAttachments([...attachments, file]);
        showSuccessToast('File added successfully');
      }
    } catch (error: any) {
      showErrorToast('Failed to pick document');
    }
  };

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        const file: FileUpload = {
          uri: asset.uri,
          type: 'image/jpeg',
          name: 'image.jpg',
          size: asset.fileSize,
        };
        setAttachments([...attachments, file]);
        showSuccessToast('Image added successfully');
      }
    } catch (error) {
      showErrorToast('Failed to pick image');
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(attachments.filter((_, i) => i !== index));
  };

  const showFilePicker = () => {
    Alert.alert(
      'Add Attachment',
      'Choose file type',
      [
        { text: 'Camera/Gallery', onPress: pickImage },
        { text: 'Document', onPress: pickDocument },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const validateForm = (): boolean => {
    if (!selectedCustomer) {
      showErrorToast('Please select a customer');
      return false;
    }

    if (!requirements.trim()) {
      showErrorToast('Please describe the requirements');
      return false;
    }

    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setLoading(true);

    try {
      const orderData: CreateOrderRequest = {
        customer_id: selectedCustomer!.id,
        priority,
        source: 'mobile_app',
        sales_rep_description: requirements,
        notes,
      };

      if (isNetworkConnected) {
        // Create order online
        const newOrder = await dispatch(createOrder(orderData)).unwrap();
        
        // Upload attachments if any
        if (attachments.length > 0) {
          await uploadAttachments(newOrder.id);
        }
        
        showSuccessToast('Order created successfully!');
        navigation.goBack();
      } else {
        // Save order offline
        dispatch(addOfflineOrder(orderData));
        showSuccessToast('Order saved offline. Will sync when online.');
        navigation.goBack();
      }
    } catch (error: any) {
      console.error('Failed to create order:', error);
      showErrorToast('Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  const uploadAttachments = async (orderId: string) => {
    for (const file of attachments) {
      try {
        const formData = new FormData();
        formData.append('file', {
          uri: file.uri,
          type: file.type,
          name: file.name,
        } as any);
        formData.append('description', `Order attachment - ${file.name}`);

        await apiService.uploadAttachment('order', orderId, formData);
      } catch (error) {
        console.error('Failed to upload attachment:', error);
        // Don't fail the entire order creation for attachment upload failures
      }
    }
  };

  const renderCustomerPicker = () => (
    <View style={styles.section}>
      <Text style={styles.label}>Customer *</Text>
      {!selectedCustomer ? (
        <>
          <TextInput
            style={styles.input}
            placeholder="Search customers..."
            value={customerSearch}
            onChangeText={handleCustomerSearch}
            onFocus={() => setShowCustomerPicker(true)}
          />
          {showCustomerPicker && (
            <View style={styles.customerList}>
              {filteredCustomers.map((customer) => (
                <TouchableOpacity
                  key={customer.id}
                  style={styles.customerItem}
                  onPress={() => {
                    setSelectedCustomer(customer);
                    setCustomerSearch(customer.name || customer.hospital_name || '');
                    setShowCustomerPicker(false);
                  }}
                >
                  <Text style={styles.customerName}>
                    {customer.name || customer.hospital_name}
                  </Text>
                  {customer.city && (
                    <Text style={styles.customerCity}>{customer.city}</Text>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </>
      ) : (
        <View style={styles.selectedCustomerContainer}>
          <View style={styles.selectedCustomerInfo}>
            <Text style={styles.selectedCustomerName}>
              {selectedCustomer.name || selectedCustomer.hospital_name}
            </Text>
            {selectedCustomer.city && (
              <Text style={styles.selectedCustomerCity}>{selectedCustomer.city}</Text>
            )}
          </View>
          <TouchableOpacity
            onPress={() => {
              setSelectedCustomer(null);
              setCustomerSearch('');
              setShowCustomerPicker(false);
            }}
            style={styles.changeCustomerButton}
          >
            <Icon name="edit" size={20} color="#2563eb" />
            <Text style={styles.changeCustomerText}>Change</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );

  const renderPrioritySelector = () => (
    <View style={styles.section}>
      <Text style={styles.label}>Priority</Text>
      <View style={styles.priorityContainer}>
        {(['low', 'medium', 'high', 'urgent'] as const).map((p) => (
          <TouchableOpacity
            key={p}
            style={[
              styles.priorityButton,
              priority === p && styles.priorityButtonActive
            ]}
            onPress={() => setPriority(p)}
          >
            <Text style={[
              styles.priorityText,
              priority === p && styles.priorityTextActive
            ]}>
              {p.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );


  const renderAttachments = () => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.label}>Attachments</Text>
        <TouchableOpacity onPress={showFilePicker} style={styles.addButton}>
          <Icon name="attach-file" size={20} color="#2563eb" />
          <Text style={styles.addButtonText}>Add File</Text>
        </TouchableOpacity>
      </View>
      
      {attachments.map((file, index) => (
        <View key={index} style={styles.attachmentItem}>
          <View style={styles.attachmentInfo}>
            <Icon name="insert-drive-file" size={20} color="#6b7280" />
            <Text style={styles.attachmentName}>{file.name}</Text>
          </View>
          <TouchableOpacity
            onPress={() => removeAttachment(index)}
            style={styles.removeAttachmentButton}
          >
            <Icon name="close" size={18} color="#ef4444" />
          </TouchableOpacity>
        </View>
      ))}
    </View>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {renderCustomerPicker()}
      {renderPrioritySelector()}
      
      <View style={styles.section}>
        <Text style={styles.label}>Requirements *</Text>
        <TextInput
          style={[styles.input, styles.requirementsTextArea]}
          placeholder="Describe all items needed in detail:

Example:
• 100 boxes of surgical gloves (size M)
• 2 units of X-ray machines  
• 50 pieces of surgical masks

The decoder will map these to inventory items later."
          value={requirements}
          onChangeText={setRequirements}
          multiline
          numberOfLines={8}
        />
      </View>
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.label}>Attachments</Text>
          <TouchableOpacity onPress={showFilePicker} style={styles.addButton}>
            <Icon name="attach-file" size={20} color="#2563eb" />
            <Text style={styles.addButtonText}>Add File</Text>
          </TouchableOpacity>
        </View>
        
        {attachments.map((file, index) => (
          <View key={index} style={styles.attachmentItem}>
            <View style={styles.attachmentInfo}>
              <Icon name="insert-drive-file" size={20} color="#6b7280" />
              <Text style={styles.attachmentName}>{file.name}</Text>
              <Text style={styles.attachmentSize}>
                {file.size ? `(${(file.size / 1024).toFixed(1)} KB)` : ''}
              </Text>
            </View>
            <TouchableOpacity
              onPress={() => removeAttachment(index)}
              style={styles.removeAttachmentButton}
            >
              <Icon name="close" size={18} color="#ef4444" />
            </TouchableOpacity>
          </View>
        ))}
        
        {attachments.length === 0 && (
          <Text style={styles.attachmentHint}>
            Upload supporting documents (PDF, Word, Excel, Images)
          </Text>
        )}
      </View>
      
      <View style={styles.section}>
        <Text style={styles.label}>Notes</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Additional notes..."
          value={notes}
          onChangeText={setNotes}
          multiline
          numberOfLines={2}
        />
      </View>

      <TouchableOpacity
        style={[styles.submitButton, loading && styles.submitButtonDisabled]}
        onPress={handleSubmit}
        disabled={loading}
      >
        <Text style={styles.submitButtonText}>
          {loading ? 'Creating Order...' : 'Create Order'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  content: {
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: '#ffffff',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  customerSelector: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: '#ffffff',
  },
  selectedCustomer: {
    fontSize: 16,
    color: '#1f2937',
  },
  placeholder: {
    fontSize: 16,
    color: '#9ca3af',
  },
  customerList: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    backgroundColor: '#ffffff',
    marginTop: 4,
    maxHeight: 200,
  },
  customerItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  customerName: {
    fontSize: 16,
    color: '#1f2937',
    fontWeight: '500',
  },
  customerCity: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  priorityContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  priorityButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 6,
    marginHorizontal: 2,
    alignItems: 'center',
    backgroundColor: '#ffffff',
  },
  priorityButtonActive: {
    backgroundColor: '#2563eb',
    borderColor: '#2563eb',
  },
  priorityText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
  },
  priorityTextActive: {
    color: '#ffffff',
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  addButtonText: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: '500',
    marginLeft: 4,
  },
  attachmentItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  attachmentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  attachmentName: {
    fontSize: 14,
    color: '#374151',
    marginLeft: 8,
    flex: 1,
  },
  removeAttachmentButton: {
    padding: 4,
  },
  submitButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 32,
  },
  submitButtonDisabled: {
    backgroundColor: '#9ca3af',
  },
  submitButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  // New styles for updated UI
  selectedCustomerContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#10b981',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: '#f0fdf4',
  },
  selectedCustomerInfo: {
    flex: 1,
  },
  selectedCustomerName: {
    fontSize: 16,
    color: '#1f2937',
    fontWeight: '600',
  },
  selectedCustomerCity: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  changeCustomerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  changeCustomerText: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: '500',
    marginLeft: 4,
  },
  requirementsTextArea: {
    height: 120,
    textAlignVertical: 'top',
  },
  attachmentSize: {
    fontSize: 12,
    color: '#9ca3af',
    marginLeft: 4,
  },
  attachmentHint: {
    fontSize: 14,
    color: '#9ca3af',
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 16,
  },
});

export default CreateOrderScreen;
