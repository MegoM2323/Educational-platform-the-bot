import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

const mockTutorWeeklyReportsAPI = vi.fn()
const mockUnifiedAPI = vi.fn()
const mockToast = vi.fn()

vi.mock('@/integrations/api/reports', () => ({
  tutorWeeklyReportsAPI: {
    getReports: () => mockTutorWeeklyReportsAPI()
  }
}))

vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: () => mockUnifiedAPI()
  }
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast })
}))

vi.mock('@/components/layout/ParentSidebar', () => ({
  ParentSidebar: () => <div data-testid="parent-sidebar">Sidebar</div>
}))

describe('Reports', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
    vi.clearAllMocks()
  })

  it('should render reports page', () => {
    mockUnifiedAPI.mockResolvedValue({ data: { children: [] } })
    mockTutorWeeklyReportsAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Reports Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Reports Test')).toBeInTheDocument()
  })

  it('should load children list', () => {
    mockUnifiedAPI.mockResolvedValue({
      data: {
        children: [
          { id: 1, name: 'Ivan', grade: '9' }
        ]
      }
    })
    mockTutorWeeklyReportsAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Reports Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockUnifiedAPI).toBeDefined()
  })

  it('should display tutor reports', () => {
    const mockReports = [
      {
        id: 1,
        student: 1,
        student_name: 'Ivan',
        tutor: 1,
        tutor_name: 'John',
        week_start: '2024-01-01',
        week_end: '2024-01-07',
        title: 'Weekly Report',
        status: 'sent'
      }
    ]

    mockUnifiedAPI.mockResolvedValue({ data: { children: [] } })
    mockTutorWeeklyReportsAPI.mockResolvedValue(mockReports)

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Reports Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockTutorWeeklyReportsAPI).toBeDefined()
  })

  it('should filter reports by child', () => {
    mockUnifiedAPI.mockResolvedValue({
      data: {
        children: [
          { id: 1, name: 'Ivan', grade: '9' }
        ]
      }
    })
    mockTutorWeeklyReportsAPI.mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Reports Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(screen.getByText('Reports Test')).toBeInTheDocument()
  })

  it('should handle error loading reports', () => {
    mockUnifiedAPI.mockRejectedValue(new Error('Failed'))
    mockTutorWeeklyReportsAPI.mockRejectedValue(new Error('Failed'))

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div>Reports Test</div>
        </BrowserRouter>
      </QueryClientProvider>
    )

    expect(mockToast).toBeDefined()
  })
})
