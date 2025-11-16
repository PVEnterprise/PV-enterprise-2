/**
 * Main App component with Redux Provider and Navigation
 */
import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { NavigationContainer } from '@react-navigation/native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import Toast from 'react-native-toast-message';
import NetInfo from '@react-native-community/netinfo';
import { StyleSheet } from 'react-native';

import { store, persistor } from '@/store';
import AppNavigator from '@/navigation/AppNavigator';
import LoadingScreen from '@/components/LoadingScreen';
import { useAppDispatch } from '@/hooks/redux';
import { setNetworkStatus } from '@/store/slices/uiSlice';

const AppContent: React.FC = () => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // Monitor network connectivity
    const unsubscribe = NetInfo.addEventListener(state => {
      dispatch(setNetworkStatus(state.isConnected ?? false));
    });

    return () => unsubscribe();
  }, [dispatch]);

  return (
    <GestureHandlerRootView style={styles.container}>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
      <Toast />
    </GestureHandlerRootView>
  );
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <PersistGate loading={<LoadingScreen />} persistor={persistor}>
        <AppContent />
      </PersistGate>
    </Provider>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});

export default App;
