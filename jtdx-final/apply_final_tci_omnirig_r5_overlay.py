from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
here = Path(__file__).resolve().parent
r4 = here / 'apply_final_tci_omnirig_r4_overlay.py'
if not r4.exists():
    raise SystemExit('[FAIL] R4 overlay missing')

# R5 is deliberately incremental over the user-tested R4 candidate.
# Preserve R4 shutdown/OmniRig/reconnect behavior and change only the
# HPSDR/Thetis large-band QSY acknowledgement path.
subprocess.run([sys.executable, str(r4), str(root)], check=True)

pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not pp.exists() or not bp.exists():
    raise SystemExit('[FAIL] FINAL-TCI patcher/builder missing after R4 overlay')

s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU R5: HPSDR band-QSY may complete on matching VFO0 acknowledgement.'
if marker not in s:
    block = r'''

# SQ4KOU R5: HPSDR band-QSY may complete on matching VFO0 acknowledgement.
# FINAL-TCI normally keeps a >1 MHz RX QSY busy until a VFO1 echo arrives.
# Thetis/HPSDR can acknowledge the requested RX VFO0 without emitting the VFO1
# echo in the order expected by this legacy state machine. In that case the
# requested RX frequency is already correct, but mysleep1() times out and the
# next poll raises a TRCVR control error.
#
# Keep the native FINAL-TCI band_change state machine. Only when HPSDR is active,
# an RX transaction is busy, and VFO0 exactly matches the requested target, use
# that VFO0 as the missing band-change acknowledgement. Mirror the original VFO1
# completion path by clearing band_change, arming timer2 for split/TX settling,
# and calling tci_done1(). No request coalescing or reconnect replay is added.
p, t = load('TCITransceiver.cpp')
old = '''              if (busy_rx_frequency_ && !band_change) {\n//                printf (" cmdvfo0 done1");\n#if JTDX_DEBUG_TO_FILE\n                fprintf (pFile," cmdvfo0 done1");\n#endif\n                tci_done1();\n              } else if (!tci_timer2_->isActive() && split_) {\n'''
new = '''              if (busy_rx_frequency_ && (!band_change ||\n                  (HPSDR && rx_frequency_ == requested_rx_frequency_))) {\n                if (band_change && HPSDR && rx_frequency_ == requested_rx_frequency_) {\n                  // Thetis/HPSDR confirmed the target RX VFO0. A VFO1 echo is\n                  // not required to finish the RX band-change transaction.\n                  band_change = false;\n                  if (!tci_timer2_->isActive()) tci_timer2_->start(210);\n                }\n//                printf (" cmdvfo0 done1");\n#if JTDX_DEBUG_TO_FILE\n                fprintf (pFile," cmdvfo0 done1");\n#endif\n                tci_done1();\n              } else if (!tci_timer2_->isActive() && split_) {\n'''
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R5 Cmd_VFO0 band-QSY anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
    save(p, t)
    print('[OK] R5 HPSDR matching-VFO0 band-QSY acknowledgement')
else:
    print('[SKIP] R5 HPSDR band-QSY acknowledgement already present')

_, t = load('TCITransceiver.cpp')
for needle in [
    'HPSDR && rx_frequency_ == requested_rx_frequency_',
    'A VFO1 echo is',
    'if (!tci_timer2_->isActive()) tci_timer2_->start(210);',
]:
    if needle not in t:
        raise SystemExit(f'[FAIL] R5 band-QSY postcheck missing {needle!r}')

# Guard against accidentally reintroducing the broad R3/BANDSAFE state-machine
# changes that regressed the first manual QSY.
for forbidden in [
    'bool const rx_superseded',
    'bool const tx_superseded',
    'band_change = !HPSDR &&',
    'do_frequency(string_to_frequency(restore_rx), restore_mode, false)',
    'do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)',
]:
    if forbidden in t:
        raise SystemExit(f'[FAIL] R5 narrow-fix gate: forbidden broad patch {forbidden!r}')
print('[PASS] R5 narrow HPSDR band-QSY source postcheck')
'''
    s += block
    pp.write_text(s, encoding='utf-8', newline='\n')

b = bp.read_text(encoding='utf-8')
if "MSI_VERSION='2.2.202'" not in b:
    if b.count("MSI_VERSION='2.2.201'") != 1:
        raise SystemExit('[FAIL] R5 MSI version 2.2.201 anchor missing')
    b = b.replace("MSI_VERSION='2.2.201'", "MSI_VERSION='2.2.202'", 1)

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R4-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R5-BANDQSY-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R5 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

for needle in [
    marker,
    '-DJTDX_ENABLE_OMNIRIG=ON',
    "MSI_VERSION='2.2.202'",
    new_name,
]:
    haystack = pp.read_text(encoding='utf-8') if needle == marker else bp.read_text(encoding='utf-8')
    if needle not in haystack:
        raise SystemExit(f'[FAIL] R5 overlay postcheck missing {needle!r}')

print('[PASS] R5 = tested R4 + targeted HPSDR matching-VFO0 band-QSY acknowledgement')
