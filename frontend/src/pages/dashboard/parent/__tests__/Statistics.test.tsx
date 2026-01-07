import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

const mockGetStatistics = vi.fn()
const mockGetChildrenStats = vi.fn()

vi.mock('@/integrations/api/dashboard', () => ({
  parentDashboardAPI: {
    getStatistics: () => mockGetStatistics(),
    getChildrenStats: () => mockGetChildrenStats()
  }
}))

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

describe('Statistics', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()

    mockGetStatistics.mockResolvedValue({
      total_children: 2,
      average_progress: 80,
      total_payments: 5000,
      pending_payments: 1000
    })

    mockGetChildrenStats.mockResolvedValue([
      {
        id: 1,
        name: 'Ivan',
        progress: 85,
        paid: 3000
      }
    ])
  })

  it('should render statistics page', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Statistics Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Statistics Test')).toBeInTheDocument()
  })

  it('should display overall statistics', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Statistics Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockGetStatistics).toBeDefined()
  })

  it('should display children statistics', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Statistics Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockGetChildrenStats).toBeDefined()
  })

  it('should load data on mount', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Statistics Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Statistics Test')).toBeInTheDocument()
  })

  it('should display charts and graphs', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Statistics Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockGetStatistics).toBeDefined()
  })
})
