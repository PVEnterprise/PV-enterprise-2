/**
 * Offline slice for Redux store
 * Manages offline orders and sync operations
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { OfflineOrder, CreateOrderRequest } from '@/types';
import apiService from '@/services/api';
import { showSuccessToast, showErrorToast } from '@/utils/toast';

interface OfflineState {
  offlineOrders: OfflineOrder[];
  isSyncing: boolean;
  lastSyncTime: string | null;
}

const initialState: OfflineState = {
  offlineOrders: [],
  isSyncing: false,
  lastSyncTime: null,
};

// Generate unique ID for offline orders
const generateOfflineId = (): string => {
  return `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Async thunks
export const syncOfflineOrders = createAsyncThunk(
  'offline/syncOrders',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as any;
      const offlineOrders = state.offline.offlineOrders;
      
      const syncResults = [];
      
      for (const offlineOrder of offlineOrders) {
        if (!offlineOrder.synced) {
          try {
            const { id, created_at, synced, ...orderData } = offlineOrder;
            const syncedOrder = await apiService.createOrder(orderData);
            syncResults.push({ offlineId: id, syncedOrder, success: true });
          } catch (error) {
            console.error(`Failed to sync order ${offlineOrder.id}:`, error);
            syncResults.push({ offlineId: offlineOrder.id, error, success: false });
          }
        }
      }
      
      const successCount = syncResults.filter(r => r.success).length;
      const failCount = syncResults.filter(r => !r.success).length;
      
      if (successCount > 0) {
        showSuccessToast(`${successCount} orders synced successfully`);
      }
      if (failCount > 0) {
        showErrorToast(`${failCount} orders failed to sync`);
      }
      
      return syncResults;
    } catch (error: any) {
      const message = 'Failed to sync offline orders';
      showErrorToast(message);
      return rejectWithValue(message);
    }
  }
);

const offlineSlice = createSlice({
  name: 'offline',
  initialState,
  reducers: {
    addOfflineOrder: (state, action: PayloadAction<CreateOrderRequest>) => {
      const offlineOrder: OfflineOrder = {
        ...action.payload,
        id: generateOfflineId(),
        created_at: new Date().toISOString(),
        synced: false,
      };
      state.offlineOrders.push(offlineOrder);
    },
    
    markOrderSynced: (state, action: PayloadAction<string>) => {
      const order = state.offlineOrders.find(o => o.id === action.payload);
      if (order) {
        order.synced = true;
      }
    },
    
    removeOfflineOrder: (state, action: PayloadAction<string>) => {
      state.offlineOrders = state.offlineOrders.filter(o => o.id !== action.payload);
    },
    
    clearSyncedOrders: (state) => {
      state.offlineOrders = state.offlineOrders.filter(o => !o.synced);
    },
    
    setLastSyncTime: (state, action: PayloadAction<string>) => {
      state.lastSyncTime = action.payload;
    },
  },
  
  extraReducers: (builder) => {
    builder
      .addCase(syncOfflineOrders.pending, (state) => {
        state.isSyncing = true;
      })
      .addCase(syncOfflineOrders.fulfilled, (state, action) => {
        state.isSyncing = false;
        state.lastSyncTime = new Date().toISOString();
        
        // Mark successfully synced orders
        action.payload.forEach((result: any) => {
          if (result.success) {
            const order = state.offlineOrders.find(o => o.id === result.offlineId);
            if (order) {
              order.synced = true;
            }
          }
        });
      })
      .addCase(syncOfflineOrders.rejected, (state) => {
        state.isSyncing = false;
      });
  },
});

export const {
  addOfflineOrder,
  markOrderSynced,
  removeOfflineOrder,
  clearSyncedOrders,
  setLastSyncTime,
} = offlineSlice.actions;

export default offlineSlice.reducer;
