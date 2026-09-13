#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parent
sh = (root / "patch_superhound.py").read_text(encoding="utf-8")
ft = (root / "patch_ft2.py").read_text(encoding="utf-8")

bad = []
if "or 'actionEnable_superhound_mode' in s" in sh:
    bad.append("old broad SuperHound UI guard still present")
if "definition_marker='  <action name=\"actionEnable_superhound_mode\">\\n'" not in sh:
    bad.append("exact SuperHound QAction definition guard missing")

ui = (
    '    <addaction name="actionEnable_hound_mode"/>\n'
    '    <addaction name="actionUse_TX_frequency_jumps"/>\n'
    '  <action name="actionEnable_hound_mode">\n'
)
ui = ui.replace(
    '    <addaction name="actionEnable_hound_mode"/>\n'
    '    <addaction name="actionUse_TX_frequency_jumps"/>\n',
    '    <addaction name="actionEnable_hound_mode"/>\n'
    '    <addaction name="actionEnable_superhound_mode"/>\n'
    '    <addaction name="actionUse_TX_frequency_jumps"/>\n',
    1
)
definition_marker = '  <action name="actionEnable_superhound_mode">\n'
hound_marker = '  <action name="actionEnable_hound_mode">\n'
if definition_marker in ui:
    bad.append("synthetic UI unexpectedly already contains QAction definition")
if ui.count(hound_marker) != 1:
    bad.append("synthetic Hound QAction anchor not unique")
ui = ui.replace(hound_marker, definition_marker + hound_marker, 1)
if ui.count('<addaction name="actionEnable_superhound_mode"/>') != 1:
    bad.append("SuperHound menu reference count wrong")
if ui.count('<action name="actionEnable_superhound_mode">') != 1:
    bad.append("SuperHound QAction definition count wrong")

required_ft2 = [
    'best_working_frequency (current_band)',
    'old_fast_mode != new_fast_mode',
    'm_TRperiod=3.75',
    'frequency_list_merge (missing_ft2_frequency_rows)',
    'npts1=39744',
    'ft2_offset_sec=0.24',
]
for needle in required_ft2:
    if needle not in ft:
        bad.append("FT2 architecture marker missing: " + needle)

marker = 'SQ4KOU FT2: per-row saved-table migration'
aud = (root / "AUDIT_PROJECT_R12.py").read_text(encoding="utf-8")
if marker not in ft:
    bad.append("stable frequency-migration marker missing from patch_ft2.py")
if marker not in aud:
    bad.append("stable frequency-migration marker missing from AUDIT_PROJECT_R12.py")
for unstable in ['SQ4KOU FT2 R10: per-row migration', 'SQ4KOU FT2 R11: per-row migration', 'SQ4KOU FT2 R12: per-row migration']:
    if unstable in ft or unstable in aud:
        bad.append("release-coupled migration marker remains: " + unstable)

if bad:
    print("[FAIL] R12 patcher self-test")
    for x in bad:
        print(" -", x)
    raise SystemExit(2)

print("[PASS] R12 patcher self-test")
print(" - clean-source SuperHound menu/QAction sequencing")
print(" - FT2 same-band QRG transition")
print(" - FT4/FT2 fast polling")
print(" - full FT2 RX/fallback markers")
