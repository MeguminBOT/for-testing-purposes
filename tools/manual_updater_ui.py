#!/usr/bin/env python3
"""Manual Qt updater harness for local experimentation.

Run this script to display the real Qt updater dialog while all network
and filesystem calls are mocked. This lets you visually verify the UI
without touching your actual installation or calling GitHub.

Usage:
    python tools/manual_updater_ui.py
"""

from __future__ import annotations

import io
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import utils.update_installer as update_installer  # type: ignore[import]  # noqa: E402

Updater = update_installer.Updater
QtDialog = update_installer.QtUpdateDialog
QApplication = update_installer.QApplication


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.headers = {"content-length": str(len(payload))}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        for idx in range(0, len(self._payload), chunk_size):
            yield self._payload[idx : idx + chunk_size]


def _build_fake_release_zip() -> bytes:
    buffer = io.BytesIO()
    base = "fake-release/"

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(base + "assets/dummy.txt", "asset data")
        archive.writestr(base + "ImageMagick/readme.txt", "dll placeholder")
        archive.writestr(base + "src/module.py", "print('hi')\n")
        archive.writestr(base + "latestVersion.txt", "9.9.9")
        archive.writestr(base + "LICENSE", "license text")
        archive.writestr(base + "README.md", "readme text")

    return buffer.getvalue()


def run_manual_update():
    if not update_installer.QT_AVAILABLE:
        raise RuntimeError("PySide6/PyQt is required to run the manual UI harness")

    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication([])
        created_app = True

    dialog = QtDialog()
    dialog.show()

    release_bytes = _build_fake_release_zip()
    fake_response = _FakeResponse(release_bytes)

    temp_dir = tempfile.TemporaryDirectory()
    project_root = Path(temp_dir.name) / "project"
    project_root.mkdir()

    for folder in ("assets", "ImageMagick", "src"):
        (project_root / folder).mkdir()

    for filename in ("latestVersion.txt", "LICENSE", "README.md"):
        (project_root / filename).write_text("original", encoding="utf-8")

    try:
        with (
            mock.patch("utils.update_installer.requests.get", return_value=fake_response),
            mock.patch.object(Updater, "find_project_root", return_value=str(project_root)),
            mock.patch.object(Updater, "create_updater_backup", return_value=None),
            mock.patch.object(Updater, "wait_for_main_app_closure", return_value=True),
            mock.patch.object(
                Updater,
                "get_latest_release_info",
                return_value={"zipball_url": "https://example.com/fake.zip", "tag_name": "v9.9.9"},
            ),
        ):
            updater = Updater(ui=dialog, exe_mode=False)
            updater.update_source()

        print("Manual updater finished. Check the dialog for logs/progress and close it when done.")
        app.exec()
    finally:
        temp_dir.cleanup()
        dialog.close()
        if created_app:
            app.quit()


if __name__ == "__main__":
    run_manual_update()
