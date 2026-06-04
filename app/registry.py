"""Import surface that populates ``Base.metadata`` and registers event handlers.

Alembic and the app both import this so every model + consumer is loaded
exactly once, in one place. Add new modules here.
"""

from __future__ import annotations

# importing the audit package registers the universal audit event consumer
import app.core.audit as _audit  # noqa: F401
from app.core.audit import models as _audit_models  # noqa: F401
from app.core.licensing import models as _licensing  # noqa: F401

# ── platform / core models ────────────────────────────────────────────────────
from app.core.tenancy import models as _tenancy  # noqa: F401
from app.modules.assignments import models as _assignments  # noqa: F401

# ── module models ─────────────────────────────────────────────────────────────
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.courses import models as _courses  # noqa: F401
from app.modules.learning import models as _learning  # noqa: F401

__all__ = ["_tenancy", "_licensing", "_audit_models", "_audit"]
