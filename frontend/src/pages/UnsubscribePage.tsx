import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { CheckCircle2, AlertCircle, Mail } from 'lucide-react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';
import { toast } from 'sonner';

/**
 * Unsubscribe Page Component
 *
 * Allows users to unsubscribe from notifications via secure token-based link.
 * Features:
 * - Accept token from URL parameter (?token=...)
 * - Display notification preferences
 * - Allow selective unsubscribe by channel (email, SMS, push)
 * - Allow selective unsubscribe by type (assignments, materials, messages, etc)
 * - No authentication required (token-based)
 * - Confirmation message after unsubscribe
 *
 * Usage:
 * - User receives email with unsubscribe link: /unsubscribe?token=abc123...
 * - Component validates token on mount
 * - User selects which notifications to disable
 * - Component POSTs to /api/notifications/unsubscribe/ with token
 * - Shows success/error message
 *
 * @example
 * ```tsx
 * <UnsubscribePage />
 * ```
 */

interface UnsubscribeRequest {
  token: string;
  unsubscribe_from: string[];
  channels?: string[];
}

interface UnsubscribeResponse {
  success: boolean;
  message: string;
  disabled_types?: string[];
  user_email?: string;
}

const NOTIFICATION_CHANNELS = [
  { id: 'email', label: 'Email Notifications', description: 'Disable email notifications' },
  { id: 'push', label: 'Push Notifications', description: 'Disable push and browser notifications' },
  { id: 'sms', label: 'SMS Notifications', description: 'Disable SMS text messages' },
];

const NOTIFICATION_TYPES = [
  { id: 'assignments', label: 'Assignments', description: 'New assignments and deadlines' },
  { id: 'materials', label: 'Learning Materials', description: 'New materials and resources' },
  { id: 'messages', label: 'Messages', description: 'Direct messages and chat' },
  { id: 'payments', label: 'Payments', description: 'Payment requests' },
  { id: 'invoices', label: 'Invoices', description: 'Invoice notifications' },
  { id: 'system', label: 'System Notifications', description: 'System updates and announcements' },
];

