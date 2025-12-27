import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  CircularProgressIndicator,
  CompactCircularProgress,
  type ProgressStatus,
} from "../CircularProgressIndicator";

// ============================================================================
// TEST DATA
// ============================================================================

const createProps = (overrides?: Partial<Parameters<typeof CircularProgressIndicator>[0]>) => ({
  progress: 65,
  status: "in_progress" as ProgressStatus,
  size: 120,
  strokeWidth: 8,
  showLabel: true,
  ...overrides,
});

// ============================================================================
// TESTS
// ============================================================================

describe("CircularProgressIndicator Component", () => {
  describe("Rendering", () => {
    it("should render SVG element", () => {
      const { container } = render(
        <CircularProgressIndicator {...createProps()} />,
      );
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("should display progress percentage", () => {
      render(
        <CircularProgressIndicator {...createProps({ progress: 75 })} />,
      );
      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    it("should display status label", () => {
      render(
        <CircularProgressIndicator
          {...createProps({ status: "in_progress" })}
        />,
      );
      expect(screen.getByText("in progress")).toBeInTheDocument();
    });

    it("should render status indicator label", () => {
      render(
        <CircularProgressIndicator {...createProps()} />,
      );
      expect(screen.getByText(/progress|in progress|completed|not started/i)).toBeInTheDocument();
    });
  });

  describe("Progress Display", () => {
    it("should have ARIA attributes", () => {
      const { container } = render(
        <CircularProgressIndicator {...createProps({ progress: 50 })} />,
      );
      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("role", "progressbar");
      expect(svg).toHaveAttribute("aria-valuenow", "50");
      expect(svg).toHaveAttribute("aria-valuemin", "0");
      expect(svg).toHaveAttribute("aria-valuemax", "100");
    });

    it("should clamp progress between 0 and 100", () => {
      const { rerender, container: container1 } = render(
        <CircularProgressIndicator {...createProps({ progress: -10 })} />,
      );
      expect(screen.getByText("0%")).toBeInTheDocument();

      rerender(
        <CircularProgressIndicator {...createProps({ progress: 150 })} />,
      );
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should handle 0% progress", () => {
      render(
        <CircularProgressIndicator {...createProps({ progress: 0 })} />,
      );
      expect(screen.getByText("0%")).toBeInTheDocument();
    });

    it("should handle 100% progress", () => {
      render(
        <CircularProgressIndicator
          {...createProps({ progress: 100 })}
        />,
      );
      expect(screen.getByText("100%")).toBeInTheDocument();
      expect(screen.getByText("Done")).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("should display 'Not Started' status", () => {
      render(
        <CircularProgressIndicator
          {...createProps({
            status: "not_started",
            progress: 0,
          })}
        />,
      );
      expect(screen.getByText("not started")).toBeInTheDocument();
    });

    it("should display 'In Progress' status", () => {
      render(
        <CircularProgressIndicator
          {...createProps({
            status: "in_progress",
            progress: 50,
          })}
        />,
      );
      expect(screen.getByText("in progress")).toBeInTheDocument();
    });

    it("should display 'Completed' status", () => {
      render(
        <CircularProgressIndicator
          {...createProps({
            status: "completed",
            progress: 100,
          })}
        />,
      );
      expect(screen.getByText("completed")).toBeInTheDocument();
    });
  });

  describe("Configuration", () => {
    it("should hide label when showLabel=false", () => {
      render(
        <CircularProgressIndicator
          {...createProps({ showLabel: false })}
        />,
      );
      expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
    });

    it("should apply custom className", () => {
      const { container } = render(
        <CircularProgressIndicator
          {...createProps({ className: "custom-class" })}
        />,
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("should use custom aria-label", () => {
      const { container } = render(
        <CircularProgressIndicator
          {...createProps({ ariaLabel: "Custom label" })}
        />,
      );
      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("aria-label", "Custom label");
    });
  });

  describe("Responsive Sizing", () => {
    it("should use custom size", () => {
      const { container } = render(
        <CircularProgressIndicator
          {...createProps({ size: 200 })}
        />,
      );
      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("width", "200");
      expect(svg).toHaveAttribute("height", "200");
    });

    it("should use custom stroke width", () => {
      const { container } = render(
        <CircularProgressIndicator
          {...createProps({ strokeWidth: 12 })}
        />,
      );
      const circles = container.querySelectorAll("circle");
      expect(circles.length).toBeGreaterThan(0);
    });
  });

  describe("Accessibility", () => {
    it("should have proper role and ARIA attributes", () => {
      const { container } = render(
        <CircularProgressIndicator {...createProps()} />,
      );
      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("role", "progressbar");
      expect(svg).toHaveAttribute("aria-valuenow");
      expect(svg).toHaveAttribute("aria-valuemin");
      expect(svg).toHaveAttribute("aria-valuemax");
      expect(svg).toHaveAttribute("aria-label");
    });

    it("should include status text for screen readers", () => {
      render(
        <CircularProgressIndicator {...createProps()} />,
      );
      const statusElement = screen.getByText("in progress");
      expect(statusElement).toBeInTheDocument();
    });
  });
});

// ============================================================================
// COMPACT CIRCULAR PROGRESS TESTS
// ============================================================================

describe("CompactCircularProgress Component", () => {
  it("should render with smaller size", () => {
    const { container } = render(
      <CompactCircularProgress progress={50} status="in_progress" />,
    );
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "60");
    expect(svg).toHaveAttribute("height", "60");
  });

  it("should hide label by default", () => {
    render(
      <CompactCircularProgress progress={50} status="in_progress" />,
    );
    // Label should be hidden in compact mode
    expect(screen.queryByText(/50%|Progress/)).not.toBeInTheDocument();
  });

  it("should display status indicator", () => {
    render(
      <CompactCircularProgress progress={50} status="in_progress" />,
    );
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("should accept custom className", () => {
    const { container } = render(
      <CompactCircularProgress
        progress={50}
        status="in_progress"
        className="custom-class"
      />,
    );
    expect(container.firstChild).toHaveClass("custom-class");
  });
});

// ============================================================================
// INTEGRATION TESTS
// ============================================================================

describe("CircularProgressIndicator Integration", () => {
  it("should handle all progress values correctly", () => {
    const progressValues = [0, 25, 50, 75, 100];

    progressValues.forEach((value) => {
      const { unmount } = render(
        <CircularProgressIndicator
          progress={value}
          status={value === 100 ? "completed" : value === 0 ? "not_started" : "in_progress"}
        />,
      );
      expect(screen.getByText(`${value}%`)).toBeInTheDocument();
      unmount();
    });
  });

  it("should handle all status types", () => {
    const statuses: ProgressStatus[] = ["not_started", "in_progress", "completed"];

    statuses.forEach((status) => {
      const { unmount } = render(
        <CircularProgressIndicator progress={50} status={status} />,
      );
      expect(screen.getByText(status.replace("_", " "))).toBeInTheDocument();
      unmount();
    });
  });
});
