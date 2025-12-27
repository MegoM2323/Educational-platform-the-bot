// CloudFront Function: Add cache headers for optimal caching
// Adds Cache-Control headers based on file type

function handler(event) {
  const request = event.request;
  const uri = request.uri;

  // Get file extension
  const ext = uri.split('.').pop().toLowerCase();

  // Hashed assets pattern: -[a-f0-9]{8}.js, -[a-f0-9]{8}.css, etc.
  // These can be cached for 1 year since the hash changes when content changes
  const hashedAssetPattern = /-[a-f0-9]{8,}\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2|ttf|otf|eot)$/i;

  if (hashedAssetPattern.test(uri)) {
    // Hashed assets - cache for 1 year
    request.headers['cache-control'] = {
      value: 'public, max-age=31536000, immutable'
    };
  } else if (/\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2|ttf|otf|eot|json|xml)$/i.test(uri)) {
    // Non-hashed static assets - cache for 30 days
    request.headers['cache-control'] = {
      value: 'public, max-age=2592000, must-revalidate'
    };
  } else if (/\.html$/i.test(uri)) {
    // HTML files - revalidate frequently (1 hour)
    request.headers['cache-control'] = {
      value: 'public, max-age=3600, must-revalidate'
    };
  } else {
    // Default - short cache (1 hour)
    request.headers['cache-control'] = {
      value: 'public, max-age=3600'
    };
  }

  // Add Vary header for proper cache key handling
  request.headers['vary'] = {
    value: 'Accept-Encoding'
  };

  return request;
}
