/**
 * LanguageSwitcher Component
 *
 * Provides UI for switching between supported languages
 * Supports dropdown and button styles
 */

import React from 'react';
import { Globe } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import useI18n from './useI18n';

export type LanguageSwitcherVariant = 'select' | 'dropdown' | 'button';

export interface LanguageSwitcherProps {
  /**
   * Display variant
   * - 'select': Dropdown select component
   * - 'dropdown': Dropdown menu with icons
   * - 'button': Simple button group
   */
  variant?: LanguageSwitcherVariant;

  /**
   * CSS classes
   */
  className?: string;

  /**
   * Show language names or just codes
   */
  showNames?: boolean;

  /**
   * Show globe icon
   */
  showIcon?: boolean;

  /**
   * Callback when language changes
   */
  onLanguageChange?: (language: string) => void;
}

/**
 * LanguageSwitcher Component
 *
 * @example
 * // Dropdown select
 * <LanguageSwitcher variant="select" />
 *
 * @example
 * // Dropdown menu
 * <LanguageSwitcher variant="dropdown" showNames={true} />
 *
 * @example
 * // Button group
 * <LanguageSwitcher variant="button" />
 */
export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  variant = 'select',
  className = '',
  showNames = true,
  showIcon = true,
  onLanguageChange,
}) => {
  const { language, changeLanguage, supportedLanguages } = useI18n();

  const handleLanguageChange = async (newLanguage: string) => {
    await changeLanguage(newLanguage as any);
    onLanguageChange?.(newLanguage);
  };

  if (variant === 'select') {
    return (
      <Select value={language} onValueChange={handleLanguageChange}>
        <SelectTrigger className={`w-[180px] ${className}`}>
          <SelectValue placeholder="Select language" />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(supportedLanguages).map(([code, { name }]) => (
            <SelectItem key={code} value={code}>
              {showNames ? name : code.toUpperCase()}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  if (variant === 'dropdown') {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon" className={className}>
            {showIcon && <Globe className="h-4 w-4" />}
            <span className="sr-only">Change language</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {Object.entries(supportedLanguages).map(([code, { name }]) => (
            <DropdownMenuItem
              key={code}
              onClick={() => handleLanguageChange(code)}
              className={language === code ? 'bg-accent' : ''}
            >
              <span>{showNames ? name : code.toUpperCase()}</span>
              {language === code && <span className="ml-2">✓</span>}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  // variant === 'button'
  return (
    <div className={`flex gap-2 ${className}`}>
      {Object.entries(supportedLanguages).map(([code, { name }]) => (
        <Button
          key={code}
          variant={language === code ? 'default' : 'outline'}
          size="sm"
          onClick={() => handleLanguageChange(code)}
          title={name}
        >
          {showNames ? name : code.toUpperCase()}
        </Button>
      ))}
    </div>
  );
};

export default LanguageSwitcher;
