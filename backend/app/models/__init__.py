"""Import all models to register complete Alembic metadata."""
from app.models.domain import AuditEvent, Hackathon, IdempotencyRecord, Membership, OutboxEvent, Team, User
from app.models.auth import AccountCredential, AuthSession, AuthThrottleBucket
from app.models.admission import JoinRequest
from app.models.invitations import Invitation

__all__ = ["User", "Hackathon", "Team", "Membership", "IdempotencyRecord", "AuditEvent", "OutboxEvent"]
__all__ += ['AccountCredential', 'AuthSession', 'AuthThrottleBucket']
__all__ += ['JoinRequest']
__all__ += ['Invitation']
