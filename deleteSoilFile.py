# -*- coding: utf-8 -*-
"""
Deletes an individual profile from .SOL file
If, after the removal, no profile is left, the file is deleted

Use (example):
    from deleteSoilFile import delete_soil_profile
    delete_soil_profile("MEUARQ.SOL", "IBSB910017")
"""

from pathlib import Path


def _list_profiles(lines: list[str]) -> list[tuple[int, str]]:
    """Returns [(first_line, id), ... ] Ignoring header SOILS:."""
    out: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        if ln.startswith("*") and not ln.upper().startswith("*SOILS:"):
            out.append((i, ln[1:12].strip()))
    return out


def delete_soil_profile(file_path: str | Path, profile_id: str) -> None:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File «{file_path}» was not found.")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    profiles = _list_profiles(lines)

    # seeks the profile block
    blk_start = blk_end = None
    for idx, (line_no, code) in enumerate(profiles):
        if code == profile_id:
            blk_start = line_no
            blk_end = profiles[idx + 1][0] if idx + 1 < len(profiles) else len(lines)
            break
    if blk_start is None:
        raise ValueError(f"The profile «{profile_id}» wasn't found in the path: {file_path}.")

    # removes the block
    new_lines = lines[:blk_start] + lines[blk_end:]

    # writes or deletes profile
    if not _list_profiles(new_lines):              # no profile left
        file_path.unlink()
    else:
        file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
