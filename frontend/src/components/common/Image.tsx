import React, { useState, useEffect, useRef, ImgHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/**
 * Image component with comprehensive optimization:
 * - Responsive images with srcset
 * - Lazy loading with IntersectionObserver
 * - WebP format support with fallback
 * - Aspect ratio preservation
 * - Blur placeholder while loading
 * - Error fallback
 *
 * @example
 * <Image
 *   src="/images/photo.jpg"
 *   alt="Profile photo"
 *   width={400}
 *   height={300}
 *   aspectRatio={4/3}
 *   blur
 * />
 */

interface ImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  /** Image source URL */
  src: string;
  /** Alternative text for accessibility */
  alt: string;
  /** Image width (for responsive sizing) */
  width?: number | string;
  /** Image height (for responsive sizing) */
  height?: number | string;
  /** Aspect ratio for layout shift prevention (e.g., 16/9) */
  aspectRatio?: number;
  /** Enable blur placeholder on load */
  blur?: boolean;
  /** Placeholder color while loading */
  placeholder?: string;
  /** Enable native lazy loading */
  lazy?: boolean;
  /** Enable IntersectionObserver for lazy loading */
  lazyObserver?: boolean;
  /** Margin for IntersectionObserver (e.g., "50px") */
  lazyMargin?: string;
  /** Support WebP format (if available) */
  webp?: boolean;
  /** Image quality for srcset (1-100) */
  quality?: number;
  /** Sizes for responsive images */
  sizes?: string;
  /** CDN base URL for optimization */
  cdnUrl?: string;
  /** Custom error image URL */
  errorImage?: string;
  /** Callback when image loads */
  onLoad?: (e: React.SyntheticEvent<HTMLImageElement>) => void;
  /** Callback on error */
  onError?: (e: React.SyntheticEvent<HTMLImageElement>) => void;
  /** Container className */
  containerClassName?: string;
  /** Enable compression detection */
  compressed?: boolean;
  /** Remove blur on scroll */
  removeBlurOnScroll?: boolean;
}

/**
 * Utility to check if browser supports WebP
 */
const checkWebPSupport = async (): Promise<boolean> => {
  // Use HTMLImageElement constructor explicitly to avoid naming conflicts
  const webpImage = document.createElement('img');
  return new Promise((resolve) => {
    webpImage.onload = webpImage.onerror = () => resolve(webpImage.height === 2);
    webpImage.src =
      "data:image/webp;base64,UklGRjoAAABXRUJQVkA4IC4AAABwAQCdASoBAAEAAkA4JaACdLoB/gAA/v8BP";
  });
};

/**
 * Generate srcset from base URL
 * Creates multiple versions for different screen densities
 */
const generateSrcSet = (
  url: string,
  width: number | string | undefined,
  quality: number = 75,
  includeWebP: boolean = false
): string => {
  if (typeof width !== "number") return url;

  const baseUrl = new URL(url, typeof window !== "undefined" ? window.location.href : "");
  const params = new URLSearchParams(baseUrl.search);

  // Generate sizes: 1x, 1.5x, 2x, 3x
  const sizes = [1, 1.5, 2, 3];
  const srcset = sizes
    .map((density) => {
      const newParams = new URLSearchParams(params);
      newParams.set("w", String(Math.round(Number(width) * density)));
      newParams.set("q", String(quality));

      const srcWithParams = `${baseUrl.origin}${baseUrl.pathname}?${newParams}`;
      const dprValue = density === 1 ? "1x" : `${density}x`;

      return `${srcWithParams} ${dprValue}`;
    })
    .join(", ");

  return srcset;
};

/**
 * Get optimized image URL with format negotiation
 */
const getOptimizedUrl = (
  url: string,
  width: number | string | undefined,
  webpSupported: boolean
): { src: string; srcWebP?: string } => {
  if (!url) return { src: "" };

  const baseUrl = new URL(url, typeof window !== "undefined" ? window.location.href : "");
  const ext = baseUrl.pathname.split(".").pop()?.toLowerCase();

  // Don't process already optimized formats
  if (ext === "webp" || ext === "svg") {
    return { src: url };
  }

  // Generate WebP variant if supported
  const srcWebP = webpSupported && ext ? url.replace(`.${ext}`, ".webp") : undefined;

  return {
    src: url,
    srcWebP,
  };
};

/**
 * Calculate blur filter intensity based on aspect ratio
 */
const calculateBlurIntensity = (): string => {
  return "blur(20px)";
};

/**
 * Image Component
 */
