/**
 * Main layout component with navigation.
 */
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Package, 
  Users, 
  UserCog,
  LogOut,
  Menu,
  X,
  TrendingUp,
  DollarSign
} from 'lucide-react';
import { useState } from 'react';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(false);

  // Role-based navigation - filter based on user permissions
  const allNavigation = [
    { 
      name: 'Dashboard', 
      href: '/', 
      icon: LayoutDashboard,
      permission: 'dashboard:view'
    },
    { 
      name: 'Orders', 
      href: '/orders', 
      icon: ShoppingCart,
      permission: 'order:read'
    },
    { 
      name: 'Pending', 
      href: '/outstanding', 
      icon: TrendingUp,
      roleOnly: 'executive'
    },
    { 
      name: 'Inventory', 
      href: '/inventory', 
      icon: Package,
      permission: 'inventory:read'
    },
    { 
      name: 'Price Lists', 
      href: '/price-lists', 
      icon: DollarSign,
      roles: ['executive', 'quoter']
    },
    { 
      name: 'Customers', 
      href: '/customers', 
      icon: Users,
      permission: 'customer:read'
    },
    { 
      name: 'Employees', 
      href: '/employees', 
      icon: UserCog,
      permission: 'user:read'
    },
  ];

  // Filter navigation based on user permissions
  const navigation = allNavigation.filter((item: any) => {
    // Handle role-only items (like Outstanding for executives)
    if (item.roleOnly) {
      return user?.role_name === item.roleOnly;
    }
    // Handle role-based items (like Price Lists for executive/quoter)
    if (item.roles) {
      return item.roles.includes(user?.role_name);
    }
    
    if (!user?.role?.permissions) return false;
    
    // Dashboard only visible to executive
    if (item.href === '/' && user.role_name !== 'executive') {
      return false;
    }
    
    // Employees module only visible to executive (admin)
    if (item.href === '/employees' && user.role_name !== 'executive') {
      return false;
    }
    
    return user.role.permissions[item.permission] === true;
  });

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation - Sticky */}
      <nav className="sticky top-0 z-50 bg-white shadow-sm border-b border-gray-200">
        <div className="mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 rounded-md text-gray-600 hover:bg-gray-100"
              >
                {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
              <h1 className="ml-2 text-xl font-bold text-primary-600">
                SreeDevi Life Sciences
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm">
                <p className="font-medium text-gray-900">{user?.full_name}</p>
                <p className="text-gray-500 capitalize">{user?.role.name.replace('_', ' ')}</p>
              </div>
              <button
                onClick={logout}
                className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
                title="Logout"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="flex">
        {/* Sidebar - Fixed & Collapsed by default, expands on hover */}
        <aside
          className={`${
            sidebarOpen ? 'block' : 'hidden'
          } lg:block ${
            sidebarExpanded ? 'w-64' : 'w-16'
          } bg-white border-r border-gray-200 fixed left-0 top-16 h-[calc(100vh-4rem)] overflow-y-auto transition-all duration-300 ease-in-out z-40`}
          onMouseEnter={() => setSidebarExpanded(true)}
          onMouseLeave={() => setSidebarExpanded(false)}
        >
          <nav className="mt-5 px-2 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`${
                    active
                      ? 'bg-primary-50 text-primary-600'
                      : 'text-gray-600 hover:bg-gray-50'
                  } group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all duration-200`}
                  onClick={() => setSidebarOpen(false)}
                  title={!sidebarExpanded ? item.name : ''}
                >
                  <Icon
                    className={`${
                      active ? 'text-primary-600' : 'text-gray-400 group-hover:text-gray-600'
                    } ${sidebarExpanded ? 'mr-3' : 'mx-auto'} h-5 w-5 flex-shrink-0`}
                  />
                  <span className={`${sidebarExpanded ? 'opacity-100' : 'opacity-0 w-0'} transition-all duration-200 whitespace-nowrap overflow-hidden`}>
                    {item.name}
                  </span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main Content - Add left margin to account for fixed sidebar */}
        <main className={`flex-1 p-6 transition-all duration-300 ${sidebarExpanded ? 'ml-64' : 'ml-16'}`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
