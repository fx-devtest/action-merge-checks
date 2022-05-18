import logging
import re
import subprocess
from typing import Sequence

# https://github.com/moneymeets/moneymeets-docs/blob/master/_posts/2020-03-18-commit-message-branch-name-guidelines.md
ALLOWED_COMMIT_MESSAGE_TYPES = ("chore", "ci", "docs", "feat", "fix", "perf", "refactor", "style", "test")


def _run_process(command: str) -> str:
    return subprocess.run(
        command,
        check=True,
        shell=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def fetch_head_only(base_ref: str):
    logging.info(f"Checking out {base_ref}...")
    _run_process(f"git fetch --depth=1 origin {base_ref}")


def fetch_full_history():
    logging.info("Getting commit list...")
    _run_process("git fetch --unshallow")


def get_base_revision(base_ref: str) -> str:
    return _run_process(f"git rev-parse origin/{base_ref}")


def get_subject(head_hash: str, base_hash: str) -> Sequence[str]:
    return tuple(_run_process(f"git log --pretty='format:%s' {base_hash}..{head_hash}").splitlines())


def get_subject_markers(subjects: Sequence[str]) -> Sequence[str]:
    return tuple(line.split(maxsplit=1)[0] for line in subjects)


def has_merge_commits(head_hash: str, base_hash: str) -> bool:
    parents = _run_process(f"git log --pretty=%p {base_hash}..{head_hash}").splitlines()
    return any(len(line.split(maxsplit=1)) > 1 for line in parents)


def has_wrong_commit_message(subject_markers: Sequence[str]) -> Sequence[str]:
    return tuple(
        marker
        for marker in subject_markers
        if re.match(rf"^({'|'.join(ALLOWED_COMMIT_MESSAGE_TYPES)})\([a-z\d-]+\): .+", marker) is None
    )


def get_commit_checks_result(head_hash: str, base_ref: str) -> tuple[bool, str]:
    fetch_head_only(base_ref)
    base_hash = get_base_revision(base_ref)

    if head_hash == base_hash:
        logging.warning(f"HEAD identical with {base_ref}, no commits to check")
        return True, "No commits to check"

    fetch_full_history()
    subjects = get_subject(head_hash, base_hash)
    subject_markers = get_subject_markers(subjects)

    fixups, squashes = (
        sum(1 for subject_marker in subject_markers if subject_marker == marker) for marker in ("fixup!", "squash!")
    )

    if fixups or squashes:
        return False, f"{fixups} fixup and {squashes} squash commits found"
    else:
        logging.info("No fixups or squashes found, check passed!")

    if has_merge_commits(head_hash, base_hash):
        return False, "Contains merge commits"
    else:
        logging.info("Branch does not contain merge commits, check passed!")

    if incorrect_commit_messages := has_wrong_commit_message(subjects):
        logging.info(
            f"Found invalid commit message(s), allowed types: {ALLOWED_COMMIT_MESSAGE_TYPES}\n"
            f"{chr(10).join(incorrect_commit_messages)}",
        )
        return False, "Invalid commit message format found"
    else:
        logging.info("Commit messages are correct, check passed!")

    return True, "All checks passed"