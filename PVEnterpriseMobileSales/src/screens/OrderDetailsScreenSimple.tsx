/**
 * Order Details Screen - Simple version that redirects to full version
 */
import React from 'react';
import OrderDetailsScreen from './OrderDetailsScreen';

// This is a simple wrapper that uses the full-featured OrderDetailsScreen
const OrderDetailsScreenSimple: React.FC = () => {
  return <OrderDetailsScreen />;
};

export default OrderDetailsScreenSimple;
