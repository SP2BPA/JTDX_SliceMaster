from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
here = Path(__file__).resolve().parent
r5 = here / 'apply_final_tci_omnirig_r5_overlay.py'
if not r5.exists():
    raise SystemExit('[FAIL] R5 overlay missing')

# R6 is incremental over R5. The R5 HPSDR-specific acknowledgement was not
# reached with Thetis because the TCI server identifies itself through the
# ExpertSDR3-compatible protocol/device strings. R6 therefore makes an exact
# matching RX VFO0 acknowledgement protocol-driven instead of device-name-driven.
subprocess.run([sys.executable, str(r5), str(root)], check=True)

pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not pp.exists() or not bp.exists():
    raise SystemExit('[FAIL] FINAL-TCI patcher/builder missing after R5 overlay')

s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU R6: exact matching VFO0 completes RX band-QSY regardless of device label.'
if marker not in s:
    block = r"""

# SQ4KOU R6: exact matching VFO0 completes RX band-QSY regardless of device label.
# Thetis exposes an ExpertSDR3-compatible TCI identity, so the legacy HPSDR flag
# is not a reliable discriminator. For an outstanding RX QSY, an exact VFO0 echo
# of requested_rx_frequency_ is sufficient proof that the requested RX frequency
# has been accepted. Mirror the original VFO1 band-change completion sequence.
p, t = load('TCITransceiver.cpp')
old = '''              if (busy_rx_frequency_ && (!band_change ||\n                  (HPSDR && rx_frequency_ == requested_rx_frequency_))) {\n                if (band_change && HPSDR && rx_frequency_ == requested_rx_frequency_) {\n                  // Thetis/HPSDR confirmed the target RX VFO0. A VFO1 echo is\n                  // not required to finish the RX band-change transaction.\n                  band_change = false;\n                  if (!tci_timer2_->isActive()) tci_timer2_->start(210);\n                }\n'''
new = '''              if (busy_rx_frequency_ && (!band_change ||\n                  rx_frequency_ == requested_rx_frequency_)) {\n                if (band_change && rx_frequency_ == requested_rx_frequency_) {\n                  // Exact VFO0 echo confirms the requested RX QSY. A VFO1 echo\n                  // is not required to finish the RX band-change transaction.\n                  band_change = false;\n                  if (!tci_timer2_->isActive()) tci_timer2_->start(210);\n                }\n'''
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R6 R5-VFO0 anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
    save(p, t)
    print('[OK] R6 generic matching-VFO0 band-QSY acknowledgement')
else:
    print('[SKIP] R6 generic matching-VFO0 acknowledgement already present')

_, t = load('TCITransceiver.cpp')
for needle in [
    'busy_rx_frequency_ && (!band_change ||',
    'rx_frequency_ == requested_rx_frequency_',
    'Exact VFO0 echo confirms the requested RX QSY.',
    'if (!tci_timer2_->isActive()) tci_timer2_->start(210);',
]:
    if needle not in t:
        raise SystemExit(f'[FAIL] R6 VFO0 postcheck missing {needle!r}')
if 'HPSDR && rx_frequency_ == requested_rx_frequency_' in t:
    raise SystemExit('[FAIL] R6 still depends on HPSDR for matching VFO0 acknowledgement')
print('[PASS] R6 generic exact-VFO0 acknowledgement source postcheck')
"""
    s += block
    pp.write_text(s, encoding='utf-8', newline='\n')

b = bp.read_text(encoding='utf-8')
if "MSI_VERSION='2.2.203'" not in b:
    if b.count("MSI_VERSION='2.2.202'") != 1:
        raise SystemExit('[FAIL] R6 MSI version 2.2.202 anchor missing')
    b = b.replace("MSI_VERSION='2.2.202'", "MSI_VERSION='2.2.203'", 1)

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R5-BANDQSY-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R6-VFO0ACK-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R6 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

for needle in [
    marker,
    '-DJTDX_ENABLE_OMNIRIG=ON',
    "MSI_VERSION='2.2.203'",
    new_name,
]:
    haystack = pp.read_text(encoding='utf-8') if needle == marker else bp.read_text(encoding='utf-8')
    if needle not in haystack:
        raise SystemExit(f'[FAIL] R6 overlay postcheck missing {needle!r}')

print('[PASS] R6 = R5 + protocol-driven exact VFO0 RX-QSY acknowledgement')
