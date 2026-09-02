package naijalingo

import "fmt"

// APIError describes an unsuccessful response from the 9jaLingo API.
type APIError struct {
	StatusCode int
	Message    string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("9jalingo API error (%d): %s", e.StatusCode, e.Message)
}

func (e *APIError) Is(target error) bool {
	other, ok := target.(*APIError)
	return ok && (other.StatusCode == 0 || other.StatusCode == e.StatusCode)
}

var (
	ErrAuthentication = &APIError{StatusCode: 401}
	ErrNotFound       = &APIError{StatusCode: 404}
	ErrRateLimited    = &APIError{StatusCode: 429}
)
