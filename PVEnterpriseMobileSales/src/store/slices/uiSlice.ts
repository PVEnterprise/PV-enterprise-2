/**
 * UI slice for Redux store
 * Manages UI state like loading, modals, etc.
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  isLoading: boolean;
  loadingMessage: string;
  isNetworkConnected: boolean;
  activeModal: string | null;
  refreshing: boolean;
}

const initialState: UIState = {
  isLoading: false,
  loadingMessage: '',
  isNetworkConnected: true,
  activeModal: null,
  refreshing: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<{ isLoading: boolean; message?: string }>) => {
      state.isLoading = action.payload.isLoading;
      state.loadingMessage = action.payload.message || '';
    },
    
    setNetworkStatus: (state, action: PayloadAction<boolean>) => {
      state.isNetworkConnected = action.payload;
    },
    
    setActiveModal: (state, action: PayloadAction<string | null>) => {
      state.activeModal = action.payload;
    },
    
    setRefreshing: (state, action: PayloadAction<boolean>) => {
      state.refreshing = action.payload;
    },
    
    clearUI: (state) => {
      state.isLoading = false;
      state.loadingMessage = '';
      state.activeModal = null;
      state.refreshing = false;
    },
  },
});

export const {
  setLoading,
  setNetworkStatus,
  setActiveModal,
  setRefreshing,
  clearUI,
} = uiSlice.actions;

export default uiSlice.reducer;
