import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Terminal, LogOut, Zap, BarChart3, Settings } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

export default function Layout() {
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold text-gray-100">Visit Steven Desk5090</h1>
          <p className="text-xs text-gray-500 mt-1">System Monitor & Terminal</p>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`
            }
          >
            <LayoutDashboard className="w-5 h-5" />
            <span className="font-medium">Dashboard</span>
          </NavLink>

          <NavLink
            to="/terminal"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`
            }
          >
            <Terminal className="w-5 h-5" />
            <span className="font-medium">Terminal</span>
          </NavLink>

          <div className="pt-4 pb-2">
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-4">Power & Energy</p>
          </div>

          <NavLink
            to="/power"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`
            }
          >
            <Zap className="w-5 h-5" />
            <span className="font-medium">Live Power</span>
          </NavLink>

          <NavLink
            to="/power/history"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`
            }
          >
            <BarChart3 className="w-5 h-5" />
            <span className="font-medium">Energy History</span>
          </NavLink>
        </nav>

        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm">
              <p className="text-gray-300">{username || 'User'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-gray-700 text-gray-200 border border-gray-600'
                  : 'text-gray-500 hover:bg-gray-800 hover:text-gray-300'
              }`
            }
          >
            <Settings className="w-4 h-4" />
            <span className="text-sm font-medium">Settings</span>
          </NavLink>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
