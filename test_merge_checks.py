import subprocess
from unittest import TestCase
from unittest.mock import MagicMock, patch

import merge_checks


@patch.object(merge_checks, "has_merge_commits")
@patch.object(merge_checks, "get_subject_markers")
@patch.object(merge_checks, "fetch_full_history")
@patch.object(merge_checks, "get_base_revision")
@patch.object(merge_checks, "fetch_head_only")
class MergeCheckTest(TestCase):
    def test_happy_path(
        self,
        mock_fetch_head_only,
        mock_get_base_revision,
        mock_fetch_full_history,
        mock_get_subject_markers,
        mock_has_merge_commits,
    ):
        head_hash = "987xyz"
        base_ref = "baseref"
        base_hash = "123abc"

        mock_get_base_revision.return_value = base_hash
        mock_get_subject_markers.return_value = ("feat(component):",)
        mock_has_merge_commits.return_value = False

        self.assertEqual(0, merge_checks.main(head_hash=head_hash, base_ref=base_ref))
        mock_fetch_head_only.assert_called_once_with(base_ref)
        mock_get_base_revision.assert_called_once_with(base_ref)
        mock_fetch_full_history.assert_called_once()
        mock_get_subject_markers.assert_called_once_with(head_hash, base_hash)
        mock_has_merge_commits.assert_called_once_with(head_hash, base_hash)

    def test_early_exit_no_commits(
        self,
        mock_fetch_head_only,
        mock_get_base_revision,
        mock_fetch_full_history,
        mock_get_subject_markers,
        mock_has_merge_commits,
    ):
        base_ref = "baseref"
        base_hash = "123abc"

        mock_get_base_revision.return_value = base_hash
        mock_has_merge_commits.return_value = False

        self.assertEqual(0, merge_checks.main(head_hash=base_hash, base_ref=base_ref))
        mock_fetch_head_only.assert_called_once_with(base_ref)
        mock_get_base_revision.assert_called_once_with(base_ref)
        mock_fetch_full_history.assert_not_called()
        mock_get_subject_markers.assert_not_called()
        mock_has_merge_commits.assert_not_called()

    def test_fixup_found(
        self,
        mock_fetch_head_only,
        mock_get_base_revision,
        mock_fetch_full_history,
        mock_get_subject_markers,
        mock_has_merge_commits,
    ):
        head_hash = "987xyz"
        base_ref = "baseref"
        base_hash = "123abc"
        mock_get_base_revision.return_value = base_hash
        mock_get_subject_markers.return_value = ("feat(component):", "fixup!")
        mock_has_merge_commits.return_value = False

        self.assertEqual(1, merge_checks.main(head_hash=head_hash, base_ref=base_ref))
        mock_fetch_head_only.assert_called_once_with(base_ref)
        mock_get_base_revision.assert_called_once_with(base_ref)
        mock_fetch_full_history.assert_called_once()
        mock_get_subject_markers.assert_called_once_with(head_hash, base_hash)
        mock_has_merge_commits.assert_not_called()

    def test_squash_found(
        self,
        mock_fetch_head_only,
        mock_get_base_revision,
        mock_fetch_full_history,
        mock_get_subject_markers,
        mock_has_merge_commits,
    ):
        head_hash = "987xyz"
        base_ref = "baseref"
        base_hash = "123abc"

        mock_get_base_revision.return_value = base_hash
        mock_get_subject_markers.return_value = ("feat(component):", "squash!")
        mock_has_merge_commits.return_value = False

        self.assertEqual(1, merge_checks.main(head_hash=head_hash, base_ref=base_ref))
        mock_fetch_head_only.assert_called_once_with(base_ref)
        mock_get_base_revision.assert_called_once_with(base_ref)
        mock_fetch_full_history.assert_called_once()
        mock_get_subject_markers.assert_called_once_with(head_hash, base_hash)
        mock_has_merge_commits.assert_not_called()

    def test_merge_commit_found(
        self,
        mock_fetch_head_only,
        mock_get_base_revision,
        mock_fetch_full_history,
        mock_get_subject_markers,
        mock_has_merge_commits,
    ):
        head_hash = "987xyz"
        base_ref = "baseref"
        base_hash = "123abc"

        mock_get_base_revision.return_value = base_hash
        mock_get_subject_markers.return_value = ("feat(component):",)
        mock_has_merge_commits.return_value = True

        self.assertEqual(1, merge_checks.main(head_hash=head_hash, base_ref=base_ref))
        mock_fetch_head_only.assert_called_once_with(base_ref)
        mock_get_base_revision.assert_called_once_with(base_ref)
        mock_fetch_full_history.assert_called_once()
        mock_get_subject_markers.assert_called_once_with(head_hash, base_hash)
        mock_has_merge_commits.assert_called_once_with(head_hash, base_hash)


class ExternalCallTest(TestCase):
    @staticmethod
    def _mock_run_process(return_value: str):
        return patch.object(merge_checks, "_run_process", return_value=return_value)

    @patch.object(subprocess, "run", return_value=MagicMock(stdout="test-output       "))
    def test_run_process_call(self, mock_run):
        self.assertEqual(merge_checks._run_process("command"), "test-output")
        mock_run.assert_called_once_with(
            "command",
            check=True,
            shell=True,
            capture_output=True,
            text=True,
        )

    def test_has_merge_commits(self):
        with self._mock_run_process("parent_1") as mock_run_process:
            self.assertFalse(merge_checks.has_merge_commits("head", "base"))
            mock_run_process.assert_called_once()

        with self._mock_run_process("parent_1 parent_2") as mock_run_process:
            self.assertTrue(merge_checks.has_merge_commits("head", "base"))
            mock_run_process.assert_called_once()

    def test_get_subject_markers(self):
        with self._mock_run_process(
            "\n".join(("feat(test): we test this", "fixup! feat(test): we test this")),
        ) as mock_run_process:
            self.assertEqual(merge_checks.get_subject_markers("head", "base"), ("feat(test):", "fixup!"))
            mock_run_process.assert_called_once()

    def test_fetch_full_history(self):
        with self._mock_run_process("") as mock_run_process:
            merge_checks.fetch_full_history()
            mock_run_process.assert_called_once()

    def test_get_base_revision(self):
        with self._mock_run_process("base_ref") as mock_run_process:
            self.assertEqual(merge_checks.get_base_revision("base"), "base_ref")
            mock_run_process.assert_called_once()

    def test_fetch_head_only(self):
        with self._mock_run_process("") as mock_run_process:
            merge_checks.fetch_head_only("base")
            mock_run_process.assert_called_once()
