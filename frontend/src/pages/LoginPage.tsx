import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Server, Lock, User, Shield, Key } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');

  const login = useAuthStore((s) => s.login);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const requires2FA = useAuthStore((s) => s.requires2FA);
  const tempUsername = useAuthStore((s) => s.tempUsername);
  const tempPassword = useAuthStore((s) => s.tempPassword);
  const clear2FA = useAuthStore((s) => s.clear2FA);

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (requires2FA) {
        // Complete 2FA login
        const success = await login(tempUsername!, tempPassword!, totpCode);
        if (success) {
          navigate('/');
        }
      } else {
        // Initial login
        const success = await login(username, password);
        if (success) {
          navigate('/');
        }
        // If not successful, 2FA might be required (handled by state)
      }
    } catch {
      // Error is handled in store
    }
  };

  const handleBack = () => {
    clear2FA();
    setTotpCode('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 p-4">
      <div className="w-full max-w-md">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 rounded-xl mb-4">
              {requires2FA ? (
                <Shield className="w-8 h-8 text-green-400" />
              ) : (
                <Server className="w-8 h-8 text-blue-400" />
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-100 mb-2">
              {requires2FA ? 'Two-Factor Authentication' : 'Visit Steven Desk5090'}
            </h1>
            <p className="text-sm text-gray-500">
              {requires2FA
                ? 'Enter the 6-digit code from your authenticator app'
                : 'System Monitor & Terminal Access'}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!requires2FA ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Username
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                      placeholder="Enter username"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                      placeholder="Enter password"
                      required
                    />
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <p className="text-sm text-green-400 text-center">
                    Authenticating as <strong>{tempUsername}</strong>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    2FA Code
                  </label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input
                      type="text"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500 transition-all text-center tracking-widest text-lg"
                      placeholder="000000"
                      required
                      autoFocus
                      maxLength={6}
                      inputMode="numeric"
                    />
                  </div>
                  <p className="mt-2 text-xs text-gray-500 text-center">
                    Enter code from Google Authenticator or backup code
                  </p>
                </div>
              </>
            )}

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || (requires2FA && totpCode.length !== 6)}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {requires2FA ? 'Verifying...' : 'Signing in...'}
                </>
              ) : requires2FA ? (
                'Verify 2FA Code'
              ) : (
                'Sign In'
              )}
            </button>

            {requires2FA && (
              <button
                type="button"
                onClick={handleBack}
                className="w-full py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium rounded-lg transition-colors"
              >
                Back to Login
              </button>
            )}
          </form>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-gray-800 text-center">
            <p className="text-xs text-gray-600">
              Secure system access. Unauthorized use prohibited.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
