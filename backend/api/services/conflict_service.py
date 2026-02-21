"""
Conflict Service – CRUD and statistics for mapping conflicts.
"""

from datetime import datetime

from pipeline.models import get_session, MappingConflict


class ConflictService:
    """Manages MappingConflict records (list, detail, update, bulk, stats)."""

    @staticmethod
    def _session():
        return get_session()

    # ── list ─────────────────────────────────────────────────────────────

    @staticmethod
    def list_conflicts(
        page: int = 1,
        per_page: int = 25,
        status: str | None = None,
        source_system: str | None = None,
        target_system: str | None = None,
        reason: str | None = None,
        search: str = "",
    ) -> dict:
        session = ConflictService._session()
        try:
            query = session.query(MappingConflict)

            if status:
                query = query.filter(MappingConflict.status == status)
            if source_system:
                query = query.filter(MappingConflict.source_system == source_system)
            if target_system:
                query = query.filter(MappingConflict.target_system == target_system)
            if reason:
                query = query.filter(MappingConflict.reason == reason)
            if search:
                like = f"%{search}%"
                query = query.filter(
                    (MappingConflict.source_code.ilike(like))
                    | (MappingConflict.target_code.ilike(like))
                    | (MappingConflict.source_description.ilike(like))
                )

            query = query.order_by(MappingConflict.created_at.desc())
            total = query.count()
            items = query.offset((page - 1) * per_page).limit(per_page).all()

            return {
                "items": [c.to_dict() for c in items],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page,
            }
        finally:
            session.close()

    # ── stats ────────────────────────────────────────────────────────────

    @staticmethod
    def get_stats() -> dict:
        from sqlalchemy import func

        session = ConflictService._session()
        try:
            total = session.query(func.count(MappingConflict.id)).scalar() or 0
            open_count = session.query(func.count(MappingConflict.id)).filter(
                MappingConflict.status == "open"
            ).scalar() or 0
            resolved_count = session.query(func.count(MappingConflict.id)).filter(
                MappingConflict.status == "resolved"
            ).scalar() or 0
            ignored_count = session.query(func.count(MappingConflict.id)).filter(
                MappingConflict.status == "ignored"
            ).scalar() or 0

            by_source = session.query(
                MappingConflict.source_system,
                MappingConflict.target_system,
                func.count(MappingConflict.id),
            ).group_by(
                MappingConflict.source_system,
                MappingConflict.target_system,
            ).all()

            by_reason = session.query(
                MappingConflict.reason,
                func.count(MappingConflict.id),
            ).group_by(MappingConflict.reason).all()

            return {
                "total": total,
                "open": open_count,
                "resolved": resolved_count,
                "ignored": ignored_count,
                "by_mapping": [{"source_system": s, "target_system": t, "count": c} for s, t, c in by_source],
                "by_reason": [{"reason": r, "count": c} for r, c in by_reason],
            }
        finally:
            session.close()

    # ── get single ───────────────────────────────────────────────────────

    @staticmethod
    def get_conflict(conflict_id: int) -> dict | None:
        session = ConflictService._session()
        try:
            conflict = session.query(MappingConflict).get(conflict_id)
            return conflict.to_dict() if conflict else None
        finally:
            session.close()

    # ── update ───────────────────────────────────────────────────────────

    @staticmethod
    def update_conflict(conflict_id: int, action: str, resolution: str = "", resolved_code: str = "") -> dict | None:
        """Apply an action (resolve / ignore / reopen) to a single conflict.

        Returns the updated dict or ``None`` if not found.
        Raises ``ValueError`` for invalid actions.
        """
        if action not in ("resolve", "ignore", "reopen"):
            raise ValueError("Invalid action. Use: resolve, ignore, or reopen")

        session = ConflictService._session()
        try:
            conflict = session.query(MappingConflict).get(conflict_id)
            if not conflict:
                return None

            now = datetime.utcnow()
            if action == "resolve":
                conflict.status = "resolved"
                conflict.resolution = resolution
                conflict.resolved_code = resolved_code
                conflict.resolved_at = now
            elif action == "ignore":
                conflict.status = "ignored"
                conflict.resolution = resolution or "Manually ignored"
                conflict.resolved_at = now
            elif action == "reopen":
                conflict.status = "open"
                conflict.resolution = None
                conflict.resolved_code = None
                conflict.resolved_at = None

            session.commit()
            return conflict.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── bulk update ──────────────────────────────────────────────────────

    @staticmethod
    def bulk_update(ids: list[int], action: str, resolution: str = "", resolved_code: str = "") -> int:
        """Bulk resolve / ignore / reopen conflicts. Returns count updated.

        Raises ``ValueError`` for invalid action or empty IDs.
        """
        if not ids:
            raise ValueError("No conflict IDs provided")
        if action not in ("resolve", "ignore", "reopen"):
            raise ValueError("Invalid action. Use: resolve, ignore, or reopen")

        session = ConflictService._session()
        try:
            now = datetime.utcnow()
            conflicts = session.query(MappingConflict).filter(MappingConflict.id.in_(ids)).all()

            updated = 0
            for conflict in conflicts:
                if action == "resolve":
                    conflict.status = "resolved"
                    conflict.resolution = resolution or "Bulk resolved"
                    conflict.resolved_code = resolved_code
                    conflict.resolved_at = now
                elif action == "ignore":
                    conflict.status = "ignored"
                    conflict.resolution = resolution or "Bulk ignored"
                    conflict.resolved_at = now
                elif action == "reopen":
                    conflict.status = "open"
                    conflict.resolution = None
                    conflict.resolved_code = None
                    conflict.resolved_at = None
                updated += 1

            session.commit()
            return updated
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
