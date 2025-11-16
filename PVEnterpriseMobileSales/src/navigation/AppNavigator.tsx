/**
 * Main App Navigator with authentication flow
 */
import React, { useEffect } from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { useAppSelector, useAppDispatch } from '@/hooks/redux';
import { checkAuthStatus } from '@/store/slices/authSlice';
import { RootStackParamList } from '@/types';

// Screens
import LoginScreen from '@/screens/LoginScreen';
import OrdersListScreen from '@/screens/OrdersListScreen';
import CreateOrderScreen from '@/screens/CreateOrderScreen';
import OrderDetailsScreen from '@/screens/OrderDetailsScreenSimple';
import LoadingScreen from '@/components/LoadingScreen';

const Stack = createStackNavigator<RootStackParamList>();

const AppNavigator: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated, isLoading } = useAppSelector(state => state.auth);

  useEffect(() => {
    // Check if user is already authenticated on app start
    dispatch(checkAuthStatus());
  }, [dispatch]);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <Stack.Navigator>
      {isAuthenticated ? (
        <>
          <Stack.Screen 
            name="OrdersList" 
            component={OrdersListScreen}
            options={{ title: 'My Orders' }}
          />
          <Stack.Screen 
            name="CreateOrder" 
            component={CreateOrderScreen}
            options={{ title: 'Create Order' }}
          />
          <Stack.Screen 
            name="OrderDetails" 
            component={OrderDetailsScreen}
            options={{ title: 'Order Details' }}
          />
        </>
      ) : (
        <Stack.Screen 
          name="Login" 
          component={LoginScreen}
          options={{ headerShown: false }}
        />
      )}
    </Stack.Navigator>
  );
};

export default AppNavigator;
