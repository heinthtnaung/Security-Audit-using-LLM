"""The roster: the members an operator configured, and which of them a run may ask.

A Python object, not a file; the project has committed to no roster format.
`egress` fails closed: a hosted member without it does not run, because what
leaves the machine is not only an advisory but which advisories you ask about. A
skipped member is reported as skipped, never silently dropped.
"""

from dataclasses import dataclass

from council.answer import MemberIdentity

OLLAMA_PROVIDER = "ollama"

SKIPPED_WITHOUT_EGRESS = "hosted, and egress was not opted in for it"


@dataclass(frozen=True)
class Member:
    """One model reached through one provider, as the operator configured it."""

    name: str
    provider: str
    model: str
    family: str
    runs_local: bool
    egress: bool = False

    def __post_init__(self) -> None:
        """Refuse a member a record could not name or reconstruct."""
        missing = [
            field
            for field in ("name", "provider", "model", "family")
            if not getattr(self, field)
        ]
        if missing:
            raise ValueError(f"A council member needs {', '.join(missing)}")
        refuse_non_boolean(self.name, "runs_local", self.runs_local)
        refuse_non_boolean(self.name, "egress", self.egress)

    def may_run(self) -> bool:
        """Say whether this run may ask this member, which a hosted one must opt into."""
        return self.runs_local or self.egress

    def is_hosted(self) -> bool:
        """Say whether this is a hosted service's model: neither here nor on an Ollama server."""
        # An Ollama member on another machine is not hosted; it is on the opted-in server.
        return not self.runs_local and self.provider != OLLAMA_PROVIDER

    def identify(self, prompt_version: str) -> MemberIdentity:
        """Name this member on an answer, recording the prompt it was asked with."""
        return MemberIdentity(
            name=self.name,
            provider=self.provider,
            model=self.model,
            family=self.family,
            ran_local=self.runs_local,
            prompt_version=prompt_version,
        )


@dataclass(frozen=True)
class SkippedMember:
    """A member this run did not ask, and the reason the report has to carry."""

    member: Member
    reason: str


@dataclass(frozen=True)
class Roster:
    """The members an operator configured for one run, in the order they are asked."""

    members: tuple[Member, ...]

    def __post_init__(self) -> None:
        """Refuse a roster with nobody on it, or with two members a record cannot tell apart."""
        # An empty roster is a configuration error, not a council.
        if not self.members:
            raise ValueError("A council needs at least one member; an empty roster cannot assess")
        refuse_repeated_names(self.members)


def members_to_ask(roster: Roster) -> tuple[Member, ...]:
    """Give the members this run may ask, refusing a run that can ask nobody."""
    asking = tuple(member for member in roster.members if member.may_run())
    if asking:
        return asking
    raise ValueError(
        "Every member of this roster is hosted without egress, so the run can ask nobody"
    )


def members_skipped(roster: Roster) -> tuple[SkippedMember, ...]:
    """Name the members `egress` stopped, so the report can say they were not asked.

    Only those; `council.providers.unreachable_members` also names the ones with
    no client.
    """
    return tuple(
        SkippedMember(member=member, reason=SKIPPED_WITHOUT_EGRESS)
        for member in roster.members
        if not member.may_run()
    )


def is_single_assessor(roster: Roster) -> bool:
    """Say whether `egress` leaves one member alone to answer, which is not a council."""
    # Ranges over egress only; `CouncilRun.single_assessor` also counts members
    # with no client, and is the stricter answer a record should carry.
    return len(members_to_ask(roster)) == 1


def refuse_repeated_names(members: tuple[Member, ...]) -> None:
    """Refuse two members sharing a name, which no record could attribute apart."""
    names = sorted(member.name for member in members)
    repeated = sorted({name for name in names if names.count(name) > 1})
    if not repeated:
        return
    raise ValueError(f"{', '.join(repeated)} names more than one member of this roster")


def refuse_non_boolean(name: str, field: str, given: object) -> None:
    """Refuse a flag that is not a flag, which would make a refusal depend on truthiness."""
    if isinstance(given, bool):
        return
    raise TypeError(f"{name!r} must say {field} as true or false, not {type(given).__name__}")
