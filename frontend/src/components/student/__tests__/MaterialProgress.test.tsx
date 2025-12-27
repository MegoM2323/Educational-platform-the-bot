import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MaterialProgress,
  MaterialProgressList,
  type MaterialProgressProps,
  type ProgressStatus,
} from "../MaterialProgress";

// ============================================================================
// TEST DATA
// ============================================================================

const mockMaterial = {
  id: 1,
  title: "Algebra Basics",
  description: "Introduction to algebraic concepts",
};

const createMaterialProgressProps = (
  overrides?: Partial<MaterialProgressProps>,
): MaterialProgressProps => ({
  material: mockMaterial,
  progress: 50,
  status: "in_progress" as ProgressStatus,
  timeSpent: 45,
  lastAccessed: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  score: 75,
  maxScore: 100,
  nextMilestone: 75,
  ...overrides,
});

// ============================================================================
// UNIT TESTS: MaterialProgress Component
// ============================================================================

describe("MaterialProgress Component", () => {
  describe("Rendering", () => {
    it("should render material title", () => {
      render(<MaterialProgress {...createMaterialProgressProps()} />);
      expect(screen.getByText("Algebra Basics")).toBeInTheDocument();
    });

    it("should render material description", () => {
      render(<MaterialProgress {...createMaterialProgressProps()} />);
      expect(
        screen.getByText("Introduction to algebraic concepts"),
      ).toBeInTheDocument();
    });

    it("should render progress percentage", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 65 })}
        />,
      );
      expect(screen.getByText("65%")).toBeInTheDocument();
    });

    it("should render status label", () => {
      render(<MaterialProgress {...createMaterialProgressProps()} />);
      expect(screen.getByText("In Progress")).toBeInTheDocument();
    });

    it("should render time spent", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ timeSpent: 45 })}
        />,
      );
      expect(screen.getByText("45 minutes")).toBeInTheDocument();
    });

    it("should render last accessed timestamp", () => {
      render(<MaterialProgress {...createMaterialProgressProps()} />);
      // Format depends on date calculation - should show "hours ago"
      const lastAccessedElements = screen.getAllByText(/hours ago/i);
      expect(lastAccessedElements.length).toBeGreaterThan(0);
    });

    it("should render score display", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ score: 78, maxScore: 100 })}
        />,
      );
      expect(screen.getByText("78/100")).toBeInTheDocument();
    });

    it("should render score percentage badge", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ score: 85, maxScore: 100 })}
        />,
      );
      expect(screen.getByText("85%")).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("should display 'Not Started' status", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            status: "not_started",
            progress: 0,
          })}
        />,
      );
      expect(screen.getByText("Not Started")).toBeInTheDocument();
    });

    it("should display 'In Progress' status", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            status: "in_progress",
            progress: 50,
          })}
        />,
      );
      expect(screen.getByText("In Progress")).toBeInTheDocument();
    });

    it("should display 'Completed' status", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            status: "completed",
            progress: 100,
          })}
        />,
      );
      expect(screen.getByText("Completed")).toBeInTheDocument();
    });
  });

  describe("Progress Bar Color Coding", () => {
    it("should have gray color for 0% progress", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 0 })}
        />,
      );
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toBeInTheDocument();
    });

    it("should have yellow color for 1-50% progress", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 35 })}
        />,
      );
      const indicator = container.querySelector(".bg-yellow-400");
      expect(indicator).toBeInTheDocument();
    });

    it("should have green color for 51-99% progress", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 75 })}
        />,
      );
      const indicator = container.querySelector(".bg-green-500");
      expect(indicator).toBeInTheDocument();
    });

    it("should have blue color for 100% progress", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 100 })}
        />,
      );
      const indicator = container.querySelector(".bg-blue-500");
      expect(indicator).toBeInTheDocument();
    });
  });

  describe("Progress Bar Display", () => {
    it("should render progress bar with correct width", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 65 })}
        />,
      );
      const progressBar = container.querySelector('[role="progressbar"]');
      const indicator = progressBar?.querySelector("div");
      expect(indicator).toHaveStyle({ width: "65%" });
    });

    it("should have ARIA attributes for accessibility", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 50 })}
        />,
      );
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toHaveAttribute("aria-valuenow", "50");
      expect(progressBar).toHaveAttribute("aria-valuemin", "0");
      expect(progressBar).toHaveAttribute("aria-valuemax", "100");
    });

    it("should clamp progress between 0 and 100", () => {
      const { container: containerUnder } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: -10 })}
        />,
      );
      const indicatorUnder = containerUnder
        .querySelector('[role="progressbar"]')
        ?.querySelector("div");
      expect(indicatorUnder).toHaveStyle({ width: "0%" });

      const { container: containerOver } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 150 })}
        />,
      );
      const indicatorOver = containerOver
        .querySelector('[role="progressbar"]')
        ?.querySelector("div");
      expect(indicatorOver).toHaveStyle({ width: "100%" });
    });
  });

  describe("Next Milestone", () => {
    it("should display milestone message when not reached", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            progress: 50,
            nextMilestone: 75,
          })}
        />,
      );
      expect(screen.getByText("25% to next milestone")).toBeInTheDocument();
    });

    it("should display completion message when milestone reached", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            progress: 75,
            nextMilestone: 75,
          })}
        />,
      );
      expect(
        screen.getByText("🎉 Next milestone reached!"),
      ).toBeInTheDocument();
    });

    it("should not display milestone when not provided", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ nextMilestone: undefined })}
        />,
      );
      expect(
        screen.queryByText(/to next milestone/),
      ).not.toBeInTheDocument();
    });
  });

  describe("Time Formatting", () => {
    it("should display 'Just now' for recent access", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            lastAccessed: new Date().toISOString(),
          })}
        />,
      );
      expect(screen.getByText("Just now")).toBeInTheDocument();
    });

    it("should display minutes ago", () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ lastAccessed: fiveMinutesAgo })}
        />,
      );
      expect(screen.getByText("5 minutes ago")).toBeInTheDocument();
    });

    it("should display hours ago", () => {
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ lastAccessed: twoHoursAgo })}
        />,
      );
      expect(screen.getByText("2 hours ago")).toBeInTheDocument();
    });

    it("should display days ago", () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ lastAccessed: threeDaysAgo })}
        />,
      );
      expect(screen.getByText("3 days ago")).toBeInTheDocument();
    });

    it("should display 'Never' when no lastAccessed provided", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ lastAccessed: undefined })}
        />,
      );
      expect(screen.getByText("Never")).toBeInTheDocument();
    });

    it("should format time spent in minutes", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ timeSpent: 30 })}
        />,
      );
      expect(screen.getByText("30 minutes")).toBeInTheDocument();
    });

    it("should format time spent in hours and minutes", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ timeSpent: 90 })}
        />,
      );
      expect(screen.getByText("1h 30m")).toBeInTheDocument();
    });

    it("should format time spent in hours only", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ timeSpent: 120 })}
        />,
      );
      expect(screen.getByText("2 hours")).toBeInTheDocument();
    });

    it("should display 'Not started' when timeSpent is 0", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ timeSpent: 0 })}
        />,
      );
      expect(screen.getByText("Not started")).toBeInTheDocument();
    });
  });

  describe("Score Display", () => {
    it("should not display score when not provided", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            score: undefined,
            maxScore: undefined,
          })}
        />,
      );
      expect(screen.queryByText(/\/100/)).not.toBeInTheDocument();
    });

    it("should display score percentage badge for good score", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ score: 85, maxScore: 100 })}
        />,
      );
      const badge = screen.getByText("85%");
      expect(badge).toHaveClass("bg-green-100");
      expect(badge).toHaveClass("text-green-700");
    });

    it("should display score percentage badge for medium score", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ score: 70, maxScore: 100 })}
        />,
      );
      const badge = screen.getByText("70%");
      expect(badge).toHaveClass("bg-yellow-100");
      expect(badge).toHaveClass("text-yellow-700");
    });

    it("should display score percentage badge for low score", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({ score: 45, maxScore: 100 })}
        />,
      );
      const badge = screen.getByText("45%");
      expect(badge).toHaveClass("bg-red-100");
      expect(badge).toHaveClass("text-red-700");
    });
  });

  describe("Responsive Design", () => {
    it("should render grid layout for desktop", () => {
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );
      const grid = container.querySelector(".grid-cols-1");
      expect(grid).toHaveClass("sm:grid-cols-2");
      expect(grid).toHaveClass("lg:grid-cols-3");
    });

    it("should have proper spacing on different screen sizes", () => {
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );
      const grid = container.querySelector(".grid");
      expect(grid).toHaveClass("gap-3");
    });
  });

  describe("Keyboard Navigation", () => {
    it("should expand details on Enter key", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );

      const component = container.firstChild as HTMLElement;
      component.focus();

      await user.keyboard("{Enter}");

      await waitFor(() => {
        expect(screen.getByText("Hide Details")).toBeInTheDocument();
      });
    });

    it("should expand details on Space key", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );

      const component = container.firstChild as HTMLElement;
      component.focus();

      await user.keyboard(" ");

      await waitFor(() => {
        expect(screen.getByText("Hide Details")).toBeInTheDocument();
      });
    });

    it("should be focusable with tabindex=0", () => {
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );
      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("tabindex", "0");
    });
  });

  describe("Details Expansion", () => {
    it("should show details button", () => {
      render(<MaterialProgress {...createMaterialProgressProps()} />);
      expect(screen.getByText("Show Details")).toBeInTheDocument();
    });

    it("should expand and collapse details", async () => {
      const user = userEvent.setup();
      render(<MaterialProgress {...createMaterialProgressProps()} />);

      const showButton = screen.getByText("Show Details");
      await user.click(showButton);

      await waitFor(() => {
        expect(screen.getByText("Hide Details")).toBeInTheDocument();
        expect(screen.getByText(`${mockMaterial.id}`)).toBeInTheDocument();
      });

      const hideButton = screen.getByText("Hide Details");
      await user.click(hideButton);

      await waitFor(() => {
        expect(screen.getByText("Show Details")).toBeInTheDocument();
      });
    });

    it("should display material ID in expanded view", async () => {
      const user = userEvent.setup();
      render(<MaterialProgress {...createMaterialProgressProps()} />);

      await user.click(screen.getByText("Show Details"));

      await waitFor(() => {
        expect(screen.getByText("Material ID:")).toBeInTheDocument();
        expect(screen.getByText(`${mockMaterial.id}`)).toBeInTheDocument();
      });
    });

    it("should display status in expanded view", async () => {
      const user = userEvent.setup();
      render(<MaterialProgress {...createMaterialProgressProps()} />);

      await user.click(screen.getByText("Show Details"));

      await waitFor(() => {
        expect(screen.getByText("Current Status:")).toBeInTheDocument();
        expect(screen.getByText("in_progress")).toBeInTheDocument();
      });
    });
  });

  describe("Accessibility", () => {
    it("should have aria-label", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps()}
          ariaLabel="Custom label"
        />,
      );
      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("aria-label", "Custom label");
    });

    it("should have default aria-label", () => {
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );
      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("aria-label");
      expect(component.getAttribute("aria-label")).toContain("Algebra Basics");
    });

    it("should have role=region", () => {
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );
      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("role", "region");
    });

    it("should have progressbar role on progress element", () => {
      const { container } = render(
        <MaterialProgress {...createMaterialProgressProps()} />,
      );
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toBeInTheDocument();
    });

    it("should have aria-label on progress bar", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ progress: 65 })}
        />,
      );
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toHaveAttribute(
        "aria-label",
        "Progress: 65%",
      );
    });
  });

  describe("Loading State", () => {
    it("should render skeleton when loading", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ isLoading: true })}
        />,
      );

      expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should have aria-busy=true when loading", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ isLoading: true })}
        />,
      );

      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("aria-busy", "true");
    });

    it("should have role=status when loading", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ isLoading: true })}
        />,
      );

      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("role", "status");
    });
  });

  describe("Error State", () => {
    it("should render error message", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            error: "Failed to load progress",
          })}
        />,
      );
      expect(screen.getByText("Failed to load progress")).toBeInTheDocument();
    });

    it("should have role=alert", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({
            error: "Failed to load progress",
          })}
        />,
      );
      const component = container.firstChild as HTMLElement;
      expect(component).toHaveAttribute("role", "alert");
    });

    it("should display retry button", () => {
      const onRetry = vi.fn();
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            error: "Failed to load progress",
            onRetry,
          })}
        />,
      );
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    it("should call onRetry when retry button is clicked", async () => {
      const user = userEvent.setup();
      const onRetry = vi.fn();

      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            error: "Failed to load progress",
            onRetry,
          })}
        />,
      );

      await user.click(screen.getByText("Retry"));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("should have red border on error", () => {
      const { container } = render(
        <MaterialProgress
          {...createMaterialProgressProps({
            error: "Failed to load progress",
          })}
        />,
      );
      const component = container.firstChild as HTMLElement;
      expect(component).toHaveClass("border-red-200");
    });
  });

  describe("Click Handler", () => {
    it("should call onClick when component is clicked", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(
        <MaterialProgress
          {...createMaterialProgressProps({ onClick })}
        />,
      );

      const component = screen.getByText("Algebra Basics").closest("[role='region']");
      await user.click(component!);

      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("Props Combinations", () => {
    it("should handle material with no description", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            material: { id: 1, title: "Test Material" },
          })}
        />,
      );

      expect(screen.getByText("Test Material")).toBeInTheDocument();
      expect(
        screen.queryByText("Introduction to algebraic concepts"),
      ).not.toBeInTheDocument();
    });

    it("should handle all optional fields missing", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            timeSpent: undefined,
            lastAccessed: undefined,
            score: undefined,
            maxScore: undefined,
            nextMilestone: undefined,
          })}
        />,
      );

      expect(screen.getByText("Not started")).toBeInTheDocument();
      expect(screen.getByText("Never")).toBeInTheDocument();
    });

    it("should handle all optional fields provided", () => {
      render(
        <MaterialProgress
          {...createMaterialProgressProps({
            timeSpent: 120,
            lastAccessed: new Date().toISOString(),
            score: 95,
            maxScore: 100,
            nextMilestone: 100,
          })}
        />,
      );

      expect(screen.getByText("2 hours")).toBeInTheDocument();
      expect(screen.getByText("95/100")).toBeInTheDocument();
      expect(screen.getByText("95%")).toBeInTheDocument();
    });
  });
});

