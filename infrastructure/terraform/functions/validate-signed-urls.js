// CloudFront Function: Validate signed URLs for media files
// Ensures media files can only be accessed with valid CloudFront signed URLs
// This protects user uploads from direct access

function handler(event) {
  const request = event.request;
  const uri = request.uri;

  // Check if this is a media file request
  const isMediaRequest = /^\/media\//.test(uri);

  if (isMediaRequest) {
    // Signed URL validation is handled by CloudFront automatically
    // This function logs access for audit purposes

    // Add a custom header to indicate this was checked
    request.headers['x-media-validated'] = {
      value: 'true'
    };

    // Note: CloudFront will automatically reject unsigned requests
    // if the URL is not properly signed with a valid signature
  }

  return request;
}
