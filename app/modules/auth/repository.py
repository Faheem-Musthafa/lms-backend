"""Auth repositories — tenant-scoped data access for identity."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, or_, select

from app.core.database.repository import TenantRepository
from app.modules.auth.models import Role, User, UserSession


class UserRepository(TenantRepository[User]):
    model = User

    def _apply_search(self, stmt: Select, term: str) -> Select:
        like = f"%{term}%"
        return stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like)))

    async def get_by_email(self, email: str) -> User | None:
        stmt = self._select().where(User.email == email.lower())
        return (await self.session.execute(stmt)).scalar_one_or_none()


class RoleRepository(TenantRepository[Role]):
    model = Role

    async def get_by_code(self, code: str) -> Role | None:
        stmt = self._select().where(Role.code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_codes(self, codes: list[str]) -> list[Role]:
        stmt = self._select().where(Role.code.in_(codes))
        return list((await self.session.execute(stmt)).scalars().all())


class SessionRepository(TenantRepository[UserSession]):
    model = UserSession

    async def get_by_jti(self, jti: uuid.UUID) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.jti == jti)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        from sqlalchemy import func, update

        await self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
