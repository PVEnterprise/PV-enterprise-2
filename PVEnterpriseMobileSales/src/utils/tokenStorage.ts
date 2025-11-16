/**
 * Secure token storage using Expo SecureStore
 * Provides secure storage for JWT tokens instead of AsyncStorage
 */
import * as SecureStore from 'expo-secure-store';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

class TokenStorage {
  async storeTokens(accessToken: string, refreshToken: string): Promise<void> {
    try {
      // Store access token
      await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
      
      // Store refresh token
      await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
    } catch (error) {
      console.error('Error storing tokens:', error);
      throw new Error('Failed to store authentication tokens');
    }
  }

  async getAccessToken(): Promise<string | null> {
    try {
      const token = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
      return token;
    } catch (error) {
      console.error('Error getting access token:', error);
      return null;
    }
  }

  async getRefreshToken(): Promise<string | null> {
    try {
      const token = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      return token;
    } catch (error) {
      console.error('Error getting refresh token:', error);
      return null;
    }
  }

  async clearTokens(): Promise<void> {
    try {
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Error clearing tokens:', error);
    }
  }

  async hasTokens(): Promise<boolean> {
    try {
      const accessToken = await this.getAccessToken();
      const refreshToken = await this.getRefreshToken();
      return !!(accessToken && refreshToken);
    } catch (error) {
      console.error('Error checking tokens:', error);
      return false;
    }
  }
}

export const tokenStorage = new TokenStorage();
