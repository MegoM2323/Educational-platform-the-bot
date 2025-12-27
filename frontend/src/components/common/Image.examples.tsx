/**
 * Image Component - Usage Examples
 *
 * Comprehensive examples demonstrating all optimization features
 */

import React from "react";
import { Image, AvatarImage, BackgroundImage } from "./Image";

// Basic Usage
export const BasicImageExample = () => (
  <Image
    src="https://example.com/photo.jpg"
    alt="Beautiful landscape"
    width={400}
    height={300}
  />
);

// Responsive Image with Aspect Ratio
export const ResponsiveImageExample = () => (
  <Image
    src="https://example.com/hero.jpg"
    alt="Hero banner"
    width={1200}
    aspectRatio={16 / 9}
    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
  />
);

// Image with Lazy Loading and IntersectionObserver
export const LazyImageExample = () => (
  <Image
    src="https://example.com/lazy-load.jpg"
    alt="Lazy loaded image"
    width={600}
    height={400}
    lazyObserver={true}
    lazyMargin="100px"
    blur={true}
  />
);

// Image with WebP Support and Quality Control
export const OptimizedImageExample = () => (
  <Image
    src="https://example.com/optimized.jpg"
    alt="Optimized for web"
    width={800}
    height={600}
    webp={true}
    quality={75}
    compressed={true}
  />
);

// Image with Error Handling
export const ImageWithErrorHandlingExample = () => (
  <Image
    src="https://example.com/image.jpg"
    alt="Image with error fallback"
    width={400}
    height={300}
    errorImage="https://example.com/placeholder.jpg"
    onError={() => console.log("Image failed to load")}
  />
);

// Avatar Image (Optimized for Profile Pictures)
export const AvatarImageExample = () => (
  <AvatarImage
    src="https://example.com/profile.jpg"
    alt="User profile picture"
    width={100}
    className="border-2 border-blue-500"
  />
);

// Multiple Avatar Variants
export const AvatarVariantsExample = () => (
  <div className="flex gap-4">
    <AvatarImage src="https://example.com/user1.jpg" alt="User 1" width={60} />
    <AvatarImage src="https://example.com/user2.jpg" alt="User 2" width={80} />
    <AvatarImage src="https://example.com/user3.jpg" alt="User 3" width={100} />
  </div>
);

// Background Image with Overlay
export const BackgroundImageWithOverlayExample = () => (
  <BackgroundImage
    src="https://example.com/background.jpg"
    overlay={true}
    overlayColor="black"
    overlayOpacity={0.5}
  >
    <div className="p-8 text-white">
      <h1 className="text-4xl font-bold">Welcome</h1>
      <p className="mt-2 text-lg">This text appears over the background image</p>
    </div>
  </BackgroundImage>
);

// Material Card with Image
export const MaterialCardImageExample = () => (
  <div className="bg-white rounded-lg shadow-md overflow-hidden max-w-sm">
    <Image
      src="https://example.com/material-thumbnail.jpg"
      alt="Course thumbnail"
      width={400}
      height={250}
      aspectRatio={16 / 10}
      blur={true}
    />
    <div className="p-4">
      <h3 className="font-bold text-lg">Advanced React Patterns</h3>
      <p className="text-gray-600 mt-2">Learn advanced React techniques</p>
    </div>
  </div>
);

