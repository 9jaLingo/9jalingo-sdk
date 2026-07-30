/** Base exception for all 9jaLingo SDK errors. */
export class NaijaLingoError extends Error {
  readonly statusCode?: number;
  readonly response?: unknown;

  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message);
    this.name = "NaijaLingoError";
    this.statusCode = statusCode;
    this.response = response;
  }
}

/** Raised when the API key is missing or invalid. */
export class AuthenticationError extends NaijaLingoError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "AuthenticationError";
  }
}

/** Raised when rate limit is exceeded. */
export class RateLimitError extends NaijaLingoError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "RateLimitError";
  }
}

/** Raised when a requested resource is not found. */
export class NotFoundError extends NaijaLingoError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "NotFoundError";
  }
}

/** Raised when the API returns a 5xx error. */
export class ServerError extends NaijaLingoError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "ServerError";
  }
}

/** Raised when the inference GPU is waking from scale-to-zero. */
export class InferenceCapacityError extends ServerError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "InferenceCapacityError";
  }
}

/** Raised when unable to connect to the API. */
export class ConnectionError extends NaijaLingoError {
  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message, statusCode, response);
    this.name = "ConnectionError";
  }
}
