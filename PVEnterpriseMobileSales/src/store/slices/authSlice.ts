/**
 * Authentication slice for Redux store
 * Manages user authentication state
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { User, LoginRequest, AuthResponse } from '@/types';
import apiService from '@/services/api';
import { tokenStorage } from '@/utils/tokenStorage';
import { showSuccessToast, showErrorToast } from '@/utils/toast';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

// Async thunks
export const loginUser = createAsyncThunk(
  'auth/login',
  async (credentials: LoginRequest, { rejectWithValue }) => {
    try {
      console.log('Attempting login with:', credentials.email);
      const authResponse: AuthResponse = await apiService.login(credentials);
      console.log('Login response received:', !!authResponse.access_token);
      
      await tokenStorage.storeTokens(authResponse.access_token, authResponse.refresh_token);
      
      const user: User = await apiService.getCurrentUser();
      showSuccessToast('Login successful!');
      
      return { user, tokens: authResponse };
    } catch (error: any) {
      console.error('Login error:', error);
      let message = 'Login failed';
      
      if (error.response) {
        // Server responded with error status
        message = error.response.data?.detail || error.response.data?.message || `Server error: ${error.response.status}`;
      } else if (error.request) {
        // Request was made but no response received
        message = 'Network error. Please check your connection.';
      } else {
        // Something else happened
        message = error.message || 'An unexpected error occurred';
      }
      
      showErrorToast(message);
      return rejectWithValue(message);
    }
  }
);

export const getCurrentUser = createAsyncThunk(
  'auth/getCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const user: User = await apiService.getCurrentUser();
      return user;
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to get user info';
      return rejectWithValue(message);
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await apiService.logout();
      showSuccessToast('Logged out successfully');
    } catch (error: any) {
      // Even if logout API fails, we should clear local tokens
      console.error('Logout API error:', error);
    } finally {
      await tokenStorage.clearTokens();
    }
  }
);

export const checkAuthStatus = createAsyncThunk(
  'auth/checkStatus',
  async (_, { rejectWithValue }) => {
    try {
      const hasTokens = await tokenStorage.hasTokens();
      if (hasTokens) {
        const user: User = await apiService.getCurrentUser();
        return user;
      }
      return null;
    } catch (error: any) {
      await tokenStorage.clearTokens();
      return null;
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
    },
    clearAuth: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.isAuthenticated = false;
        state.user = null;
      })
      
      // Get current user
      .addCase(getCurrentUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(getCurrentUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Logout
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.error = null;
      })
      
      // Check auth status
      .addCase(checkAuthStatus.fulfilled, (state, action) => {
        if (action.payload) {
          state.user = action.payload;
          state.isAuthenticated = true;
        } else {
          state.user = null;
          state.isAuthenticated = false;
        }
        state.isLoading = false;
      });
  },
});

export const { clearError, setUser, clearAuth } = authSlice.actions;
export default authSlice.reducer;
