/**
 * Orders List Screen - Main landing screen for sales reps
 * Shows all orders with status information
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { useAppDispatch, useAppSelector } from '@/hooks/redux';
import { fetchOrders } from '@/store/slices/ordersSlice';
import { logoutUser } from '@/store/slices/authSlice';
import { syncOfflineOrders } from '@/store/slices/offlineSlice';
import { Order } from '@/types';

const OrdersListScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  
  const { orders, isLoading } = useAppSelector(state => state.orders);
  const { user } = useAppSelector(state => state.auth);
  const { offlineOrders, isSyncing } = useAppSelector(state => state.offline);
  const { isNetworkConnected } = useAppSelector(state => state.ui);
  
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    try {
      await dispatch(fetchOrders()).unwrap();
    } catch (error) {
      console.error('Failed to load orders:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadOrders();
    
    // Sync offline orders if connected
    if (isNetworkConnected && offlineOrders.length > 0) {
      try {
        await dispatch(syncOfflineOrders()).unwrap();
      } catch (error) {
        console.error('Failed to sync offline orders:', error);
      }
    }
    
    setRefreshing(false);
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Logout', 
          style: 'destructive',
          onPress: () => dispatch(logoutUser())
        },
      ]
    );
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

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'draft': return 'edit';
      case 'pending_approval': return 'hourglass-empty';
      case 'approved': return 'check-circle';
      case 'completed': return 'done-all';
      case 'cancelled': return 'cancel';
      default: return 'help';
    }
  };

  const renderOrderItem = ({ item }: { item: Order }) => (
    <TouchableOpacity
      style={styles.orderCard}
      onPress={() => navigation.navigate('OrderDetails' as never, { orderId: item.id } as never)}
    >
      <View style={styles.orderHeader}>
        <Text style={styles.orderNumber}>{item.order_number}</Text>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Icon name={getStatusIcon(item.status)} size={12} color="#ffffff" />
          <Text style={styles.statusText}>{item.status.replace('_', ' ').toUpperCase()}</Text>
        </View>
      </View>
      
      <Text style={styles.customerName}>
        {item.customer?.name || item.customer?.hospital_name || 'Unknown Customer'}
      </Text>
      
      <View style={styles.orderMeta}>
        <View style={styles.metaItem}>
          <Icon name="flag" size={14} color="#6b7280" />
          <Text style={styles.metaText}>{item.priority.toUpperCase()}</Text>
        </View>
        <View style={styles.metaItem}>
          <Icon name="schedule" size={14} color="#6b7280" />
          <Text style={styles.metaText}>
            {new Date(item.created_at).toLocaleDateString()}
          </Text>
        </View>
        {item.items && (
          <View style={styles.metaItem}>
            <Icon name="list" size={14} color="#6b7280" />
            <Text style={styles.metaText}>{item.items.length} items</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.headerLeft}>
        <Text style={styles.greeting}>Hello, {user?.name || user?.full_name}!</Text>
        <Text style={styles.subtitle}>Your Orders</Text>
      </View>
      <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
        <Icon name="logout" size={24} color="#ef4444" />
      </TouchableOpacity>
    </View>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <Icon name="assignment" size={64} color="#d1d5db" />
      <Text style={styles.emptyTitle}>No Orders Yet</Text>
      <Text style={styles.emptySubtitle}>
        Create your first order to get started
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      {renderHeader()}
      
      {/* Network Status */}
      {!isNetworkConnected && (
        <View style={styles.offlineBanner}>
          <Icon name="wifi-off" size={16} color="#ffffff" />
          <Text style={styles.offlineText}>You're offline</Text>
        </View>
      )}
      
      {/* Offline Orders Count */}
      {offlineOrders.length > 0 && (
        <View style={styles.offlineOrdersBanner}>
          <Icon name="cloud-upload" size={16} color="#f59e0b" />
          <Text style={styles.offlineOrdersText}>
            {offlineOrders.filter(o => !o.synced).length} orders pending sync
          </Text>
        </View>
      )}

      <FlatList
        data={orders}
        renderItem={renderOrderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={orders.length === 0 ? styles.emptyContainer : styles.listContainer}
        ListEmptyComponent={renderEmptyState}
        refreshControl={
          <RefreshControl 
            refreshing={refreshing || isLoading || isSyncing} 
            onRefresh={onRefresh} 
          />
        }
      />

      {/* Floating Action Button */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('CreateOrder' as never)}
      >
        <Icon name="add" size={24} color="#ffffff" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerLeft: {
    flex: 1,
  },
  greeting: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  logoutButton: {
    padding: 8,
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ef4444',
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  offlineText: {
    color: '#ffffff',
    fontSize: 14,
    marginLeft: 8,
    fontWeight: '500',
  },
  offlineOrdersBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fef3c7',
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  offlineOrdersText: {
    color: '#92400e',
    fontSize: 14,
    marginLeft: 8,
    fontWeight: '500',
  },
  listContainer: {
    padding: 16,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  orderCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  orderNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '600',
    marginLeft: 4,
  },
  customerName: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
  },
  orderMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaText: {
    fontSize: 12,
    color: '#6b7280',
    marginLeft: 4,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#374151',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginTop: 8,
  },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2563eb',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
});

export default OrdersListScreen;
