/**
 * API client with CSRF token handling.
 *
 * The backend's starlette-csrf middleware is configured with:
 *   cookie_name="csrf_token", header_name="x-csrf-token"
 *
 * This client reads the `csrf_token` cookie and sends it as the
 * `X-CSRF-Token` header on state-changing requests (POST, PUT, DELETE, PATCH).
 * Handles 401 responses by redirecting to /login.
 */

const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";

function getCsrfToken(): string | null {
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${CSRF_COOKIE_NAME}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

const STATE_CHANGING_METHODS = new Set(["POST", "PUT", "DELETE", "PATCH"]);

interface ApiRequestOptions extends Omit<RequestInit, "method"> {
  method?: string;
  /**
   * When true, a 401 response will NOT trigger `window.location.href = "/login"`.
   * Instead the ApiClientError is thrown normally for the caller to handle.
   * Use this on the /api/auth/me call inside AuthProvider to avoid an infinite redirect loop.
   */
  suppressAuthRedirect?: boolean;
}

interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

export class ApiClientError extends Error {
  status: number;
  detail?: unknown;

  constructor({ status, message, detail }: ApiError) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiClient<T = unknown>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { method = "GET", headers: customHeaders, suppressAuthRedirect, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };

  // Include CSRF token on state-changing requests
  if (STATE_CHANGING_METHODS.has(method.toUpperCase())) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers[CSRF_HEADER_NAME] = csrfToken;
    }
  }

  const response = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    ...rest,
  });

  // Handle 401 by redirecting to login (unless caller suppresses the redirect)
  if (response.status === 401) {
    if (!suppressAuthRedirect) {
      window.location.href = "/login";
    }
    throw new ApiClientError({
      status: 401,
      message: "Unauthorized",
    });
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      // Response body may not be JSON
    }
    throw new ApiClientError({
      status: response.status,
      message: `API request failed: ${response.status} ${response.statusText}`,
      detail,
    });
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
