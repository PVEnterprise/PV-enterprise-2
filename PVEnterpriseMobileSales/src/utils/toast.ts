/**
 * Toast utility functions for showing success, error, and info messages
 * Uses react-native-toast-message
 */
import Toast from 'react-native-toast-message';

export const showSuccessToast = (message: string, title?: string) => {
  Toast.show({
    type: 'success',
    text1: title || 'Success',
    text2: message,
    visibilityTime: 3000,
  });
};

export const showErrorToast = (message: string, title?: string) => {
  Toast.show({
    type: 'error',
    text1: title || 'Error',
    text2: message,
    visibilityTime: 4000,
  });
};

export const showInfoToast = (message: string, title?: string) => {
  Toast.show({
    type: 'info',
    text1: title || 'Info',
    text2: message,
    visibilityTime: 3000,
  });
};

export const showWarningToast = (message: string, title?: string) => {
  Toast.show({
    type: 'error', // Using error type for warning (can be customized)
    text1: title || 'Warning',
    text2: message,
    visibilityTime: 3500,
  });
};