// Gallery Grid with Lazy Loading
export const ImageGalleryExample = () => {
  const images = [
    { id: 1, src: "https://example.com/gallery1.jpg", alt: "Gallery 1" },
    { id: 2, src: "https://example.com/gallery2.jpg", alt: "Gallery 2" },
    { id: 3, src: "https://example.com/gallery3.jpg", alt: "Gallery 3" },
    { id: 4, src: "https://example.com/gallery4.jpg", alt: "Gallery 4" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {images.map((image) => (
        <Image
          key={image.id}
          src={image.src}
          alt={image.alt}
          width={300}
          height={300}
          aspectRatio={1}
          lazyObserver={true}
          blur={true}
          className="rounded-lg object-cover"
        />
      ))}
    </div>
  );
};

// Student Assignment Submission with Images
export const AssignmentImageExample = () => (
  <div className="bg-gray-50 p-6 rounded-lg">
    <h3 className="font-bold mb-4">Submitted Work</h3>
    <Image
      src="https://example.com/student-work.jpg"
      alt="Student assignment submission"
      width={600}
      height={400}
      aspectRatio={3 / 2}
      lazyObserver={true}
      blur={true}
      onLoad={() => console.log("Student work image loaded")}
    />
  </div>
);

// Teacher Dashboard with Student Photos
export const TeacherDashboardImageExample = () => (
  <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
    {[1, 2, 3, 4, 5, 6].map((studentId) => (
      <div key={studentId} className="bg-white rounded-lg p-4 shadow">
        <AvatarImage
          src={`https://example.com/student${studentId}.jpg`}
          alt={`Student ${studentId}`}
          width={120}
          className="mx-auto mb-2"
        />
        <h4 className="text-center font-semibold">Student {studentId}</h4>
        <p className="text-center text-sm text-gray-600">Class A</p>
      </div>
    ))}
  </div>
);

// Material Bank with Images
export const MaterialBankImageExample = () => (
  <div className="space-y-4">
    {[
      {
        id: 1,
        title: "Algebra Fundamentals",
        image: "https://example.com/algebra.jpg",
      },
      {
        id: 2,
        title: "Geometry Basics",
        image: "https://example.com/geometry.jpg",
      },
      {
        id: 3,
        title: "Calculus Introduction",
        image: "https://example.com/calculus.jpg",
      },
    ].map((material) => (
      <div key={material.id} className="flex gap-4 bg-white p-4 rounded-lg">
        <Image
          src={material.image}
          alt={material.title}
          width={150}
          height={120}
          aspectRatio={5 / 4}
          blur={true}
          lazyObserver={true}
          className="rounded"
        />
        <div className="flex-1">
          <h3 className="font-bold text-lg">{material.title}</h3>
          <p className="text-gray-600 mt-2">Complete course material</p>
        </div>
      </div>
    ))}
  </div>
);

// Responsive Picture with Different Sizes
export const ResponsivePictureExample = () => (
  <Image
    src="https://example.com/responsive.jpg"
    alt="Responsive image"
    width={800}
    height={600}
    sizes={`
      (max-width: 480px) 100vw,
      (max-width: 768px) 90vw,
      (max-width: 1024px) 70vw,
      60vw
    `}
    webp={true}
    quality={80}
  />
);

// Performance Optimization Demo
export const PerformanceOptimizedExample = () => (
  <div className="space-y-4">
    <h2 className="text-2xl font-bold">Optimized Images</h2>

    {/* Banner with highest compression */}
    <Image
      src="https://example.com/banner.jpg"
      alt="Marketing banner"
      width={1200}
      height={400}
      aspectRatio={3 / 1}
      quality={60}
      webp={true}
      lazyObserver={true}
      blur={true}
    />

    {/* Gallery with balanced compression */}
    <div className="grid grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <Image
          key={i}
          src={`https://example.com/gallery${i + 1}.jpg`}
          alt={`Gallery item ${i + 1}`}
          width={300}
          height={300}
          aspectRatio={1}
          quality={75}
          webp={true}
          lazyObserver={true}
          blur={true}
          className="rounded-lg object-cover"
        />
      ))}
    </div>

    {/* Detailed image with higher quality */}
    <Image
      src="https://example.com/detailed.jpg"
      alt="High quality detailed image"
      width={800}
      height={600}
      aspectRatio={4 / 3}
      quality={90}
      webp={true}
      lazyObserver={false}
      blur={false}
    />
  </div>
);

// Knowledge Graph Lesson with Images
export const KnowledgeGraphImageExample = () => (
  <div className="bg-white p-6 rounded-lg shadow">
    <h2 className="text-2xl font-bold mb-4">Lesson: Solar System</h2>

    <div className="mb-6">
      <h3 className="font-semibold mb-3">The Sun</h3>
      <Image
        src="https://example.com/sun.jpg"
        alt="The Sun"
        width={600}
        height={400}
        aspectRatio={3 / 2}
        lazyObserver={true}
        blur={true}
      />
    </div>

    <div className="grid grid-cols-3 gap-4">
      {["Mercury", "Venus", "Earth"].map((planet, i) => (
        <div key={planet}>
          <h4 className="font-semibold mb-2">{planet}</h4>
          <Image
            src={`https://example.com/planet${i + 1}.jpg`}
            alt={planet}
            width={300}
            height={300}
            aspectRatio={1}
            lazyObserver={true}
            blur={true}
            className="rounded"
          />
        </div>
      ))}
    </div>
  </div>
);

// User Profile with Background and Avatar
export const UserProfileExample = () => (
  <div className="bg-white rounded-lg overflow-hidden shadow-lg">
    {/* Background image */}
    <BackgroundImage
      src="https://example.com/profile-bg.jpg"
      overlay={true}
      overlayOpacity={0.3}
    >
      <div className="h-32" />
    </BackgroundImage>

    {/* Profile content */}
    <div className="px-6 pb-6">
      <div className="flex gap-4 -mt-16 mb-4">
        <AvatarImage
          src="https://example.com/user-avatar.jpg"
          alt="User avatar"
          width={120}
          className="border-4 border-white rounded-full"
        />
        <div className="mt-8">
          <h2 className="text-2xl font-bold">John Doe</h2>
          <p className="text-gray-600">Student</p>
        </div>
      </div>

      <p className="text-gray-700">
        Passionate about learning and creative problem solving.
      </p>
    </div>
  </div>
);

// Forum Post with User Avatar and Image
export const ForumPostExample = () => (
  <div className="bg-white p-6 rounded-lg border">
    <div className="flex gap-4 mb-4">
      <AvatarImage
        src="https://example.com/author.jpg"
        alt="Author"
        width={50}
        className="rounded-full"
      />
      <div>
        <h4 className="font-bold">Sarah Johnson</h4>
        <p className="text-sm text-gray-500">2 hours ago</p>
      </div>
    </div>

    <h3 className="text-xl font-bold mb-2">How to Solve This Math Problem?</h3>
    <p className="text-gray-700 mb-4">
      I'm stuck on this differential equation problem. Can anyone help?
    </p>

    <Image
      src="https://example.com/math-problem.jpg"
      alt="Math problem screenshot"
      width={600}
      height={400}
      aspectRatio={3 / 2}
      blur={true}
      lazyObserver={true}
      className="rounded-lg mb-4"
    />

    <p className="text-gray-600 text-sm">
      Any hints or solutions would be appreciated!
    </p>
  </div>
);
