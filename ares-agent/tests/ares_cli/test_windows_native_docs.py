from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\ares\\ares-agent\\venv\\Scripts" in doc
    assert "Get-Command ares        # should print C:\\Users\\<you>\\AppData\\Local\\ares\\ares-agent\\venv\\Scripts\\ares.exe" in doc
    assert '$aresBin = "$InstallDir\\venv\\Scripts"' in install
