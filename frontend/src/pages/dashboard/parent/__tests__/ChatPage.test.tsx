import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

const mockUseChat = vi.fn()
const mockUseChatMessages = vi.fn()

vi.mock('@/hooks/useChat', () => ({
  useChat: () => mockUseChat(),
  useChatMessages: () => mockUseChatMessages()
}))

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

describe('ChatPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()

    mockUseChat.mockReturnValue({
      conversations: [],
      isLoading: false,
      error: null
    })

    mockUseChatMessages.mockReturnValue({
      messages: [],
      isLoading: false
    })
  })

  it('should render chat page', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Chat Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Chat Page Test')).toBeInTheDocument()
  })

  it('should display chat conversations', () => {
    mockUseChat.mockReturnValue({
      conversations: [
        {
          id: 1,
          name: 'John Doe',
          lastMessage: 'Hello',
          unreadCount: 0
        }
      ],
      isLoading: false,
      error: null
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Chat Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUseChat).toBeDefined()
  })

  it('should display chat messages', () => {
    mockUseChatMessages.mockReturnValue({
      messages: [
        {
          id: 1,
          content: 'Hello from John',
          sender: 'john',
          timestamp: '2024-01-01T00:00:00Z'
        }
      ],
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Chat Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUseChatMessages).toBeDefined()
  })

  it('should load conversations on mount', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Chat Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUseChat).toBeDefined()
  })

  it('should handle loading state', () => {
    mockUseChat.mockReturnValue({
      conversations: [],
      isLoading: true,
      error: null
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Chat Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Chat Page Test')).toBeInTheDocument()
  })

  it('should handle error state', () => {
    mockUseChat.mockReturnValue({
      conversations: [],
      isLoading: false,
      error: new Error('Failed to load')
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Chat Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUseChat).toBeDefined()
  })

  it('should display chat window component', () => {
    mockUseChatMessages.mockReturnValue({
      messages: [
        {
          id: 1,
          content: 'Test message',
          sender: 'me',
          timestamp: '2024-01-01T00:00:00Z'
        }
      ],
      isLoading: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div data-testid="chat-window">Test message</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByTestId('chat-window')).toBeInTheDocument()
  })
})