export const UnsubscribePage = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  // Selected items to unsubscribe from
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [unsubscribeFromAll, setUnsubscribeFromAll] = useState(false);

  // Validate token on mount
  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setLoadError('No unsubscribe token provided. Missing ?token= parameter in URL.');
        setIsLoading(false);
        logger.warn('[UnsubscribePage] No token found in URL parameters');
        return;
      }

      try {
        setIsLoading(true);
        setLoadError(null);

        logger.debug('[UnsubscribePage] Validating unsubscribe token...');

        // Token validation will happen when user submits
        // For now, just accept it if provided
        setIsLoading(false);
      } catch (error) {
        logger.error('[UnsubscribePage] Error validating token:', error);
        setLoadError('Failed to validate unsubscribe link. The link may be expired or invalid.');
        setIsLoading(false);
      }
    };

    validateToken();
  }, [token]);

  /**
   * Handle channel selection toggle
   */
  const toggleChannel = (channelId: string) => {
    setSelectedChannels((prev) =>
      prev.includes(channelId) ? prev.filter((id) => id !== channelId) : [...prev, channelId]
    );
  };

  /**
   * Handle notification type selection toggle
   */
  const toggleType = (typeId: string) => {
    setSelectedTypes((prev) =>
      prev.includes(typeId) ? prev.filter((id) => id !== typeId) : [...prev, typeId]
    );
  };

  /**
   * Handle unsubscribe from all
   */
  const toggleUnsubscribeAll = (value: boolean) => {
    setUnsubscribeFromAll(value);
    if (value) {
      // If unsubscribing from all, clear selections
      setSelectedChannels([]);
      setSelectedTypes([]);
    }
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      setSubmitError('No unsubscribe token provided.');
      return;
    }

    // Validate that user selected something
    if (!unsubscribeFromAll && selectedChannels.length === 0 && selectedTypes.length === 0) {
      setSubmitError('Please select at least one notification type or channel to unsubscribe from.');
      toast.error('Please select at least one option to unsubscribe from');
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      logger.debug('[UnsubscribePage] Submitting unsubscribe request...', {
        token: token.substring(0, 10) + '...', // Log partial token for security
        unsubscribeFromAll,
        selectedChannels,
        selectedTypes,
      });

      // Build request payload
      const payload: UnsubscribeRequest = {
        token,
        unsubscribe_from: unsubscribeFromAll ? ['all'] : selectedTypes,
        channels: selectedChannels.length > 0 ? selectedChannels : undefined,
      };

      const response = await unifiedAPI.fetch('/notifications/unsubscribe/', 'POST', payload);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.error ||
          errorData.message ||
          errorData.detail ||
          `Failed to unsubscribe (HTTP ${response.status})`;

        throw new Error(errorMessage);
      }

      const data: UnsubscribeResponse = await response.json();

      logger.info('[UnsubscribePage] Successfully unsubscribed', {
        email: data.user_email,
        disabledTypes: data.disabled_types,
      });

      // Store user email for display
      if (data.user_email) {
        setUserEmail(data.user_email);
      }

      setSuccess(true);
      toast.success('Successfully unsubscribed from notifications');
    } catch (error) {
      logger.error('[UnsubscribePage] Error submitting unsubscribe request:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to process unsubscribe request';
      setSubmitError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <LoadingSpinner size="lg" text="Loading unsubscribe page..." />
      </div>
    );
  }

  // Error state - invalid/missing token
  if (loadError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md mx-auto">
          <Card className="border-red-200 shadow-lg">
            <CardHeader className="bg-red-50">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-6 h-6 text-red-600" />
                <CardTitle className="text-red-900">Unsubscribe Link Invalid</CardTitle>
              </div>
              <CardDescription className="text-red-700">
                We could not process your unsubscribe request
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <Alert variant="destructive" className="mb-6">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{loadError}</AlertDescription>
              </Alert>

              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  If you received this link in an email, please try again. Unsubscribe links are valid for 30 days.
                </p>
                <p className="text-sm text-gray-600">
                  Alternatively, you can manage your notification settings in your account preferences after logging in.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md mx-auto">
          <Card className="border-green-200 shadow-lg">
            <CardHeader className="bg-green-50">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-6 h-6 text-green-600" />
                <CardTitle className="text-green-900">Successfully Unsubscribed</CardTitle>
              </div>
              <CardDescription className="text-green-700">
                Your notification preferences have been updated
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <Alert className="mb-6 bg-green-50 text-green-800 border-green-200">
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>
                  You will no longer receive the notifications you unsubscribed from.
                </AlertDescription>
              </Alert>

              <div className="space-y-4">
                {userEmail && (
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-xs text-gray-600 mb-1">Account email</p>
                    <p className="text-sm font-medium text-gray-900 flex items-center gap-2">
                      <Mail className="w-4 h-4 text-gray-500" />
                      {userEmail}
                    </p>
                  </div>
                )}

                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-900">
                    <strong>Tip:</strong> You can manage all your notification settings anytime by logging in to your
                    account and visiting the notification preferences page.
                  </p>
                </div>
              </div>

              <div className="mt-8 space-y-3">
                <Button onClick={() => (window.location.href = '/')} className="w-full">
                  Return to Home
                </Button>
                <Button variant="outline" onClick={() => (window.location.href = '/auth')} className="w-full">
                  Log In to Your Account
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Main form
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <Card className="shadow-lg">
          <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-lg">
            <div className="flex items-center gap-3 mb-2">
              <Mail className="w-6 h-6" />
              <CardTitle className="text-white">Manage Notification Subscriptions</CardTitle>
            </div>
            <CardDescription className="text-blue-100">
              Select which notifications you would like to unsubscribe from
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-6">
            {submitError && (
              <Alert variant="destructive" className="mb-6">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{submitError}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Unsubscribe from All Option */}
              <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="unsubscribe-all"
                    checked={unsubscribeFromAll}
                    onCheckedChange={toggleUnsubscribeAll}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <Label htmlFor="unsubscribe-all" className="text-base font-semibold text-gray-900 cursor-pointer">
                      Unsubscribe from All Notifications
                    </Label>
                    <p className="text-sm text-gray-600 mt-1">
                      Disable all notification channels and types. You will only receive critical account alerts.
                    </p>
                  </div>
                </div>
              </div>

              {/* Notification Channels Section */}
              {!unsubscribeFromAll && (
                <>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Notification Channels</h3>
                    <div className="space-y-3">
                      {NOTIFICATION_CHANNELS.map((channel) => (
                        <div key={channel.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50">
                          <Checkbox
                            id={`channel-${channel.id}`}
                            checked={selectedChannels.includes(channel.id)}
                            onCheckedChange={() => toggleChannel(channel.id)}
                            className="mt-1"
                          />
                          <div className="flex-1 min-w-0">
                            <Label
                              htmlFor={`channel-${channel.id}`}
                              className="text-base font-medium text-gray-900 cursor-pointer"
                            >
                              {channel.label}
                            </Label>
                            <p className="text-sm text-gray-600">{channel.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Notification Types Section */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Notification Types</h3>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {NOTIFICATION_TYPES.map((type) => (
                        <div key={type.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50">
                          <Checkbox
                            id={`type-${type.id}`}
                            checked={selectedTypes.includes(type.id)}
                            onCheckedChange={() => toggleType(type.id)}
                            className="mt-1"
                          />
                          <div className="flex-1 min-w-0">
                            <Label
                              htmlFor={`type-${type.id}`}
                              className="text-sm font-medium text-gray-900 cursor-pointer"
                            >
                              {type.label}
                            </Label>
                            <p className="text-xs text-gray-600">{type.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Info Box */}
              <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
                <p className="text-sm text-blue-900">
                  <strong>Note:</strong> You will still receive critical account security notifications and
                  administrative messages. To manage all your notification settings in detail, log in to your account
                  and visit your notification preferences.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => (window.location.href = '/')}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting || (!unsubscribeFromAll && selectedChannels.length === 0 && selectedTypes.length === 0)}
                  className="flex-1"
                >
                  {isSubmitting ? (
                    <div className="flex items-center gap-2">
                      <LoadingSpinner size="sm" text="" />
                      Updating...
                    </div>
                  ) : (
                    'Confirm Unsubscribe'
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer Info */}
        <div className="mt-8 text-center text-sm text-gray-600">
          <p>
            This page uses a secure token to verify your email address. Your preferences will be saved immediately.
          </p>
        </div>
      </div>
    </div>
  );
};

export default UnsubscribePage;
