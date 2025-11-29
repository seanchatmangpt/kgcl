"""Tests for YAWL resource management.

Verifies resource types (roles, participants, positions, capabilities)
and resource allocation patterns.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.resources.y_resource import (
    ResourceStatus,
    YCapability,
    YOrgGroup,
    YParticipant,
    YPosition,
    YResourceManager,
    YRole,
)


class TestYRole:
    """Tests for YRole creation and membership."""

    def test_create_role(self) -> None:
        """Create role with name."""
        role = YRole(id="role-admin", name="Administrator")

        assert role.id == "role-admin"
        assert role.name == "Administrator"
        assert len(role.participants) == 0

    def test_role_add_participant(self) -> None:
        """Add participant to role."""
        role = YRole(id="role-admin", name="Administrator")

        role.add_participant("user-001")
        role.add_participant("user-002")

        assert "user-001" in role.participants
        assert "user-002" in role.participants
        assert len(role.participants) == 2

    def test_role_remove_participant(self) -> None:
        """Remove participant from role."""
        role = YRole(id="role-admin", name="Administrator")
        role.add_participant("user-001")

        role.remove_participant("user-001")

        assert "user-001" not in role.participants

    def test_role_has_participant(self) -> None:
        """Check role membership."""
        role = YRole(id="role-admin", name="Administrator")
        role.add_participant("user-001")

        assert role.has_participant("user-001")
        assert not role.has_participant("user-999")


class TestYParticipant:
    """Tests for YParticipant (user) management."""

    def test_create_participant(self) -> None:
        """Create participant with basic info."""
        participant = YParticipant(id="user-001", user_id="jsmith", first_name="John", last_name="Smith")

        assert participant.id == "user-001"
        assert participant.user_id == "jsmith"
        assert participant.get_full_name() == "John Smith"

    def test_participant_roles(self) -> None:
        """Participant can have multiple roles."""
        participant = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", roles={"role-admin", "role-manager"}
        )

        assert "role-admin" in participant.roles
        assert "role-manager" in participant.roles

    def test_participant_positions(self) -> None:
        """Participant can have position."""
        participant = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", positions={"pos-director"}
        )

        assert "pos-director" in participant.positions

    def test_participant_capabilities(self) -> None:
        """Participant can have capabilities."""
        participant = YParticipant(
            id="user-001",
            user_id="jsmith",
            first_name="John",
            last_name="Smith",
            capabilities={"cap-approve-large", "cap-sign-contracts"},
        )

        assert "cap-approve-large" in participant.capabilities

    def test_participant_is_available(self) -> None:
        """Check participant availability via status."""
        participant = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", status=ResourceStatus.AVAILABLE
        )

        assert participant.is_available()

        participant.set_status(ResourceStatus.BUSY)
        assert not participant.is_available()


class TestYPosition:
    """Tests for YPosition (organizational position)."""

    def test_create_position(self) -> None:
        """Create position."""
        position = YPosition(id="pos-director", name="Director", org_group_id="org-finance")

        assert position.id == "pos-director"
        assert position.name == "Director"
        assert position.org_group_id == "org-finance"

    def test_position_reports_to(self) -> None:
        """Position can report to another position."""
        director = YPosition(id="pos-director", name="Director")
        manager = YPosition(id="pos-manager", name="Manager", reports_to_id="pos-director")

        assert manager.reports_to_id == "pos-director"


class TestYCapability:
    """Tests for YCapability (skill/permission)."""

    def test_create_capability(self) -> None:
        """Create capability."""
        capability = YCapability(
            id="cap-approve-large", name="Approve Large Orders", description="Can approve orders over $10,000"
        )

        assert capability.id == "cap-approve-large"
        assert capability.name == "Approve Large Orders"


class TestYOrgGroup:
    """Tests for YOrgGroup (organizational unit)."""

    def test_create_org_group(self) -> None:
        """Create org group."""
        org = YOrgGroup(id="org-finance", name="Finance Department")

        assert org.id == "org-finance"
        assert org.name == "Finance Department"

    def test_org_group_hierarchy(self) -> None:
        """Org groups can have parent."""
        parent_org = YOrgGroup(id="org-company", name="Company")
        child_org = YOrgGroup(id="org-finance", name="Finance", belongs_to_id="org-company")

        assert child_org.belongs_to_id == "org-company"


class TestYResourceManager:
    """Tests for YResourceManager operations."""

    def test_create_resource_manager(self) -> None:
        """Create empty resource manager."""
        rm = YResourceManager()

        assert len(rm.roles) == 0
        assert len(rm.participants) == 0
        assert len(rm.positions) == 0

    def test_add_role(self) -> None:
        """Add role to manager."""
        rm = YResourceManager()
        role = YRole(id="role-admin", name="Administrator")

        rm.add_role(role)

        assert "role-admin" in rm.roles
        assert rm.get_role("role-admin") == role

    def test_add_participant(self) -> None:
        """Add participant to manager."""
        rm = YResourceManager()
        participant = YParticipant(id="user-001", user_id="jsmith", first_name="John", last_name="Smith")

        rm.add_participant(participant)

        assert "user-001" in rm.participants
        assert rm.get_participant("user-001") == participant

    def test_find_participants_by_role(self) -> None:
        """Find participants by role."""
        rm = YResourceManager()

        role = YRole(id="role-admin", name="Administrator")
        rm.add_role(role)

        p1 = YParticipant(id="user-001", user_id="jsmith", first_name="John", last_name="Smith", roles={"role-admin"})
        p2 = YParticipant(id="user-002", user_id="mjones", first_name="Mary", last_name="Jones", roles={"role-admin"})
        p3 = YParticipant(id="user-003", user_id="bwilson", first_name="Bob", last_name="Wilson", roles={"role-clerk"})

        rm.add_participant(p1)
        rm.add_participant(p2)
        rm.add_participant(p3)

        admins = rm.find_participants(role_ids={"role-admin"})

        assert len(admins) == 2
        assert any(p.id == "user-001" for p in admins)
        assert any(p.id == "user-002" for p in admins)
        assert not any(p.id == "user-003" for p in admins)

    def test_find_participants_by_capability(self) -> None:
        """Find participants by capability."""
        rm = YResourceManager()

        cap = YCapability(id="cap-approve", name="Approve Orders")
        rm.add_capability(cap)

        p1 = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", capabilities={"cap-approve"}
        )
        p2 = YParticipant(id="user-002", user_id="mjones", first_name="Mary", last_name="Jones", capabilities=set())

        rm.add_participant(p1)
        rm.add_participant(p2)

        approvers = rm.find_participants(capability_ids={"cap-approve"})

        assert len(approvers) == 1
        assert approvers[0].id == "user-001"

    def test_find_participants_by_position(self) -> None:
        """Find participants by position."""
        rm = YResourceManager()

        pos = YPosition(id="pos-manager", name="Manager")
        rm.add_position(pos)

        p1 = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", positions={"pos-manager"}
        )

        rm.add_participant(p1)

        managers = rm.find_participants(position_ids={"pos-manager"})

        assert len(managers) == 1
        assert managers[0].id == "user-001"

    def test_find_available_participants(self) -> None:
        """Find only available participants."""
        rm = YResourceManager()

        p1 = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", status=ResourceStatus.AVAILABLE
        )
        p2 = YParticipant(
            id="user-002", user_id="mjones", first_name="Mary", last_name="Jones", status=ResourceStatus.BUSY
        )

        rm.add_participant(p1)
        rm.add_participant(p2)

        available = rm.find_participants(available_only=True)

        assert len(available) == 1
        assert available[0].id == "user-001"


class TestResourceAllocationPatterns:
    """Tests for resource allocation patterns (offer, allocate, start)."""

    def test_offer_to_role(self) -> None:
        """Offer work item to all users in a role."""
        rm = YResourceManager()

        role = YRole(id="role-clerk", name="Clerk")
        rm.add_role(role)

        p1 = YParticipant(
            id="user-001",
            user_id="jsmith",
            first_name="John",
            last_name="Smith",
            roles={"role-clerk"},
            status=ResourceStatus.AVAILABLE,
        )
        p2 = YParticipant(
            id="user-002",
            user_id="mjones",
            first_name="Mary",
            last_name="Jones",
            roles={"role-clerk"},
            status=ResourceStatus.AVAILABLE,
        )

        rm.add_participant(p1)
        rm.add_participant(p2)

        # Get participants to offer work to
        offer_to = rm.find_participants(role_ids={"role-clerk"}, available_only=True)

        assert len(offer_to) == 2

    def test_direct_allocation(self) -> None:
        """Allocate work item directly to specific user."""
        rm = YResourceManager()

        participant = YParticipant(
            id="user-001", user_id="jsmith", first_name="John", last_name="Smith", status=ResourceStatus.AVAILABLE
        )
        rm.add_participant(participant)

        # Direct allocation - get specific participant
        allocated = rm.get_participant("user-001")

        assert allocated is not None
        assert allocated.id == "user-001"

    def test_capability_based_allocation(self) -> None:
        """Allocate based on capability requirements."""
        rm = YResourceManager()

        cap = YCapability(id="cap-sign", name="Sign Documents")
        rm.add_capability(cap)

        p1 = YParticipant(
            id="user-001",
            user_id="jsmith",
            first_name="John",
            last_name="Smith",
            capabilities={"cap-sign"},
            status=ResourceStatus.AVAILABLE,
        )
        p2 = YParticipant(
            id="user-002",
            user_id="mjones",
            first_name="Mary",
            last_name="Jones",
            capabilities=set(),
            status=ResourceStatus.AVAILABLE,
        )

        rm.add_participant(p1)
        rm.add_participant(p2)

        # Find users who can sign
        signers = rm.find_participants(capability_ids={"cap-sign"}, available_only=True)

        assert len(signers) == 1
        assert signers[0].id == "user-001"