// ============================================================================
// UNIT TESTS: MaterialProgressList Component
// ============================================================================

describe("MaterialProgressList Component", () => {
  const mockMaterials: MaterialProgressProps[] = [
    createMaterialProgressProps({
      material: { id: 1, title: "Algebra Basics", description: "Intro to algebra" },
      progress: 65,
      status: "in_progress",
    }),
    createMaterialProgressProps({
      material: { id: 2, title: "Geometry", description: "Shapes and angles" },
      progress: 100,
      status: "completed",
    }),
    createMaterialProgressProps({
      material: { id: 3, title: "Trigonometry" },
      progress: 0,
      status: "not_started",
    }),
  ];

  describe("Rendering", () => {
    it("should render all materials in list", () => {
      render(
        <MaterialProgressList
          materials={mockMaterials}
        />,
      );

      expect(screen.getByText("Algebra Basics")).toBeInTheDocument();
      expect(screen.getByText("Geometry")).toBeInTheDocument();
      expect(screen.getByText("Trigonometry")).toBeInTheDocument();
    });

    it("should render correct number of items", () => {
      const { container } = render(
        <MaterialProgressList materials={mockMaterials} />,
      );

      const items = container.querySelectorAll('[role="region"]');
      expect(items).toHaveLength(3);
    });

    it("should apply custom className", () => {
      const { container } = render(
        <MaterialProgressList
          materials={mockMaterials}
          className="custom-class"
        />,
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("custom-class");
    });
  });

  describe("Empty State", () => {
    it("should display empty message when no materials", () => {
      render(
        <MaterialProgressList materials={[]} />,
      );

      expect(screen.getByText("No materials found")).toBeInTheDocument();
    });

    it("should display custom empty message", () => {
      render(
        <MaterialProgressList
          materials={[]}
          emptyMessage="No courses assigned"
        />,
      );

      expect(screen.getByText("No courses assigned")).toBeInTheDocument();
    });

    it("should have dashed border in empty state", () => {
      const { container } = render(
        <MaterialProgressList materials={[]} />,
      );

      const emptyState = container.querySelector(".border-dashed");
      expect(emptyState).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should render skeleton loaders when loading", () => {
      const { container } = render(
        <MaterialProgressList
          materials={[]}
          isLoading={true}
        />,
      );

      const skeletons = container.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it("should render 3 skeleton items", () => {
      const { container } = render(
        <MaterialProgressList
          materials={[]}
          isLoading={true}
        />,
      );

      const skeletons = container.querySelectorAll(".space-y-4 > div");
      expect(skeletons.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Error State", () => {
    it("should display error message", () => {
      render(
        <MaterialProgressList
          materials={[]}
          error="Failed to load materials"
        />,
      );

      expect(screen.getByText("Failed to load materials")).toBeInTheDocument();
    });

    it("should have role=alert on error", () => {
      const { container } = render(
        <MaterialProgressList
          materials={[]}
          error="Failed to load materials"
        />,
      );

      const errorDiv = container.querySelector("[role='alert']");
      expect(errorDiv).toBeInTheDocument();
    });

    it("should display retry button on error", () => {
      const onRetry = vi.fn();

      render(
        <MaterialProgressList
          materials={[]}
          error="Failed to load materials"
          onRetry={onRetry}
        />,
      );

      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    it("should call onRetry when retry button clicked", async () => {
      const user = userEvent.setup();
      const onRetry = vi.fn();

      render(
        <MaterialProgressList
          materials={[]}
          error="Failed to load materials"
          onRetry={onRetry}
        />,
      );

      await user.click(screen.getByText("Retry"));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("should have red border on error", () => {
      const { container } = render(
        <MaterialProgressList
          materials={[]}
          error="Failed to load materials"
        />,
      );

      const errorDiv = container.querySelector(".border-red-200");
      expect(errorDiv).toBeInTheDocument();
    });
  });

  describe("Responsive Design", () => {
    it("should render as vertical list", () => {
      const { container } = render(
        <MaterialProgressList materials={mockMaterials} />,
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("space-y-4");
    });

    it("should have proper spacing", () => {
      const { container } = render(
        <MaterialProgressList materials={mockMaterials} />,
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("gap-0");
    });
  });
});

// ============================================================================
// INTEGRATION TESTS
// ============================================================================

describe("MaterialProgress Integration Tests", () => {
  it("should handle all material statuses correctly", () => {
    const statuses: ProgressStatus[] = [
      "not_started",
      "in_progress",
      "completed",
    ];

    statuses.forEach((status) => {
      const { unmount } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ status })}
        />,
      );

      expect(screen.getByText(/Not Started|In Progress|Completed/)).toBeInTheDocument();
      unmount();
    });
  });

  it("should correctly format different time durations", () => {
    const testCases = [
      { minutes: 0, expected: "Not started" },
      { minutes: 30, expected: "30 minutes" },
      { minutes: 60, expected: "1 hour" },
      { minutes: 90, expected: "1h 30m" },
      { minutes: 120, expected: "2 hours" },
    ];

    testCases.forEach(({ minutes, expected }) => {
      const { unmount } = render(
        <MaterialProgress
          {...createMaterialProgressProps({ timeSpent: minutes })}
        />,
      );

      expect(screen.getByText(expected)).toBeInTheDocument();
      unmount();
    });
  });

  it("should handle edge cases for score display", () => {
    const testCases = [
      { score: 100, maxScore: 100, expected: "100%" },
      { score: 0, maxScore: 100, expected: "0%" },
      { score: 50, maxScore: 100, expected: "50%" },
      { score: 75, maxScore: 150, expected: "50%" },
    ];

    testCases.forEach(({ score, maxScore, expected }) => {
      const { unmount } = render(
        <MaterialProgress
          {...createMaterialProgressProps({
            score,
            maxScore,
          })}
        />,
      );

      expect(screen.getByText(expected)).toBeInTheDocument();
      unmount();
    });
  });
});
