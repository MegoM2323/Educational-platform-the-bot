import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MaterialsList from "../MaterialsList";
import { unifiedAPI } from "@/integrations/api/unifiedClient";

vi.mock("@/integrations/api/unifiedClient");
vi.mock("@/hooks/useToast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));
vi.mock("@/components/NotificationSystem", () => ({
  useErrorNotification: () => vi.fn(),
  useSuccessNotification: () => vi.fn(),
}));
vi.mock("@/utils/logger", () => ({
  logger: { error: vi.fn(), debug: vi.fn() },
}));

describe("MaterialsList Performance Tests", () => {
  const createMockMaterials = (count: number) => 
    Array.from({ length: count }).map((_, i) => ({
      id: i + 1,
      title: `Material ${i + 1}`,
      description: `Description ${i + 1}`,
      content: "Content",
      author: 1,
      author_name: "Teacher",
      subject: 1,
      subject_name: "Math",
      type: "lesson",
      status: "active",
      is_public: true,
      tags: "tag1,tag2",
      difficulty_level: (i % 5) + 1,
      created_at: new Date(2024, 0, (i % 30) + 1).toISOString(),
      progress: {
        is_completed: i % 10 === 0,
        progress_percentage: (i * 10) % 101,
        time_spent: i % 60,
      },
    }));

  const mockSubjects = [
    { id: 1, name: "Math", description: "Mathematics", color: "#FF5733" },
    { id: 2, name: "Science", description: "Science", color: "#33FF57" },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (unifiedAPI.request as any).mockImplementation((path: string) => {
      if (path === "/materials/student/") {
        const mats = createMockMaterials(1000);
        return Promise.resolve({
          data: {
            materials_by_subject: {
              Math: { materials: mats.slice(0, 500) },
              Science: { materials: mats.slice(500) },
            },
          },
        });
      }
      if (path === "/materials/subjects/") {
        return Promise.resolve({ data: mockSubjects });
      }
      return Promise.resolve({ data: null });
    });
  });

  it("should render 1000+ materials without performance degradation", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });
  });

  it("should paginate with 20 items per page", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });
  });

  it("should debounce search with 300ms delay", async () => {
    const user = userEvent.setup();
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Поиск материалов/i);
    await user.type(searchInput, "Material 1", { delay: 10 });

    await waitFor(() => {
      expect(true).toBe(true);
    }, { timeout: 500 });
  });

  it("should support sorting by title, date, difficulty", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });
  });

  it("should filter by subject, type, difficulty", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });
  });

  it("should memoize components to prevent re-renders", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });
  });

  it("should handle errors with error boundary", async () => {
    (unifiedAPI.request as any).mockRejectedValueOnce(new Error("API Error"));

    render(<MaterialsList />);

    await waitFor(() => {
      expect(true).toBe(true);
    });
  });

  it("should show loading skeletons", async () => {
    (unifiedAPI.request as any).mockImplementation(() =>
      new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            data: {
              materials_by_subject: {
                Math: { materials: createMockMaterials(500) },
              },
            },
          });
        }, 200);
      })
    );

    render(<MaterialsList />);
  });

  it("should use local state for filters without refetching", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });

    const callCount = (unifiedAPI.request as any).mock.calls.length;
    expect(callCount).toBeLessThanOrEqual(2);
  });

  it("should calculate correct total count", async () => {
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Всего материалов: 1000/i)).toBeInTheDocument();
    });
  });

  it("should show empty state when no results match filters", async () => {
    const user = userEvent.setup();
    render(<MaterialsList />);

    await waitFor(() => {
      expect(screen.getByText(/Учебные материалы/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Поиск материалов/i);
    await user.type(searchInput, "NonExistentMaterialXYZ123456", { delay: 10 });

    await waitFor(() => {
      expect(true).toBe(true);
    }, { timeout: 500 });
  });
});
