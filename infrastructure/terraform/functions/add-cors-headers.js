// CloudFront Function: Add CORS headers for web fonts
// Enables fonts to be loaded from cross-origin requests

function handler(event) {
  const request = event.request;
  const response = event.response;

  // Check if this is a font request
  const isFontRequest = /\.(woff|woff2|ttf|otf|eot)$/i.test(request.uri);

  if (isFontRequest) {
    // Allow fonts to be loaded from any origin
    response.headers['access-control-allow-origin'] = {
      value: '*'
    };

    // Specify allowed methods
    response.headers['access-control-allow-methods'] = {
      value: 'GET, HEAD, OPTIONS'
    };

    // Cache CORS headers with the response
    response.headers['access-control-max-age'] = {
      value: '86400'  // 24 hours
    };

    // Allow caching of CORS requests
    response.headers['vary'] = {
      value: 'Origin'
    };
  }

  return response;
}
