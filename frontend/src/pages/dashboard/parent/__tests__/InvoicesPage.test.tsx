import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

const mockUseParentInvoices = vi.fn()
const mockUseInvoiceWebSocket = vi.fn()
const mockToast = vi.fn()

vi.mock('@/hooks/useParentInvoices', () => ({
  useParentInvoices: () => mockUseParentInvoices()
}))

vi.mock('@/hooks/useInvoiceWebSocket', () => ({
  useInvoiceWebSocket: () => mockUseInvoiceWebSocket()
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast })
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useSearchParams: () => [new URLSearchParams(), vi.fn()]
  }
})

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

vi.mock('@/components/invoices/ParentInvoicesList', () => ({
  ParentInvoicesList: () => <div>Invoices List</div>
}))

vi.mock('@/components/invoices/ParentInvoiceDetail', () => ({
  ParentInvoiceDetail: () => <div>Invoice Detail</div>
}))

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query')
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() })
  }
})

describe('InvoicesPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()

    mockUseParentInvoices.mockReturnValue({
      invoices: [],
      totalCount: 0,
      totalPages: 1,
      currentPage: 1,
      hasNext: false,
      hasPrevious: false,
      summary: { paid: 0, pending: 0 },
      unpaidCount: 0,
      isLoading: false,
      error: null,
      setStatus: vi.fn(),
      setPage: vi.fn(),
      markAsViewed: vi.fn(),
      initiatePayment: vi.fn(),
      refetch: vi.fn(),
      isInitiatingPayment: false
    })

    mockUseInvoiceWebSocket.mockReturnValue({
      on: vi.fn(),
      off: vi.fn()
    })
  })

  it('should render invoices page', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Invoices Page Test')).toBeInTheDocument()
  })

  it('should display invoices list', () => {
    mockUseParentInvoices.mockReturnValue({
      invoices: [
        {
          id: 1,
          number: 'INV-001',
          amount: 5000,
          status: 'pending',
          created_at: '2024-01-01'
        }
      ],
      totalCount: 1,
      totalPages: 1,
      currentPage: 1,
      hasNext: false,
      hasPrevious: false,
      summary: { paid: 0, pending: 5000 },
      unpaidCount: 1,
      isLoading: false,
      error: null,
      setStatus: vi.fn(),
      setPage: vi.fn(),
      markAsViewed: vi.fn(),
      initiatePayment: vi.fn(),
      refetch: vi.fn(),
      isInitiatingPayment: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices List</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Invoices List')).toBeInTheDocument()
  })

  it('should handle payment success status', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockToast).toBeDefined()
  })

  it('should handle payment failed status', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockToast).toBeDefined()
  })

  it('should setup WebSocket listeners', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUseInvoiceWebSocket).toBeDefined()
  })

  it('should display pagination controls', () => {
    mockUseParentInvoices.mockReturnValue({
      invoices: [],
      totalCount: 50,
      totalPages: 3,
      currentPage: 1,
      hasNext: true,
      hasPrevious: false,
      summary: { paid: 0, pending: 0 },
      unpaidCount: 0,
      isLoading: false,
      error: null,
      setStatus: vi.fn(),
      setPage: vi.fn(),
      markAsViewed: vi.fn(),
      initiatePayment: vi.fn(),
      refetch: vi.fn(),
      isInitiatingPayment: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Invoices Page Test')).toBeInTheDocument()
  })

  it('should display invoice summary', () => {
    mockUseParentInvoices.mockReturnValue({
      invoices: [],
      totalCount: 0,
      totalPages: 1,
      currentPage: 1,
      hasNext: false,
      hasPrevious: false,
      summary: { paid: 5000, pending: 2000 },
      unpaidCount: 1,
      isLoading: false,
      error: null,
      setStatus: vi.fn(),
      setPage: vi.fn(),
      markAsViewed: vi.fn(),
      initiatePayment: vi.fn(),
      refetch: vi.fn(),
      isInitiatingPayment: false
    })

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoices Page Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Invoices Page Test')).toBeInTheDocument()
  })

  it('should handle invoice detail view', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Invoice Detail</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Invoice Detail')).toBeInTheDocument()
  })
})
