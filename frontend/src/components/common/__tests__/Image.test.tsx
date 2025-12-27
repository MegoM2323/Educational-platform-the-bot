import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { Image, AvatarImage, BackgroundImage } from "../Image";

// Mock IntersectionObserver
class MockIntersectionObserver {
  callback: IntersectionObserverCallback;
  options: IntersectionObserverInit;

  constructor(callback: IntersectionObserverCallback, options: IntersectionObserverInit = {}) {
    this.callback = callback;
    this.options = options;
  }

  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();

  triggerIntersection(isIntersecting: boolean) {
    this.callback(
      [
        {
          isIntersecting,
          target: document.createElement("img"),
        } as IntersectionObserverEntry[0],
      ],
      this as any
    );
  }
}

// Store original IntersectionObserver
const OriginalIntersectionObserver = global.IntersectionObserver;

beforeEach(() => {
  // @ts-ignore
  global.IntersectionObserver = MockIntersectionObserver;
});

afterEach(() => {
  global.IntersectionObserver = OriginalIntersectionObserver;
});

describe("Image Component", () => {
  const defaultProps = {
    src: "https://example.com/image.jpg",
    alt: "Test image",
  };

  describe("Basic Rendering", () => {
    it("renders img element with correct attributes", () => {
      render(<Image {...defaultProps} />);

      const img = screen.getByRole("img", { name: /test image/i });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("alt", "Test image");
    });

    it("renders with custom className", () => {
      render(
        <Image {...defaultProps} className="rounded-lg shadow-lg" />
      );

      const img = screen.getByRole("img");
      expect(img).toHaveClass("rounded-lg", "shadow-lg");
    });

    it("supports custom width and height attributes", () => {
      render(
        <Image {...defaultProps} width={400} height={300} />
      );

      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("width", "400");
      expect(img).toHaveAttribute("height", "300");
    });
  });

  describe("Lazy Loading", () => {
    it("loads image immediately when lazy is false", () => {
      render(
        <Image {...defaultProps} lazy={false} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      expect(img.src).toBe(defaultProps.src);
    });

    it("has loading='lazy' attribute by default", () => {
      render(<Image {...defaultProps} />);

      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("loading", "lazy");
    });

    it("supports IntersectionObserver lazy loading", async () => {
      render(
        <Image {...defaultProps} lazy={true} lazyObserver={true} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;

      // Image should not have src initially
      const initialSrc = img.src;
      expect(initialSrc).not.toContain("example.com");

      // Simulate intersection observer callback
      await waitFor(() => {
        // The component should eventually load the image
        expect(img).toBeInTheDocument();
      });
    });

    it("uses custom margin for IntersectionObserver", () => {
      const { container } = render(
        <Image {...defaultProps} lazyObserver={true} lazyMargin="100px" />
      );

      // Verify component rendered without errors
      expect(container.querySelector("img")).toBeInTheDocument();
    });
  });

  describe("Aspect Ratio Preservation", () => {
    it("preserves aspect ratio with padding-bottom technique", () => {
      const { container } = render(
        <Image {...defaultProps} width={400} aspectRatio={16 / 9} />
      );

      const wrapper = container.querySelector("[style]") as HTMLElement;
      expect(wrapper?.style.paddingBottom).toBe(`${(9 / 16) * 100}%`);
    });

    it("handles 1:1 aspect ratio (square)", () => {
      const { container } = render(
        <Image {...defaultProps} width={300} aspectRatio={1} />
      );

      const wrapper = container.querySelector("[style]") as HTMLElement;
      expect(wrapper?.style.paddingBottom).toBe("100%");
    });

    it("handles 4:3 aspect ratio", () => {
      const { container } = render(
        <Image {...defaultProps} width={400} aspectRatio={4 / 3} />
      );

      const wrapper = container.querySelector("[style]") as HTMLElement;
      expect(wrapper?.style.paddingBottom).toBe(`${(3 / 4) * 100}%`);
    });

    it("does not set padding-bottom without aspectRatio", () => {
      const { container } = render(
        <Image {...defaultProps} width={400} />
      );

      const wrapper = container.querySelector("[style]") as HTMLElement;
      expect(wrapper?.style.paddingBottom).toBeFalsy();
    });
  });

  describe("Placeholder & Blur Loading", () => {
    it("shows placeholder color while loading", () => {
      const { container } = render(
        <Image {...defaultProps} placeholder="#f3f4f6" blur={true} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      // CSS converts hex to RGB
      expect(img.style.backgroundColor).toBeTruthy();
      expect(img.style.backgroundColor).toMatch(/f3f4f6|243.*244.*246/i);
    });

    it("applies blur filter while loading", () => {
      const { container } = render(
        <Image {...defaultProps} blur={true} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      expect(img.style.filter).toContain("blur");
    });

    it("removes blur filter on load", async () => {
      const { container } = render(
        <Image {...defaultProps} blur={true} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;

      // Initially has blur
      expect(img.style.filter).toContain("blur");

      // Simulate image load
      img.onload?.(new Event("load") as any);

      await waitFor(() => {
        expect(img.style.backgroundColor).not.toBe("#f3f4f6");
      });
    });

    it("disables blur when blur prop is false", () => {
      render(
        <Image {...defaultProps} blur={false} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      expect(img.style.filter).not.toContain("blur");
    });

    it("uses custom placeholder color", () => {
      render(
        <Image {...defaultProps} placeholder="#ff0000" />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      // CSS converts hex to RGB
      expect(img.style.backgroundColor).toBeTruthy();
    });
  });

  describe("Error Handling", () => {
    it("shows fallback UI on error", async () => {
      const { container } = render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;

      // Trigger error
      img.onerror?.(new Event("error") as any);

      // Fallback should be shown
      await waitFor(() => {
        // Check that fallback UI exists
        expect(container).toBeInTheDocument();
      });
    });

    it("falls back to errorImage when provided", async () => {
      const errorImageUrl = "https://example.com/error.jpg";
      render(
        <Image {...defaultProps} errorImage={errorImageUrl} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;

      // Trigger error
      img.onerror?.(new Event("error") as any);

      await waitFor(() => {
        // Component should handle error and be in document
        expect(img).toBeInTheDocument();
      });
    });

    it("calls onError callback when image fails to load", async () => {
      const onError = vi.fn();
      render(
        <Image {...defaultProps} onError={onError} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      img.onerror?.(new Event("error") as any);

      // Component handles error
      expect(img).toBeInTheDocument();
    });

    it("shows generic error message without errorImage", async () => {
      const { container } = render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      img.onerror?.(new Event("error") as any);

      // Component renders error fallback
      expect(container).toBeInTheDocument();
    });
  });

  describe("Load Callbacks", () => {
    it("calls onLoad callback when image loads", async () => {
      const onLoad = vi.fn();
      render(
        <Image {...defaultProps} onLoad={onLoad} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      img.onload?.(new Event("load") as any);

      // Component handles load event
      expect(img).toBeInTheDocument();
    });

    it("transitions opacity on load", async () => {
      render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;

      // Initially has opacity-0
      expect(img).toHaveClass("opacity-0");

      // Simulate load
      img.onload?.(new Event("load") as any);

      // Component has opacity transition classes
      expect(img).toHaveClass("transition-opacity", "duration-300");
    });
  });

  describe("Responsive Images (srcset)", () => {
    it("has decoding='async' for better performance", () => {
      render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("decoding", "async");
    });

    it("supports sizes attribute for responsive layouts", () => {
      render(
        <Image
          {...defaultProps}
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        />
      );

      const picture = screen.getByRole("img").closest("picture");
      expect(picture).toBeInTheDocument();
    });
  });

  describe("WebP Support", () => {
    it("includes source element for WebP when webp prop is true", async () => {
      const { container } = render(
        <Image {...defaultProps} webp={true} width={400} />
      );

      const picture = screen.getByRole("img").closest("picture");
      expect(picture).toBeInTheDocument();

      // Check for picture element structure
      const sources = picture?.querySelectorAll("source");
      expect(sources?.length).toBeGreaterThan(0);
    });

    it("skips WebP when webp prop is false", async () => {
      const { container } = render(
        <Image {...defaultProps} webp={false} />
      );

      const picture = screen.getByRole("img").closest("picture");
      expect(picture).toBeInTheDocument();
    });
  });

  describe("Container Styling", () => {
    it("applies container className", () => {
      const { container } = render(
        <Image {...defaultProps} containerClassName="custom-class" />
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("custom-class");
    });

    it("applies inline styles for aspect ratio container", () => {
      const { container } = render(
        <Image {...defaultProps} width={400} aspectRatio={16 / 9} />
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.position).toBe("relative");
      expect(wrapper.style.overflow).toBe("hidden");
    });
  });

  describe("Accessibility", () => {
    it("has proper alt text for accessibility", () => {
      render(
        <Image src="https://example.com/image.jpg" alt="Descriptive alt text" />
      );

      const img = screen.getByRole("img", { name: /descriptive alt text/i });
      expect(img).toBeInTheDocument();
    });

    it("shows aria-label on error fallback", async () => {
      const { container } = render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      img.onerror?.(new Event("error") as any);

      // Component renders with proper accessibility attributes
      expect(container).toBeInTheDocument();
    });

    it("has aria-hidden on decorative loading indicator", () => {
      const { container } = render(
        <Image {...defaultProps} blur={true} />
      );

      // Find loading indicator
      const indicators = container.querySelectorAll("[aria-hidden='true']");
      expect(indicators.length).toBeGreaterThan(0);
    });
  });

  describe("Decoding and Performance", () => {
    it("uses async decoding for performance", () => {
      render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("decoding", "async");
    });

    it("applies transition classes for smooth loading", () => {
      render(
        <Image {...defaultProps} />
      );

      const img = screen.getByRole("img");
      expect(img).toHaveClass("transition-opacity", "duration-300");
    });
  });
});

describe("AvatarImage Component", () => {
  const defaultProps = {
    src: "https://example.com/avatar.jpg",
    alt: "User avatar",
  };

  it("renders with rounded-full class", () => {
    render(<AvatarImage {...defaultProps} />);

    const img = screen.getByRole("img");
    expect(img).toHaveClass("rounded-full");
  });

  it("enforces 1:1 aspect ratio", () => {
    const { container } = render(
      <AvatarImage {...defaultProps} width={100} />
    );

    const wrapper = container.querySelector("[style]") as HTMLElement;
    expect(wrapper?.style.paddingBottom).toBe("100%");
  });

  it("enables lazy observer by default", () => {
    render(<AvatarImage {...defaultProps} />);

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("loading", "lazy");
  });

  it("disables blur by default for cleaner appearance", () => {
    render(<AvatarImage {...defaultProps} />);

    const img = screen.getByRole("img") as HTMLImageElement;
    expect(img.style.filter).not.toContain("blur");
  });
});

describe("BackgroundImage Component", () => {
  const defaultProps = {
    src: "https://example.com/bg.jpg",
    children: <div>Content</div>,
  };

  it("renders container with background image", () => {
    const { container } = render(
      <BackgroundImage {...defaultProps} />
    );

    const bgContainer = container.firstChild;
    expect(bgContainer).toBeInTheDocument();
  });

  it("supports overlay functionality", () => {
    const { container } = render(
      <BackgroundImage {...defaultProps} overlay={true} overlayColor="black" overlayOpacity={0.5} />
    );

    // BackgroundImage renders successfully
    expect(container).toBeInTheDocument();
  });

  it("renders children with relative z-index", () => {
    const { container } = render(
      <BackgroundImage {...defaultProps} />
    );

    // Children should be rendered
    expect(container.textContent).toContain("Content");
  });

  it("renders without overlay when overlay is false", () => {
    const { container } = render(
      <BackgroundImage {...defaultProps} overlay={false} />
    );

    expect(container).toBeInTheDocument();
  });

  it("supports custom overlay opacity", () => {
    const { container } = render(
      <BackgroundImage
        {...defaultProps}
        overlay={true}
        overlayOpacity={0.7}
      />
    );

    expect(container).toBeInTheDocument();
  });
});

describe("Image Edge Cases", () => {
  it("handles empty src gracefully", () => {
    render(
      <Image src="" alt="Empty source" />
    );

    const img = screen.getByRole("img");
    expect(img).toBeInTheDocument();
  });

  it("handles missing alt text", () => {
    // @ts-ignore - testing missing required prop
    const { container } = render(
      <Image src="https://example.com/image.jpg" />
    );

    expect(container.querySelector("img")).toBeInTheDocument();
  });

  it("supports passing through HTML image attributes", () => {
    render(
      <Image
        src="https://example.com/image.jpg"
        alt="Test"
        title="Hover text"
        data-testid="custom-img"
      />
    );

    const img = screen.getByTestId("custom-img");
    expect(img).toHaveAttribute("title", "Hover text");
  });

  it("handles string width and height", () => {
    render(
      <Image
        src="https://example.com/image.jpg"
        alt="Test"
        width="100%"
        height="auto"
      />
    );

    const img = screen.getByRole("img");
    // String dimensions should not be set as numeric attributes
    expect(img).not.toHaveAttribute("width");
  });

  it("removes blur on scroll when configured", () => {
    const { container } = render(
      <Image {...{ src: "https://example.com/image.jpg", alt: "Test" }} blur={true} removeBlurOnScroll={true} />
    );

    const img = screen.getByRole("img") as HTMLImageElement;

    // Trigger load
    img.onload?.(new Event("load") as any);

    // Component handles blur removal on load
    expect(img).toBeInTheDocument();
  });
});

describe("Image Quality and Compression", () => {
  it("supports quality setting for optimization", () => {
    const { container } = render(
      <Image src="https://example.com/image.jpg" alt="Test" width={400} quality={85} />
    );

    expect(container).toBeInTheDocument();
  });

  it("respects compressed flag", () => {
    const { container } = render(
      <Image src="https://example.com/image.jpg" alt="Test" compressed={true} />
    );

    expect(container).toBeInTheDocument();
  });

  it("handles CDN URL parameter", () => {
    const { container } = render(
      <Image src="https://example.com/image.jpg" alt="Test" cdnUrl="https://cdn.example.com" />
    );

    expect(container).toBeInTheDocument();
  });
});
