from typing import Any, Dict, List, Optional


class AppException(Exception):
    """Base application exception with standardized code and status mapping."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class EntityNotFoundError(AppException):
    def __init__(self, message: str = "Resource yang diminta tidak ditemukan.", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, code="NOT_FOUND", status_code=404, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Token autentikasi tidak valid atau tidak disertakan.", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Anda tidak memiliki hak akses pada resource ini.", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, code="FORBIDDEN", status_code=403, details=details)


class BadRequestError(AppException):
    def __init__(self, message: str = "Permintaan tidak dapat diproses karena data tidak valid.", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, code="BAD_REQUEST", status_code=400, details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Terjadi konflik state data.", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, code="CONFLICT", status_code=409, details=details)


class DatabaseUnavailableError(AppException):
    def __init__(self, message: str = "Layanan database Feature Store tidak dapat diakses atau timeout.", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, code="DATABASE_UNAVAILABLE", status_code=503, details=details)
