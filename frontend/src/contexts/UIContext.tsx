// UI Context для управления состоянием интерфейса
import React, { createContext, useContext, useCallback, useMemo, ReactNode, useReducer } from 'react';
import { logger } from '@/utils/logger';

interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  modals: Record<string, boolean>;
  notifications: {
    position: 'top' | 'bottom' | 'top-right' | 'bottom-right';
    maxNotifications: number;
  };
  language: string;
}

type UIAction =
  | { type: 'SET_THEME'; payload: 'light' | 'dark' }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SIDEBAR'; payload: boolean }
  | { type: 'OPEN_MODAL'; payload: string }
  | { type: 'CLOSE_MODAL'; payload: string }
  | { type: 'SET_MODALS'; payload: Record<string, boolean> }
  | { type: 'SET_LANGUAGE'; payload: string };

interface UIContextType {
  state: UIState;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  setSidebar: (open: boolean) => void;
  openModal: (modalName: string) => void;
  closeModal: (modalName: string) => void;
  closeAllModals: () => void;
  setLanguage: (lang: string) => void;
}

const initialState: UIState = {
  theme: (typeof window !== 'undefined' && localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  sidebarOpen: true,
  modals: {},
  notifications: {
    position: 'top-right',
    maxNotifications: 5,
  },
  language: 'ru',
};

const UIContext = createContext<UIContextType | undefined>(undefined);

function uiReducer(state: UIState, action: UIAction): UIState {
  switch (action.type) {
    case 'SET_THEME':
      return { ...state, theme: action.payload };
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case 'SET_SIDEBAR':
      return { ...state, sidebarOpen: action.payload };
    case 'OPEN_MODAL':
      return { ...state, modals: { ...state.modals, [action.payload]: true } };
    case 'CLOSE_MODAL':
      return { ...state, modals: { ...state.modals, [action.payload]: false } };
    case 'SET_MODALS':
      return { ...state, modals: action.payload };
    case 'SET_LANGUAGE':
      return { ...state, language: action.payload };
    default:
      return state;
  }
}

interface UIProviderProps {
  children: ReactNode;
}

export const UIProvider: React.FC<UIProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(uiReducer, initialState);

  // Persist theme to localStorage
  const setTheme = useCallback((theme: 'light' | 'dark') => {
    dispatch({ type: 'SET_THEME', payload: theme });
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', theme);
    }
    logger.debug('[UIContext] Theme changed to:', theme);
  }, []);

  const toggleSidebar = useCallback(() => {
    dispatch({ type: 'TOGGLE_SIDEBAR' });
    logger.debug('[UIContext] Sidebar toggled');
  }, []);

  const setSidebar = useCallback((open: boolean) => {
    dispatch({ type: 'SET_SIDEBAR', payload: open });
    logger.debug('[UIContext] Sidebar set to:', open);
  }, []);

  const openModal = useCallback((modalName: string) => {
    dispatch({ type: 'OPEN_MODAL', payload: modalName });
    logger.debug('[UIContext] Modal opened:', modalName);
  }, []);

  const closeModal = useCallback((modalName: string) => {
    dispatch({ type: 'CLOSE_MODAL', payload: modalName });
    logger.debug('[UIContext] Modal closed:', modalName);
  }, []);

  const closeAllModals = useCallback(() => {
    dispatch({ type: 'SET_MODALS', payload: {} });
    logger.debug('[UIContext] All modals closed');
  }, []);

  const setLanguage = useCallback((lang: string) => {
    dispatch({ type: 'SET_LANGUAGE', payload: lang });
    logger.debug('[UIContext] Language changed to:', lang);
  }, []);

  const value: UIContextType = useMemo(
    () => ({
      state,
      setTheme,
      toggleSidebar,
      setSidebar,
      openModal,
      closeModal,
      closeAllModals,
      setLanguage,
    }),
    [state, setTheme, toggleSidebar, setSidebar, openModal, closeModal, closeAllModals, setLanguage]
  );

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
};

export const useUI = (): UIContextType => {
  const context = useContext(UIContext);
  if (context === undefined) {
    throw new Error('useUI must be used within a UIProvider');
  }
  return context;
};

// Selectors to prevent re-renders
export const useTheme = () => {
  const { state, setTheme } = useUI();
  return useMemo(() => ({ theme: state.theme, setTheme }), [state.theme, setTheme]);
};

export const useSidebar = () => {
  const { state, toggleSidebar, setSidebar } = useUI();
  return useMemo(
    () => ({ sidebarOpen: state.sidebarOpen, toggleSidebar, setSidebar }),
    [state.sidebarOpen, toggleSidebar, setSidebar]
  );
};

export const useModals = () => {
  const { state, openModal, closeModal, closeAllModals } = useUI();
  return useMemo(
    () => ({
      modals: state.modals,
      openModal,
      closeModal,
      closeAllModals,
      isModalOpen: (name: string) => state.modals[name] ?? false,
    }),
    [state.modals, openModal, closeModal, closeAllModals]
  );
};

export const useLanguage = () => {
  const { state, setLanguage } = useUI();
  return useMemo(() => ({ language: state.language, setLanguage }), [state.language, setLanguage]);
};

// Selector for specific modal
export const useModal = (modalName: string) => {
  const { state, openModal, closeModal } = useUI();
  const isOpen = state.modals[modalName] ?? false;
  return useMemo(
    () => ({
      isOpen,
      open: () => openModal(modalName),
      close: () => closeModal(modalName),
      toggle: () => (isOpen ? closeModal(modalName) : openModal(modalName)),
    }),
    [isOpen, openModal, closeModal, modalName]
  );
};