export const Image: React.FC<ImageProps> = ({
  src,
  alt,
  width,
  height,
  aspectRatio,
  blur = true,
  placeholder = "#f3f4f6",
  lazy = true,
  lazyObserver = false,
  lazyMargin = "50px",
  webp = true,
  quality = 75,
  sizes,
  cdnUrl,
  errorImage,
  onLoad,
  onError,
  containerClassName,
  compressed = true,
  removeBlurOnScroll = true,
  className,
  ...props
}) => {
  const [imageSrc, setImageSrc] = useState<string | null>(lazy && lazyObserver ? null : src);
  const [srcSet, setSrcSet] = useState<string>("");
  const [srcSetWebP, setSrcSetWebP] = useState<string>("");
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [webpSupported, setWebpSupported] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const intersectionObserverRef = useRef<IntersectionObserver | null>(null);

  // Check WebP support
  useEffect(() => {
    if (!webp) return;

    checkWebPSupport().then((supported) => {
      setWebpSupported(supported);
    });
  }, [webp]);

  // Setup lazy loading with IntersectionObserver
  useEffect(() => {
    if (!lazyObserver || !imgRef.current) return;

    intersectionObserverRef.current = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setImageSrc(src);
          if (intersectionObserverRef.current) {
            intersectionObserverRef.current.unobserve(entry.target);
          }
        }
      },
      {
        rootMargin: lazyMargin,
      }
    );

    intersectionObserverRef.current.observe(imgRef.current);

    return () => {
      if (intersectionObserverRef.current) {
        intersectionObserverRef.current.disconnect();
      }
    };
  }, [src, lazyMargin, lazyObserver]);

  // Generate responsive srcsets
  useEffect(() => {
    if (!imageSrc) return;

    // Generate standard srcset
    const srcSet = generateSrcSet(imageSrc, width, quality, false);
    setSrcSet(srcSet);

    // Generate WebP srcset if supported
    if (webpSupported) {
      const webpUrl = imageSrc.replace(/\.[^.]+$/, ".webp");
      const srcSetWebP = generateSrcSet(webpUrl, width, quality, true);
      setSrcSetWebP(srcSetWebP);
    }
  }, [imageSrc, width, quality, webpSupported]);

  const handleLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    setIsLoaded(true);
    setHasError(false);
    onLoad?.(e);

    // Optional: Remove blur on scroll
    if (removeBlurOnScroll && imgRef.current) {
      imgRef.current.style.filter = "";
    }
  };

  const handleError = (e: React.SyntheticEvent<HTMLImageElement>) => {
    if (errorImage && imageSrc !== errorImage) {
      setImageSrc(errorImage);
      return;
    }

    setHasError(true);
    setIsLoaded(true);
    onError?.(e);
  };

  // Inline styles for aspect ratio preservation
  const containerStyle: React.CSSProperties = {
    position: "relative",
    overflow: "hidden",
  };

  if (aspectRatio && typeof width === "number") {
    containerStyle.paddingBottom = `${(1 / aspectRatio) * 100}%`;
    containerStyle.width = typeof width === "number" ? `${width}px` : width;
  }

  const imageStyle: React.CSSProperties = {
    display: "block",
    width: "100%",
    height: "auto",
    backgroundColor: !isLoaded ? placeholder : undefined,
    filter: !isLoaded && blur ? calculateBlurIntensity() : undefined,
    transition: "filter 0.3s ease-out, opacity 0.3s ease-out",
  };

  // Error state: show fallback
  if (hasError && !errorImage) {
    return (
      <div
        ref={containerRef}
        className={cn(
          "flex items-center justify-center bg-muted text-muted-foreground",
          containerClassName
        )}
        style={{
          ...containerStyle,
          minHeight: height || 200,
        }}
        role="img"
        aria-label={`Failed to load: ${alt}`}
      >
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 opacity-50"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="mt-2 text-sm">{alt}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={containerClassName}
      style={containerStyle}
    >
      {/* Picture element for format negotiation */}
      <picture>
        {/* WebP format for browsers that support it */}
        {webpSupported && srcSetWebP && (
          <source srcSet={srcSetWebP} type="image/webp" />
        )}

        {/* Standard format fallback */}
        {srcSet && <source srcSet={srcSet} sizes={sizes} />}

        {/* IMG tag */}
        <img
          ref={imgRef}
          src={imageSrc || undefined}
          alt={alt}
          width={typeof width === "number" ? width : undefined}
          height={typeof height === "number" ? height : undefined}
          className={cn(
            "transition-opacity duration-300",
            isLoaded ? "opacity-100" : "opacity-0",
            className
          )}
          style={imageStyle}
          loading={lazy ? "lazy" : "eager"}
          onLoad={handleLoad}
          onError={handleError}
          decoding="async"
          {...props}
        />
      </picture>

      {/* Loading indicator (optional) */}
      {!isLoaded && blur && (
        <div
          className="absolute inset-0 animate-pulse"
          style={{ backgroundColor: placeholder }}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

Image.displayName = "Image";

/**
 * Optimized avatar image component
 */
export const AvatarImage: React.FC<ImageProps> = (props) => {
  return (
    <Image
      {...props}
      aspectRatio={1}
      blur={false}
      lazyObserver={true}
      className={cn("rounded-full", props.className)}
    />
  );
};

AvatarImage.displayName = "AvatarImage";

/**
 * Optimized background image component
 */
interface BackgroundImageProps extends Omit<ImageProps, "alt"> {
  alt?: string;
  children?: React.ReactNode;
  overlay?: boolean;
  overlayColor?: string;
  overlayOpacity?: number;
}

export const BackgroundImage: React.FC<BackgroundImageProps> = ({
  src,
  alt = "Background image",
  children,
  overlay = false,
  overlayColor = "black",
  overlayOpacity = 0.3,
  ...props
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [bgImage, setBgImage] = useState<string | null>(null);

  useEffect(() => {
    // Preload image
    const imgElement = document.createElement('img');
    imgElement.onload = () => setBgImage(src);
    imgElement.onerror = () => console.error(`Failed to load background image: ${src}`);
    imgElement.src = src;
  }, [src]);

  return (
    <div
      ref={containerRef}
      className="relative overflow-hidden"
      style={{
        backgroundImage: bgImage ? `url(${bgImage})` : undefined,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {overlay && (
        <div
          className="absolute inset-0"
          style={{
            backgroundColor: overlayColor,
            opacity: overlayOpacity,
          }}
          aria-hidden="true"
        />
      )}

      {children && (
        <div className="relative z-10">
          {children}
        </div>
      )}
    </div>
  );
};

BackgroundImage.displayName = "BackgroundImage";
