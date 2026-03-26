import { useState, useEffect } from 'react';
import { Shield, Key, AlertTriangle, Check, Copy, Lock, Smartphone, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { setup2FA, verify2FA, disable2FA, changePassword } from '../api/auth';
import api from '../api/client';

export default function SettingsPage() {
  const username = useAuthStore((s) => s.username);
  const [has2FA, setHas2FA] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 2FA Setup state
  const [showSetup, setShowSetup] = useState(false);
  const [password, setPassword] = useState('');
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [setupStep, setSetupStep] = useState<'password' | 'qr' | 'backup'>('password');

  // Disable 2FA state
  const [showDisable, setShowDisable] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');

  // Password change state
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordStrength, setPasswordStrength] = useState<string | null>(null);

  // Device management state
  const [devices, setDevices] = useState<any[]>([]);
  const [deviceLimit, setDeviceLimit] = useState(5);
  const [requireRegisteredDevice, setRequireRegisteredDevice] = useState(false);
  const [newDeviceName, setNewDeviceName] = useState('');
  const [showRegisterDevice, setShowRegisterDevice] = useState(false);

  useEffect(() => {
    // Check if user has 2FA enabled
    const check2FA = async () => {
      try {
        const { getMe } = await import('../api/auth');
        const user = await getMe();
        setHas2FA(user.has_2fa);
      } catch {
        // Ignore error
      }
    };
    check2FA();

    // Fetch registered devices
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const response = await api.get('/auth/devices');
      setDevices(response.data.devices || []);
      setDeviceLimit(response.data.max_devices || 5);
      setRequireRegisteredDevice(response.data.require_registered_device || false);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
    }
  };

  const handleRegisterDevice = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      await api.post('/auth/devices/register', { device_name: newDeviceName || 'New Device' });
      setSuccess('Device registered successfully');
      setNewDeviceName('');
      setShowRegisterDevice(false);
      fetchDevices();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register device');
    } finally {
      setLoading(false);
    }
  };

  const handleUnregisterDevice = async (deviceId: string) => {
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      await api.post('/auth/devices/unregister', { device_id: deviceId });
      setSuccess('Device unregistered successfully');
      fetchDevices();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to unregister device');
    } finally {
      setLoading(false);
    }
  };

  const toggleDeviceRequirement = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const newValue = !requireRegisteredDevice;
      await api.post('/auth/devices/requirement', { require_registered_device: newValue });
      setRequireRegisteredDevice(newValue);
      setSuccess(`Device registration requirement ${newValue ? 'enabled' : 'disabled'}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update setting');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSetup = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const result = await setup2FA(username!, password);
      setQrCode(result.qr_code);
      setSecret(result.secret);
      setBackupCodes(result.backup_codes);
      setSetupStep('qr');
      // Don't clear password here - needed for verify2FA
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to setup 2FA');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      await verify2FA(username!, password, verificationCode);
      setHas2FA(true);
      setSetupStep('backup');
      setSuccess('2FA enabled successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid verification code');
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      await disable2FA(username!, disablePassword, disableCode);
      setHas2FA(false);
      setShowDisable(false);
      setDisablePassword('');
      setDisableCode('');
      setSuccess('2FA disabled successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to disable 2FA');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
    setTimeout(() => setSuccess(null), 2000);
  };

  const checkPasswordStrength = (password: string): string => {
    const checks = [];
    if (password.length < 12) checks.push('At least 12 characters');
    if (!/[A-Z]/.test(password)) checks.push('One uppercase letter');
    if (!/[a-z]/.test(password)) checks.push('One lowercase letter');
    if (!/\d/.test(password)) checks.push('One digit');
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) checks.push('One special character');
    const common = ['password', '123456', 'qwerty', 'admin', 'letmein'];
    if (common.some(p => password.toLowerCase().includes(p))) checks.push('Avoid common patterns');

    if (checks.length === 0) return 'Strong';
    if (checks.length <= 2) return 'Medium: ' + checks.join(', ');
    return 'Weak: ' + checks.join(', ');
  };

  const handlePasswordChange = async () => {
    setError(null);
    setSuccess(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    const strength = checkPasswordStrength(newPassword);
    if (strength !== 'Strong') {
      setError('Password does not meet complexity requirements: ' + strength);
      return;
    }

    setLoading(true);
    try {
      await changePassword(username!, currentPassword, newPassword);
      setSuccess('Password changed successfully! Please log in again.');
      setShowPasswordChange(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordStrength(null);
      // Log out after password change
      setTimeout(() => {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Settings</h1>

      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-3">
          <Check className="w-5 h-5 text-green-400" />
          <p className="text-green-400">{success}</p>
        </div>
      )}

      {/* 2FA Section */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-green-500/20 rounded-lg">
            <Shield className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-100">Two-Factor Authentication</h2>
            <p className="text-sm text-gray-500">
              {has2FA
                ? '2FA is enabled. Your account is protected.'
                : 'Add an extra layer of security to your account.'}
            </p>
          </div>
        </div>

        {!has2FA ? (
          <div>
            {!showSetup ? (
              <button
                onClick={() => setShowSetup(true)}
                className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-medium rounded-lg transition-colors"
              >
                Enable 2FA
              </button>
            ) : (
              <div className="space-y-4">
                {setupStep === 'password' && (
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">
                      Enter your password to continue
                    </label>
                    <div className="flex gap-3">
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
                        placeholder="Password"
                      />
                      <button
                        onClick={handleStartSetup}
                        disabled={loading || !password}
                        className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-600/50 text-white font-medium rounded-lg"
                      >
                        {loading ? 'Loading...' : 'Continue'}
                      </button>
                    </div>
                  </div>
                )}

                {setupStep === 'qr' && qrCode && (
                  <div className="space-y-4">
                    <div className="p-4 bg-gray-800 rounded-lg">
                      <p className="text-sm text-gray-300 mb-4">
                        1. Scan this QR code with Google Authenticator or Authy:
                      </p>
                      <div className="flex justify-center mb-4">
                        <img src={qrCode} alt="2FA QR Code" className="w-48 h-48" />
                      </div>
                      <p className="text-sm text-gray-400 text-center mb-2">
                        Or enter this code manually:
                      </p>
                      <div className="flex items-center justify-center gap-2">
                        <code className="px-3 py-1 bg-gray-700 rounded text-gray-300 font-mono">
                          {secret}
                        </code>
                        <button
                          onClick={() => secret && copyToClipboard(secret)}
                          className="p-1 hover:bg-gray-700 rounded"
                        >
                          <Copy className="w-4 h-4 text-gray-400" />
                        </button>
                      </div>
                    </div>

                    <div>
                      <p className="text-sm text-gray-300 mb-2">
                        2. Enter the 6-digit code from your authenticator app:
                      </p>
                      <div className="flex gap-3">
                        <input
                          type="text"
                          value={verificationCode}
                          onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                          className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 text-center tracking-widest"
                          placeholder="000000"
                          maxLength={6}
                        />
                        <button
                          onClick={handleVerify}
                          disabled={loading || verificationCode.length !== 6}
                          className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-600/50 text-white font-medium rounded-lg"
                        >
                          {loading ? 'Verifying...' : 'Verify'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {setupStep === 'backup' && backupCodes && (
                  <div className="space-y-4">
                    <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle className="w-5 h-5 text-yellow-400" />
                        <h3 className="font-semibold text-yellow-400">Save Your Backup Codes</h3>
                      </div>
                      <p className="text-sm text-gray-300 mb-4">
                        These codes can be used to access your account if you lose your authenticator device.
                        Save them in a secure location.
                      </p>
                      <div className="grid grid-cols-2 gap-2 mb-4">
                        {backupCodes.map((code, i) => (
                          <code
                            key={i}
                            className="px-3 py-2 bg-gray-800 rounded text-gray-300 font-mono text-center"
                          >
                            {code}
                          </code>
                        ))}
                      </div>
                      <button
                        onClick={() => copyToClipboard(backupCodes.join('\n'))}
                        className="w-full py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg flex items-center justify-center gap-2"
                      >
                        <Copy className="w-4 h-4" />
                        Copy All Codes
                      </button>
                    </div>
                    <button
                      onClick={() => {
                        setShowSetup(false);
                        setSetupStep('password');
                        setQrCode(null);
                        setSecret(null);
                        setBackupCodes(null);
                        setPassword('');
                      }}
                      className="w-full py-2 bg-green-600 hover:bg-green-500 text-white font-medium rounded-lg"
                    >
                      Done
                    </button>
                  </div>
                )}

                <button
                  onClick={() => {
                    setShowSetup(false);
                    setSetupStep('password');
                    setQrCode(null);
                    setPassword('');
                  }}
                  className="text-sm text-gray-500 hover:text-gray-400"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        ) : (
          <div>
            {!showDisable ? (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-green-400">
                  <Check className="w-5 h-5" />
                  <span className="font-medium">2FA is enabled</span>
                </div>
                <button
                  onClick={() => setShowDisable(true)}
                  className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 font-medium rounded-lg transition-colors"
                >
                  Disable 2FA
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-300">
                  Enter your password and current 2FA code to disable:
                </p>
                <input
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
                  placeholder="Password"
                />
                <input
                  type="text"
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 text-center tracking-widest"
                  placeholder="2FA Code"
                  maxLength={6}
                />
                <div className="flex gap-3">
                  <button
                    onClick={handleDisable}
                    disabled={loading || !disablePassword || disableCode.length !== 6}
                    className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-red-600/50 text-white font-medium rounded-lg"
                  >
                    {loading ? 'Disabling...' : 'Disable 2FA'}
                  </button>
                  <button
                    onClick={() => {
                      setShowDisable(false);
                      setDisablePassword('');
                      setDisableCode('');
                    }}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Password Change Section */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Lock className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-100">Password</h2>
            <p className="text-sm text-gray-500">Change your account password</p>
          </div>
        </div>

        {!showPasswordChange ? (
          <button
            onClick={() => setShowPasswordChange(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg transition-colors"
          >
            Change Password
          </button>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <p className="text-sm text-yellow-400 font-medium mb-2">Password Requirements:</p>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• At least 12 characters</li>
                <li>• One uppercase letter (A-Z)</li>
                <li>• One lowercase letter (a-z)</li>
                <li>• One digit (0-9)</li>
                <li>• One special character (!@#$%^&*)</li>
                <li>• No common patterns (password, 123456, etc.)</li>
              </ul>
            </div>

            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Current Password"
            />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => {
                setNewPassword(e.target.value);
                setPasswordStrength(checkPasswordStrength(e.target.value));
              }}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="New Password"
            />
            {passwordStrength && (
              <p className={`text-sm ${passwordStrength === 'Strong' ? 'text-green-400' : 'text-yellow-400'}`}>
                Strength: {passwordStrength}
              </p>
            )}
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Confirm New Password"
            />
            {newPassword !== confirmPassword && confirmPassword && (
              <p className="text-sm text-red-400">Passwords do not match</p>
            )}

            <div className="flex gap-3">
              <button
                onClick={handlePasswordChange}
                disabled={loading || !currentPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 text-white font-medium rounded-lg"
              >
                {loading ? 'Changing...' : 'Change Password'}
              </button>
              <button
                onClick={() => {
                  setShowPasswordChange(false);
                  setCurrentPassword('');
                  setNewPassword('');
                  setConfirmPassword('');
                  setPasswordStrength(null);
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Device Management Section */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-indigo-500/20 rounded-lg">
            <Smartphone className="w-6 h-6 text-indigo-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-100">Registered Devices</h2>
            <p className="text-sm text-gray-500">
              Manage devices allowed to access your account
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">
              {requireRegisteredDevice ? 'Restriction On' : 'Restriction Off'}
            </span>
            <button
              onClick={toggleDeviceRequirement}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors ${
                requireRegisteredDevice
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {requireRegisteredDevice ? <ToggleRight className="w-6 h-6" /> : <ToggleLeft className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {requireRegisteredDevice && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
            <p className="text-sm text-green-400">
              ✅ Device restriction is enabled. Only registered devices can log in.
            </p>
          </div>
        )}

        <div className="space-y-3 mb-4">
          {devices.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No registered devices</p>
          ) : (
            devices.map((device: any) => (
              <div
                key={device.device_id}
                className="flex items-center justify-between p-3 bg-gray-800 rounded-lg"
              >
                <div>
                  <p className="font-medium text-gray-200">{device.device_name}</p>
                  <p className="text-xs text-gray-500">
                    Last used: {new Date(device.last_used).toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-600">
                    IP: {device.ip_address}
                  </p>
                </div>
                <button
                  onClick={() => handleUnregisterDevice(device.device_id)}
                  disabled={loading}
                  className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
          <span>{devices.length} of {deviceLimit} devices registered</span>
        </div>

        {!showRegisterDevice ? (
          <button
            onClick={() => setShowRegisterDevice(true)}
            disabled={devices.length >= deviceLimit}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white font-medium rounded-lg transition-colors"
          >
            Register This Device
          </button>
        ) : (
          <div className="space-y-3">
            <input
              type="text"
              value={newDeviceName}
              onChange={(e) => setNewDeviceName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Device name (e.g., My Laptop, iPhone 15)"
            />
            <div className="flex gap-3">
              <button
                onClick={handleRegisterDevice}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white font-medium rounded-lg"
              >
                {loading ? 'Registering...' : 'Register'}
              </button>
              <button
                onClick={() => {
                  setShowRegisterDevice(false);
                  setNewDeviceName('');
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Security Info */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Key className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-100">Security Information</h2>
            <p className="text-sm text-gray-500">Account security status</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-gray-800">
            <span className="text-gray-400">Username</span>
            <span className="text-gray-200 font-medium">{username}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-800">
            <span className="text-gray-400">Two-Factor Authentication</span>
            <span className={has2FA ? 'text-green-400' : 'text-yellow-400'}>
              {has2FA ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-800">
            <span className="text-gray-400">Registered Devices</span>
            <span className="text-gray-200">{devices.length} / {deviceLimit}</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-gray-400">Session</span>
            <span className="text-green-400">Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
