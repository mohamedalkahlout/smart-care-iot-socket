"""
Caregiver Roles and Invitations Service (P2.2).
Provides role-based access control:
- owner: Full control, can invite caregivers, manage device.
- caregiver: Monitors status, receives alerts, safe remote control (under safety guard limits).
- viewer: Read-only access to status and telemetry.
"""
import time
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class UserRole:
    user_id: str
    role: str  # "owner", "caregiver", "viewer"
    granted_by: str
    granted_at: float


@dataclass
class InviteToken:
    token: str
    role: str
    created_at: float
    expires_at: float
    is_used: bool = False
    used_by: Optional[str] = None


@dataclass
class AuditEntry:
    timestamp: float
    user_id: str
    action: str
    details: str


class RolesService:
    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.users: Dict[str, UserRole] = {
            owner_id: UserRole(user_id=owner_id, role="owner", granted_by="system", granted_at=time.time())
        }
        self.invites: Dict[str, InviteToken] = {}
        self.audit_log: List[AuditEntry] = []
        self._log(owner_id, "INIT", "Device initialized with owner")

    def _log(self, user_id: str, action: str, details: str):
        self.audit_log.append(AuditEntry(timestamp=time.time(), user_id=user_id, action=action, details=details))

    def create_invite(self, issuer_id: str, role: str, expiry_seconds: int = 86400) -> Optional[str]:
        # Only owner can generate invites
        if self.get_role(issuer_id) != "owner":
            return None
        if role not in ["caregiver", "viewer"]:
            return None

        token = "inv_" + secrets.token_urlsafe(16)
        now = time.time()
        self.invites[token] = InviteToken(
            token=token,
            role=role,
            created_at=now,
            expires_at=now + expiry_seconds,
            is_used=False
        )
        self._log(issuer_id, "CREATE_INVITE", f"Generated {role} invite token valid for {expiry_seconds}s")
        return token

    def accept_invite(self, token: str, user_id: str) -> bool:
        now = time.time()
        if token not in self.invites:
            return False
        inv = self.invites[token]
        if inv.is_used or now > inv.expires_at:
            return False

        inv.is_used = True
        inv.used_by = user_id
        self.users[user_id] = UserRole(
            user_id=user_id,
            role=inv.role,
            granted_by=self.owner_id,
            granted_at=now
        )
        self._log(user_id, "ACCEPT_INVITE", f"Accepted invitation for role: {inv.role}")
        return True

    def revoke_user(self, issuer_id: str, target_user_id: str) -> bool:
        if self.get_role(issuer_id) != "owner" or target_user_id == self.owner_id:
            return False
        if target_user_id in self.users:
            del self.users[target_user_id]
            self._log(issuer_id, "REVOKE_USER", f"Revoked permissions for {target_user_id}")
            return True
        return False

    def get_role(self, user_id: str) -> str:
        if user_id in self.users:
            return self.users[user_id].role
        return "none"

    def can_actuate(self, user_id: str) -> bool:
        role = self.get_role(user_id)
        return role in ["owner", "caregiver"]

    def can_modify_safety_limits(self, user_id: str) -> bool:
        # Caregivers CANNOT change upper safety thresholds - only owner
        return self.get_role(user_id) == "owner"
