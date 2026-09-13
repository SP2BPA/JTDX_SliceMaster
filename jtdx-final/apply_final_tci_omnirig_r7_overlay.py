from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
here = Path(__file__).resolve().parent
r6 = here / 'apply_final_tci_omnirig_r6_overlay.py'
if not r6.exists():
    raise SystemExit('[FAIL] R6 overlay missing')

# R7 is incremental over R6. R6 proved that device-name gating was not the
# complete cause of the RX-QSY failure. The native JTDX 2.2.159 do_frequency()
# waits on tci_loop1_, but tci_done1 is shared by several unrelated TCI events.
# One such event can therefore wake mysleep1(2000) before the requested VFO0
# acknowledgement arrives, after which JTDX immediately reports
# "TCI failed set rxfreq". R7 keeps the native state machine but makes the wait
# target-specific: unrelated tci_done1 wakeups no longer complete RX QSY.
subprocess.run([sys.executable, str(r6), str(root)], check=True)

pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not pp.exists() or not bp.exists():
    raise SystemExit('[FAIL] FINAL-TCI patcher/builder missing after R6 overlay')

s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU R7: RX QSY acknowledgement wait is target-specific, not signal-specific.'
if marker not in s:
    block = r'''

# SQ4KOU R7: RX QSY acknowledgement wait is target-specific, not signal-specific.
# tci_done1 is shared by VFO, mode, ready/start/audio and other TCI paths. The
# original single mysleep1(2000) can therefore be released by an unrelated TCI
# event and test rx_frequency_ too early. Keep processing the Qt event loop, but
# do not complete the RX QSY wait until VFO0 equals requested_rx_frequency_ or
# the real wall-clock deadline expires. One bounded resend is used only after a
# genuine 2 s target timeout; a final mismatch remains a real TRCVR error.
p, t = load('TCITransceiver.cpp')

if '#include <QElapsedTimer>' not in t:
    inc_old = '#include <QThread>\n'
    inc_new = '#include <QThread>\n#include <QElapsedTimer>\n'
    if t.count(inc_old) != 1:
        raise SystemExit(f'[FAIL] R7 QElapsedTimer include anchor count={t.count(inc_old)}')
    t = t.replace(inc_old, inc_new, 1)

old = '''          sendTextMessage(cmd);\n          mysleep1(2000);\n//      if (band_change) mysleep1(500);\n          if (requested_rx_frequency_ == rx_frequency_) update_rx_frequency (f);\n'''
new = '''          sendTextMessage(cmd);\n          // SQ4KOU R7: tci_done1 is shared by unrelated TCI messages. A single\n          // mysleep1(2000) can return early on mode/ready/audio/etc. Keep waiting\n          // until the requested VFO0 value is actually observed or 2 s elapse.\n          QElapsedTimer rx_ack_wait;\n          rx_ack_wait.start();\n          while (requested_rx_frequency_ != rx_frequency_ && inConnected &&\n                 rx_ack_wait.elapsed() < 2000) {\n            int const left = 2000 - static_cast<int>(rx_ack_wait.elapsed());\n            mysleep1(left > 250 ? 250 : left);\n          }\n\n          // A genuine timeout gets one bounded resend. This covers a dropped\n          // WebSocket command/notification without turning transient traffic into\n          // a modal TRCVR failure. We still fail if the target never arrives.\n          if (requested_rx_frequency_ != rx_frequency_ && inConnected && _power_) {\n            sendTextMessage(cmd);\n            rx_ack_wait.restart();\n            while (requested_rx_frequency_ != rx_frequency_ && inConnected &&\n                   rx_ack_wait.elapsed() < 1000) {\n              int const left = 1000 - static_cast<int>(rx_ack_wait.elapsed());\n              mysleep1(left > 250 ? 250 : left);\n            }\n          }\n//      if (band_change) mysleep1(500);\n          if (requested_rx_frequency_ == rx_frequency_) update_rx_frequency (f);\n'''
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R7 do_frequency wait anchor count={t.count(old)}')
    t = t.replace(old, new, 1)

save(p, t)

_, t = load('TCITransceiver.cpp')
for needle in [
    '#include <QElapsedTimer>',
    'QElapsedTimer rx_ack_wait;',
    'rx_ack_wait.elapsed() < 2000',
    'rx_ack_wait.restart();',
    'rx_ack_wait.elapsed() < 1000',
    'requested_rx_frequency_ != rx_frequency_ && inConnected',
    'if (requested_rx_frequency_ == rx_frequency_) update_rx_frequency (f);',
    'error_ = tr ("TCI failed set rxfreq");',
]:
    if needle not in t:
        raise SystemExit(f'[FAIL] R7 target-specific RX-QSY postcheck missing {needle!r}')

# There must no longer be a bare single 2 s sleep directly after the RX VFO send.
forbidden = '''          sendTextMessage(cmd);\n          mysleep1(2000);\n//      if (band_change) mysleep1(500);'''
if forbidden in t:
    raise SystemExit('[FAIL] R7 still contains native signal-specific RX-QSY wait')
print('[PASS] R7 target-specific RX-QSY acknowledgement wait + bounded resend')
'''
    s += block
    pp.write_text(s, encoding='utf-8', newline='\n')

b = bp.read_text(encoding='utf-8')
if "MSI_VERSION='2.2.204'" not in b:
    if b.count("MSI_VERSION='2.2.203'") != 1:
        raise SystemExit('[FAIL] R7 MSI version 2.2.203 anchor missing')
    b = b.replace("MSI_VERSION='2.2.203'", "MSI_VERSION='2.2.204'", 1)

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R6-VFO0ACK-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R7-RXACK-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R7 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

for needle in [
    marker,
    '-DJTDX_ENABLE_OMNIRIG=ON',
    "MSI_VERSION='2.2.204'",
    new_name,
]:
    haystack = pp.read_text(encoding='utf-8') if needle == marker else bp.read_text(encoding='utf-8')
    if needle not in haystack:
        raise SystemExit(f'[FAIL] R7 overlay postcheck missing {needle!r}')

print('[PASS] R7 = R6 + target-specific RX VFO acknowledgement wait; OmniRig preserved')
