/**
 * Main application component with routing.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import OrdersPage from '@/pages/OrdersPage';
import OrderDetailPage from '@/pages/OrderDetailPage';
import DecodeOrderPage from '@/pages/DecodeOrderPage';
import InventoryPage from '@/pages/InventoryPage';
import CustomersPage from '@/pages/CustomersPage';
import EmployeesPage from '@/pages/EmployeesPage';
import OutstandingPage from '@/pages/OutstandingPage';
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
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
};

const RoleRoute = ({ 
  children, 
  allowedRoles 
}: { 
  children: React.ReactNode; 
  allowedRoles: string[];
}) => {
  const { user } = useAuth();
  
  // Check if user has one of the allowed roles
  const hasRole = allowedRoles.includes(user?.role_name || '');
  
  if (!hasRole) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">Only executives can access this page.</p>
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
};

const SmartRedirect = () => {
  const { user } = useAuth();
  
  // Redirect to first accessible page based on permissions
  if (user?.role?.permissions?.['order:read']) {
    return <Navigate to="/orders" replace />;
  } else if (user?.role?.permissions?.['inventory:read']) {
    return <Navigate to="/inventory" replace />;
  } else if (user?.role?.permissions?.['customer:read']) {
    return <Navigate to="/customers" replace />;
  } else if (user?.role?.permissions?.['user:read']) {
    return <Navigate to="/employees" replace />;
  }
  
  // Fallback to orders if no specific permission found
  return <Navigate to="/orders" replace />;
};

const HomePage = () => {
  const { user } = useAuth();
  
  // Redirect based on role - prioritize workflow pages over dashboard
  // Each role goes to their main workflow page
  if (user?.role_name === 'decoder' || user?.role_name === 'sales_rep' || user?.role_name === 'quoter') {
    return <Navigate to="/orders" replace />;
  }
  
  if (user?.role_name === 'inventory_admin') {
    return <Navigate to="/inventory" replace />;
  }
  
  // Executives and admins go to dashboard if they have permission
  if (user?.role?.permissions?.['dashboard:view']) {
    return <DashboardPage />;
  }
  
  // Otherwise redirect to first accessible page
  return <SmartRedirect />;
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
        <Route index element={<HomePage />} />
        <Route 
          path="dashboard" 
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
          path="orders/:orderId/decode" 
          element={
            <PermissionRoute permission="order:update">
              <DecodeOrderPage />
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
        <Route 
          path="outstanding" 
          element={
            <RoleRoute allowedRoles={['executive']}>
              <OutstandingPage />
            </RoleRoute>
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
