/**
 * Main application component with routing.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import OrdersPage from '@/pages/OrdersPage';
import OrderDetailPage from '@/pages/OrderDetailPage';
import InventoryPage from '@/pages/InventoryPage';
import CustomersPage from '@/pages/CustomersPage';
import EmployeesPage from '@/pages/EmployeesPage';
import Layout from '@/components/Layout';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const PermissionRoute = ({ 
  children, 
  permission 
}: { 
  children: React.ReactNode; 
  permission: string;
}) => {
  const { user } = useAuth();
  
  // Check if user has the required permission
  const hasPermission = user?.role?.permissions?.[permission] === true;
  
  if (!hasPermission) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">You don't have permission to access this page.</p>
          <Navigate to="/" replace />
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route 
          index 
          element={
            <PermissionRoute permission="dashboard:view">
              <DashboardPage />
            </PermissionRoute>
          } 
        />
        <Route 
          path="orders" 
          element={
            <PermissionRoute permission="order:read">
              <OrdersPage />
            </PermissionRoute>
          } 
        />
        <Route 
          path="orders/:orderId" 
          element={
            <PermissionRoute permission="order:read">
              <OrderDetailPage />
            </PermissionRoute>
          } 
        />
        <Route 
          path="inventory" 
          element={
            <PermissionRoute permission="inventory:read">
              <InventoryPage />
            </PermissionRoute>
          } 
        />
        <Route 
          path="customers" 
          element={
            <PermissionRoute permission="customer:read">
              <CustomersPage />
            </PermissionRoute>
          } 
        />
        <Route 
          path="employees" 
          element={
            <PermissionRoute permission="user:read">
              <EmployeesPage />
            </PermissionRoute>
          } 
        />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
