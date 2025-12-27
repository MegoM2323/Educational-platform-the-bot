#!/usr/bin/env node

/**
 * Build Performance Monitoring Script
 * Tracks build metrics and generates reports
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import os from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Build metrics storage
const METRICS_FILE = path.join(process.cwd(), 'frontend', '.build-metrics.json');
const BUILD_THRESHOLDS = {
  maxBuildTime: 15000, // 15 seconds in milliseconds
  maxBundleSize: 250000, // 250 KB in bytes
  maxCSSSize: 100000, // 100 KB in bytes
};

/**
 * Parse build output to extract metrics
 */
function parseBuildOutput() {
  try {
    const distDir = path.join(process.cwd(), 'frontend', 'dist');

    // Check if dist directory exists
    if (!fs.existsSync(distDir)) {
      console.error('ERROR: dist directory not found');
      return null;
    }

    // Calculate bundle sizes
    const stats = {
      timestamp: new Date().toISOString(),
      distSize: getDirSize(distDir),
      jsSize: 0,
      cssSize: 0,
      assets: {
        jsCount: 0,
        cssCount: 0,
        imageCount: 0,
        fontCount: 0,
      },
    };

    // Count and size files by type
    const files = getAllFiles(distDir);
    files.forEach((file) => {
      const size = fs.statSync(file).size;
      const ext = path.extname(file);

      if (ext === '.js') {
        stats.jsSize += size;
        stats.assets.jsCount++;
      } else if (ext === '.css') {
        stats.cssSize += size;
        stats.assets.cssCount++;
      } else if (['.jpg', '.png', '.gif', '.svg', '.webp'].includes(ext)) {
        stats.assets.imageCount++;
      } else if (['.woff', '.woff2', '.ttf', '.otf'].includes(ext)) {
        stats.assets.fontCount++;
      }
    });

    return stats;
  } catch (error) {
    console.error('Error parsing build output:', error);
    return null;
  }
}

/**
 * Get total directory size
 */
function getDirSize(dir) {
  let size = 0;
  const files = getAllFiles(dir);
  files.forEach((file) => {
    size += fs.statSync(file).size;
  });
  return size;
}

/**
 * Recursively get all files in directory
 */
function getAllFiles(dir) {
  const files = [];

  function traverse(currentDir) {
    const items = fs.readdirSync(currentDir);
    items.forEach((item) => {
      const fullPath = path.join(currentDir, item);
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        traverse(fullPath);
      } else {
        files.push(fullPath);
      }
    });
  }

  traverse(dir);
  return files;
}

/**
 * Check if metrics meet performance thresholds
 */
function checkThresholds(stats) {
  const warnings = [];
  const errors = [];

  if (stats.distSize > BUILD_THRESHOLDS.maxBundleSize) {
    errors.push(
      `Bundle size (${formatBytes(stats.distSize)}) exceeds limit (${formatBytes(BUILD_THRESHOLDS.maxBundleSize)})`
    );
  }

  if (stats.cssSize > BUILD_THRESHOLDS.maxCSSSize) {
    warnings.push(
      `CSS size (${formatBytes(stats.cssSize)}) exceeds limit (${formatBytes(BUILD_THRESHOLDS.maxCSSSize)})`
    );
  }

  return { warnings, errors };
}

/**
 * Load historical metrics
 */
function loadHistoricalMetrics() {
  try {
    if (fs.existsSync(METRICS_FILE)) {
      const data = fs.readFileSync(METRICS_FILE, 'utf-8');
      return JSON.parse(data);
    }
  } catch (error) {
    console.warn('Could not load historical metrics:', error.message);
  }
  return [];
}

/**
 * Save metrics to history
 */
function saveMetrics(stats) {
  try {
    const history = loadHistoricalMetrics();
    history.push(stats);

    // Keep only last 100 builds
    if (history.length > 100) {
      history.shift();
    }

    fs.writeFileSync(METRICS_FILE, JSON.stringify(history, null, 2));
  } catch (error) {
    console.error('Could not save metrics:', error.message);
  }
}

/**
 * Format bytes to human-readable format
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Generate build report
 */
function generateReport(stats, thresholds) {
  console.log('\n' + '='.repeat(60));
  console.log('BUILD PERFORMANCE REPORT');
  console.log('='.repeat(60));

  console.log('\nBundle Statistics:');
  console.log(`  Total Size:      ${formatBytes(stats.distSize)}`);
  console.log(`  JavaScript:      ${formatBytes(stats.jsSize)} (${stats.assets.jsCount} files)`);
  console.log(`  CSS:             ${formatBytes(stats.cssSize)} (${stats.assets.cssCount} files)`);
  console.log(`  Images:          ${stats.assets.imageCount} files`);
  console.log(`  Fonts:           ${stats.assets.fontCount} files`);

  console.log('\nPerformance Targets:');
  console.log(`  Max Bundle:      ${formatBytes(BUILD_THRESHOLDS.maxBundleSize)} (status: ${
    stats.distSize <= BUILD_THRESHOLDS.maxBundleSize ? '✓ OK' : '✗ FAIL'
  })`);
  console.log(`  Max CSS:         ${formatBytes(BUILD_THRESHOLDS.maxCSSSize)} (status: ${
    stats.cssSize <= BUILD_THRESHOLDS.maxCSSSize ? '✓ OK' : '✗ FAIL'
  })`);
  console.log(`  Build Time:      ${BUILD_THRESHOLDS.maxBuildTime}ms (target < 15s)`);

  if (thresholds.warnings.length > 0) {
    console.log('\nWarnings:');
    thresholds.warnings.forEach((warning) => {
      console.log(`  ⚠ ${warning}`);
    });
  }

  if (thresholds.errors.length > 0) {
    console.log('\nErrors:');
    thresholds.errors.forEach((error) => {
      console.log(`  ✗ ${error}`);
    });
  }

  console.log('\n' + '='.repeat(60));
}

/**
 * Detect performance regressions
 */
function detectRegressions(stats, history) {
  if (history.length < 2) {
    console.log('Regression detection: Not enough historical data');
    return [];
  }

  const regressions = [];
  const previousStats = history[history.length - 2];

  const buildTimePct = ((stats.distSize - previousStats.distSize) / previousStats.distSize) * 100;
  const threshold = 5; // 5% threshold

  if (buildTimePct > threshold) {
    regressions.push(
      `Bundle size increased by ${buildTimePct.toFixed(1)}% (${formatBytes(stats.distSize)} vs ${formatBytes(previousStats.distSize)})`
    );
  }

  return regressions;
}

/**
 * Main function
 */
async function main() {
  console.log('Starting build performance analysis...\n');

  const stats = parseBuildOutput();
  if (!stats) {
    console.error('Failed to parse build output');
    process.exit(1);
  }

  const thresholds = checkThresholds(stats);
  const history = loadHistoricalMetrics();
  const regressions = detectRegressions(stats, history);

  generateReport(stats, thresholds);

  if (regressions.length > 0) {
    console.log('\nPerformance Regressions Detected:');
    regressions.forEach((regression) => {
      console.log(`  ⚠ ${regression}`);
    });
  }

  // Save metrics
  saveMetrics(stats);

  // Exit with appropriate code
  if (thresholds.errors.length > 0) {
    console.error('\nBuild failed: Performance thresholds exceeded');
    process.exit(1);
  }

  console.log('\n✓ Build passed all performance checks\n');
  process.exit(0);
}

main().catch((error) => {
  console.error('Unexpected error:', error);
  process.exit(1);
});
