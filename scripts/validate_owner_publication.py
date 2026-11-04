#!/usr/bin/env python3
"""Проверить владельца публикации и отказ до записи при неверном CI-источнике."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("owner_publication", ROOT / "scripts/publish_owner_release.py")
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)
REAL_API = pub.api


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="nagramix-publisher-check-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "product/features").mkdir(parents=True)
        (self.root / "product/releases").mkdir()
        (self.root / "product/features/registry.json").write_text('{"release":"0.8.5"}')
        (self.root / "product/releases/0.8.5.md").write_text("Утверждённая аннотация")
        self.archive = self.root / "artifact.zip"
        self.names = ["NagramiX-0.8.5-unsigned.ipa", "BUILD-PROVENANCE.txt", "SHA256SUMS"]
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr(self.names[0], b"package-boundary")
            archive.writestr(self.names[1], f"Workflow run: https://github.com/{pub.REPO}/actions/runs/10\n")
            archive.writestr(self.names[2], "checksums-boundary")
        self.login = pub.OWNER
        self.source = "a" * 40
        self.run = {"id": 10, "workflow_id": 1, "head_repository": {"full_name": pub.REPO},
                    "head_branch": "main", "event": "workflow_dispatch", "status": "completed",
                    "actor": {"login": pub.OWNER}, "triggering_actor": {"login": pub.OWNER},
                    "head_sha": self.source, "run_number": 163}
        self.jobs = [{"name": "build", "conclusion": "success", "steps": [
            {"name": pub.COLD_GATE, "conclusion": "success"}]}]
        self.artifact = {"name": "NagramiX-0.8.5-unsigned-arm64", "expired": False,
                         "digest": pub.digest(self.archive)}
        self.release, self.ref = None, None
        self.tag_lookup_missing = False
        self.release_pages = {}
        self.writes, self.uploads = [], []
        for name, replacement in (("ROOT", self.root), ("api", self.api), ("upload", self.upload)):
            patch = mock.patch.object(pub, name, replacement)
            patch.start()
            self.addCleanup(patch.stop)
        self.package = mock.patch.object(pub, "validate_package").start()
        self.addCleanup(mock.patch.stopall)

    def api(self, path, method="GET", data=None, optional=False):
        if method != "GET":
            self.writes.append((method, path, copy.deepcopy(data)))
        if path == "user":
            return {"login": self.login}
        if path.endswith("/actions/runs/10"):
            return copy.deepcopy(self.run)
        if path.endswith("/actions/workflows/build-unsigned-ipa.yml"):
            return {"id": 1}
        if path.endswith("/jobs?per_page=100"):
            return {"jobs": copy.deepcopy(self.jobs)}
        if path.endswith("/artifacts?per_page=100"):
            return {"artifacts": [copy.deepcopy(self.artifact)]}
        if "/git/ref/tags/" in path:
            return copy.deepcopy(self.ref)
        if "/releases/tags/" in path:
            return None if self.tag_lookup_missing else copy.deepcopy(self.release)
        if path.startswith(pub.API + "/releases?per_page=100&page="):
            page = int(path.rsplit("=", 1)[1])
            return copy.deepcopy(self.release_pages.get(page, []))
        if path == pub.API + "/releases" and method == "POST":
            self.release = {**data, "id": 99, "author": {"login": pub.OWNER}, "assets": [],
                            "html_url": "https://github.com/" + pub.REPO + "/releases/tag/v0.8.5"}
            return copy.deepcopy(self.release)
        if path == pub.API + "/releases/99":
            if method == "PATCH":
                self.release.update(data)
            return copy.deepcopy(self.release)
        raise AssertionError((method, path))

    def upload(self, tag, paths):
        self.package.assert_called_once()
        self.uploads.append(tag)
        self.release["assets"] = [{"name": p.name, "size": p.stat().st_size,
                                   "digest": pub.digest(p), "uploader": {"login": pub.OWNER}} for p in paths]

    def reject(self, finalize_uploaded=False):
        with self.assertRaises(RuntimeError):
            pub.publish(10, self.archive, finalize_uploaded=finalize_uploaded)
        self.assertEqual(self.writes, [])
        self.assertEqual(self.uploads, [])

    def test_success_uses_owner_and_exact_title(self):
        self.assertTrue(pub.publish(10, self.archive).endswith("v0.8.5"))
        self.assertEqual([x[0] for x in self.writes], ["POST", "PATCH"])
        self.assertEqual(self.release["name"], "Релиз 0.8.5")
        self.assertFalse(self.release["draft"])
        self.assertFalse(self.release["prerelease"])

    def test_prerelease_is_explicit(self):
        pub.publish(10, self.archive, prerelease=True)
        self.assertTrue(self.release["prerelease"])
        self.assertEqual(self.release["make_latest"], "false")

    def test_empty_owner_draft_is_reused(self):
        self.release = {"id": 99, "draft": True, "author": {"login": pub.OWNER},
                        "target_commitish": self.source, "assets": [], "html_url": "verified"}
        self.ref = {"object": {"type": "commit", "sha": self.source}}
        self.assertEqual(pub.publish(10, self.archive), "verified")
        self.assertEqual([x[0] for x in self.writes], ["PATCH"])

    def test_nonempty_owner_draft_is_not_reused(self):
        self.release = {"draft": True, "author": {"login": pub.OWNER},
                        "target_commitish": self.source, "assets": [{"name": "partial-upload"}]}
        self.reject()

    def uploaded_owner_draft(self):
        with zipfile.ZipFile(self.archive) as archive:
            assets = [{"name": name, "size": len(archive.read(name)),
                       "digest": "sha256:" + hashlib.sha256(archive.read(name)).hexdigest(),
                       "uploader": {"login": pub.OWNER}} for name in self.names]
        return {"id": 99, "draft": True, "author": {"login": pub.OWNER},
                "target_commitish": self.source, "assets": assets, "html_url": "verified"}

    def test_finalize_complete_owner_draft_without_uploading(self):
        self.release = self.uploaded_owner_draft()
        self.assertEqual(pub.publish(10, self.archive, finalize_uploaded=True), "verified")
        self.assertEqual(self.uploads, [])
        self.assertEqual([item[0] for item in self.writes], ["PATCH"])
        self.assertFalse(self.release["draft"])
        self.package.assert_called_once()

    def test_finalize_requires_existing_draft(self):
        self.reject(finalize_uploaded=True)

    def test_finalize_rejects_unverified_assets_before_writes(self):
        for change in ("empty", "partial", "extra", "digest", "size", "uploader"):
            with self.subTest(change=change):
                self.release = self.uploaded_owner_draft()
                assets = self.release["assets"]
                if change == "empty":
                    assets.clear()
                elif change == "partial":
                    assets.pop()
                elif change == "extra":
                    assets.append(copy.deepcopy(assets[0]))
                elif change == "digest":
                    assets[0]["digest"] = "sha256:" + "0" * 64
                elif change == "size":
                    assets[0]["size"] += 1
                elif change == "uploader":
                    assets[0]["uploader"]["login"] = "github-actions[bot]"
                self.reject(finalize_uploaded=True)

    def test_finalize_never_replaces_published_or_foreign_release(self):
        for change in ("published", "author", "source"):
            with self.subTest(change=change):
                self.release = self.uploaded_owner_draft()
                if change == "published":
                    self.release["draft"] = False
                elif change == "author":
                    self.release["author"]["login"] = "github-actions[bot]"
                else:
                    self.release["target_commitish"] = "b" * 40
                self.reject(finalize_uploaded=True)

    def test_finalize_preserves_existing_tag_source(self):
        self.release = self.uploaded_owner_draft()
        self.ref = {"object": {"type": "commit", "sha": "b" * 40}}
        self.reject(finalize_uploaded=True)

    def test_finalize_finds_unpublished_draft_after_tag_lookup_404(self):
        self.release = {**self.uploaded_owner_draft(), "tag_name": "v0.8.5"}
        self.tag_lookup_missing = True
        self.release_pages[1] = [{"tag_name": "v0.8.4", "draft": False}, self.release]
        self.assertEqual(pub.publish(10, self.archive, finalize_uploaded=True), "verified")
        self.assertEqual(self.uploads, [])
        self.assertEqual([item[0] for item in self.writes], ["PATCH"])

    def test_draft_lookup_checks_later_pages(self):
        self.release = {**self.uploaded_owner_draft(), "tag_name": "v0.8.5"}
        self.tag_lookup_missing = True
        self.release_pages[1] = [{"tag_name": "unrelated"}] * 100
        self.release_pages[2] = [self.release]
        self.assertEqual(pub.publish(10, self.archive, finalize_uploaded=True), "verified")
        self.assertEqual([item[0] for item in self.writes], ["PATCH"])

    def test_ambiguous_drafts_are_rejected_before_writes(self):
        self.release = {**self.uploaded_owner_draft(), "tag_name": "v0.8.5"}
        self.tag_lookup_missing = True
        self.release_pages[1] = [self.release, {**self.release, "id": 100}]
        self.reject(finalize_uploaded=True)

    def test_wrong_account(self):
        self.login = "github-actions[bot]"
        self.reject()
        self.package.assert_not_called()

    def test_foreign_run(self):
        self.run["head_repository"]["full_name"] = "other/repo"
        self.reject()

    def test_wrong_rerun_actor(self):
        self.run["triggering_actor"]["login"] = "codex"
        self.reject()

    def test_incomplete_run(self):
        self.run["status"] = "in_progress"
        self.reject()

    def test_failed_build(self):
        self.jobs[0]["conclusion"] = "failure"
        self.reject()

    def test_cached_build(self):
        self.jobs[0]["steps"][0]["conclusion"] = "skipped"
        self.reject()

    def test_expired_artifact(self):
        self.artifact["expired"] = True
        self.reject()

    def test_different_archive(self):
        self.artifact["digest"] = "sha256:" + "0" * 64
        self.reject()

    def test_unexpected_archive_member(self):
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("../outside", b"bad")
        self.artifact["digest"] = pub.digest(self.archive)
        self.reject()

    def test_package_failure(self):
        self.package.side_effect = RuntimeError("package invalid")
        self.reject()

    def test_published_release_is_never_replaced(self):
        self.release = {"draft": False}
        self.reject()

    def test_foreign_draft_is_never_used(self):
        self.release = {"draft": True, "author": {"login": "github-actions[bot]"}}
        self.reject()

    def test_other_tag_source_is_never_replaced(self):
        self.ref = {"object": {"type": "commit", "sha": "b" * 40}}
        self.reject()

    def test_upload_by_bot_is_not_published(self):
        original = pub.upload
        def bot_upload(tag, paths):
            original(tag, paths)
            self.release["assets"][0]["uploader"]["login"] = "github-actions[bot]"
        with mock.patch.object(pub, "upload", bot_upload), self.assertRaises(RuntimeError):
            pub.publish(10, self.archive)
        self.assertEqual([x[0] for x in self.writes], ["POST"])
        self.assertTrue(self.release["draft"])

    def test_server_digest_mismatch_is_not_published(self):
        original = pub.upload
        def damaged_upload(tag, paths):
            original(tag, paths)
            self.release["assets"][0]["digest"] = "sha256:" + "0" * 64
        with mock.patch.object(pub, "upload", damaged_upload), self.assertRaises(RuntimeError):
            pub.publish(10, self.archive)
        self.assertEqual([x[0] for x in self.writes], ["POST"])
        self.assertTrue(self.release["draft"])

    def test_missing_and_forbidden_are_different(self):
        for status in (404, 403):
            result = subprocess.CompletedProcess([], 1, "", f"gh: Error (HTTP {status})")
            with mock.patch.object(pub.subprocess, "run", return_value=result):
                if status == 404:
                    self.assertIsNone(REAL_API("missing", optional=True))
                else:
                    with self.assertRaises(RuntimeError):
                        REAL_API("forbidden", optional=True)


def check_workflow():
    text = (ROOT / ".github/workflows/build-unsigned-ipa.yml").read_text()
    assert "contents: write" not in text
    assert not any(value in text for value in ("gh release create", "gh release upload", "gh release edit"))
    assert text.count('test "$GITHUB_ACTOR" = "Mr-EFES"') == 2
    assert text.count('test "$GITHUB_TRIGGERING_ACTOR" = "Mr-EFES"') == 2
    assert "python3 scripts/validate_owner_publication.py" in text
    assert "scripts/publish_owner_release.py --source-run-id" in text


if __name__ == "__main__":
    check_workflow()
    unittest.main()
