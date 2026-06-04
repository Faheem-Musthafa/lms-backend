# importing handlers registers the universal audit event consumer
from app.core.audit import handlers as _handlers  # noqa: F401
from app.core.audit.models import AuditLog
from app.core.audit.service import AuditService

__all__ = ["AuditLog", "AuditService"]
