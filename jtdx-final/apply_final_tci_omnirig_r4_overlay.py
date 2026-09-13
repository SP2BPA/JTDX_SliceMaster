from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not pp.exists() or not bp.exists():
    raise SystemExit('[FAIL] FINAL-TCI patcher/builder missing')

# R4 rule: the verified FINAL-TCI VFO/band state machine is authoritative.
# Do not transplant BANDSAFE/BANDFIX/coalescing/reconnect sequencing changes here.
s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU R4: native FINAL-TCI QSY path + OmniRig; JT9 shutdown cleanup only.'
if marker not in s:
    block = r'''

# SQ4KOU R4: native FINAL-TCI QSY path + OmniRig; JT9 shutdown cleanup only.
# killbyname(): 0 = terminated successfully, 603 = process not running.
# This fixes only the misleading shutdown popup. TCITransceiver.cpp is intentionally
# left exactly on the verified FINAL-TCI source path.
p, t = load('mainwindow.cpp')
old = """          int iret=killbyname(\"jtdxjt9.exe\");
          if(iret == 603) break;
            JTDXMessageBox::warning_message (this, \"\", tr (\"Error Killing jtdxjt9.exe Process\")
                                         , tr (\"KillByName return code: %1\")
                                         .arg (iret));
"""
new = """          int iret=killbyname(\"jtdxjt9.exe\");
          if(iret == 0) continue;   // process terminated successfully; drain any stale copy
          if(iret == 603) break;    // process is already not running
          JTDXMessageBox::warning_message (this, \"\", tr (\"Error Killing jtdxjt9.exe Process\")
                                       , tr (\"KillByName return code: %1\")
                                       .arg (iret));
          break;                    // report a real error once; never loop modal warnings
"""
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] mainwindow JT9 shutdown anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
    save(p, t)
    print('[OK] JT9 shutdown return-code handling')
else:
    print('[SKIP] JT9 shutdown return-code handling already present')

_, t = load('mainwindow.cpp')
for needle in [
    'if(iret == 0) continue;',
    'if(iret == 603) break;',
    'report a real error once; never loop modal warnings',
]:
    if needle not in t:
        raise SystemExit(f'[FAIL] JT9 shutdown postcheck missing {needle!r}')
print('[PASS] R4 JT9 shutdown source postcheck')
'''
    s += block
    pp.write_text(s, encoding='utf-8', newline='\n')

# Reject the exact runtime-state changes that regressed the first manual QSY in R3.
# These strings are from the later BANDSAFE/coalescing overlay and must not enter R4.
s = pp.read_text(encoding='utf-8')
for forbidden in [
    'bool const rx_superseded',
    'bool const tx_superseded',
    'band_change = !HPSDR &&',
    'Cancel any half-finished VFO/split transaction.',
    'do_frequency(string_to_frequency(restore_rx), restore_mode, false)',
    'do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)',
]:
    if forbidden in s:
        raise SystemExit(f'[FAIL] R4 native TCI gate: forbidden later-state-machine patch {forbidden!r}')
print('[PASS] R4 native FINAL-TCI QSY/reconnect path retained')

b = bp.read_text(encoding='utf-8')

# The FINAL builder used a 180 s pacman watchdog. On current GitHub Windows runners
# the official MSYS2 dependency transaction can legitimately take just over 3 min,
# and killing pacman mid-transaction leaves Qt5 metadata incomplete. Give pacman
# enough time to finish atomically instead of retrying from a damaged local DB.
if "'600s'," not in b:
    if b.count("'180s',") != 1:
        raise SystemExit(f'[FAIL] pacman timeout anchor count={b.count("\'180s\',")}')
    b = b.replace("'180s',", "'600s',", 1)

# Enable the already-present native JTDX OmniRig backend; no parallel CAT implementation.
if '-DJTDX_ENABLE_OMNIRIG=ON' not in b:
    if b.count('-DJTDX_ENABLE_OMNIRIG=OFF') != 1:
        raise SystemExit('[FAIL] OmniRig CMake flag anchor missing')
    b = b.replace('-DJTDX_ENABLE_OMNIRIG=OFF', '-DJTDX_ENABLE_OMNIRIG=ON', 1)

old_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5; do\n'
new_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5 dumpcpp-qt5; do\n'
if new_tools not in b:
    if b.count(old_tools) != 1:
        raise SystemExit(f'[FAIL] OmniRig tool gate anchor count={b.count(old_tools)}')
    b = b.replace(old_tools, new_tools, 1)

alias_anchor = 'ln -sf /mingw64/bin/windeployqt-qt5.exe "$WORK/bin/windeployqt.exe"\n'
alias_new = alias_anchor + 'ln -sf /mingw64/bin/dumpcpp-qt5.exe "$WORK/bin/dumpcpp.exe"\n'
if alias_new not in b:
    if b.count(alias_anchor) != 1:
        raise SystemExit(f'[FAIL] dumpcpp alias anchor count={b.count(alias_anchor)}')
    b = b.replace(alias_anchor, alias_new, 1)

# Pin Qt5 explicitly as well as through CMAKE_PREFIX_PATH. This prevents a stale or
# partially refreshed CMake search path from hiding a valid Qt5 installation.
qt_anchor = '  -DCMAKE_PREFIX_PATH="$HAMLIB_PREFIX_WIN;C:/msys64/mingw64" \\\n'
qt_line = qt_anchor + '  -DQt5_DIR=C:/msys64/mingw64/lib/cmake/Qt5 \\\n'
if '-DQt5_DIR=C:/msys64/mingw64/lib/cmake/Qt5' not in b:
    if b.count(qt_anchor) != 1:
        raise SystemExit(f'[FAIL] Qt5 CMake anchor count={b.count(qt_anchor)}')
    b = b.replace(qt_anchor, qt_line, 1)

cmake_anchor = 'rm -rf jtdx/build-superhound\ncmake -S jtdx -B jtdx/build-superhound -G Ninja \\\n'
preflight = '''# Native OmniRig COM + Qt5 preflight.\nOMNIRIG_AXSERVER="$(dumpcpp -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270} 2>/dev/null | tr -d '\\r' || true)"\nif [ -z "$OMNIRIG_AXSERVER" ]; then\n  echo '[FAIL] OmniRig COM server/type library is not registered on this Windows host'\n  exit 38\nfi\necho "[PASS] OmniRig COM type library: $OMNIRIG_AXSERVER"\nif [ ! -f /mingw64/lib/cmake/Qt5/Qt5Config.cmake ]; then\n  echo '[FAIL] Qt5Config.cmake missing after MSYS2 dependency installation'\n  exit 45\nfi\necho '[PASS] Qt5 CMake package present'\n\nrm -rf jtdx/build-superhound\ncmake -S jtdx -B jtdx/build-superhound -G Ninja \\\n'''
if '[PASS] OmniRig COM type library:' not in b:
    if b.count(cmake_anchor) != 1:
        raise SystemExit(f'[FAIL] OmniRig CMake preflight anchor count={b.count(cmake_anchor)}')
    b = b.replace(cmake_anchor, preflight, 1)

post_anchor = "echo '[PASS] CMake FFTW threads link gate'\n\ncmake --build jtdx/build-superhound --parallel\n"
post_block = '''echo '[PASS] CMake FFTW threads link gate'\n\ngrep -Fq 'JTDX_ENABLE_OMNIRIG:BOOL=ON' jtdx/build-superhound/CMakeCache.txt || {\n  echo '[FAIL] OmniRig CMake option is not ON'\n  exit 39\n}\ngrep -Fq 'OmniRigTransceiver.cpp' jtdx/build-superhound/build.ninja || {\n  echo '[FAIL] OmniRigTransceiver.cpp is absent from Ninja build graph'\n  exit 40\n}\ngrep -Fq 'JTDX_ENABLE_OMNIRIG' jtdx/build-superhound/build.ninja || {\n  echo '[FAIL] OmniRig compile definition is absent from Ninja build graph'\n  exit 41\n}\nif ! grep -Fiq 'OmniRig.cpp' jtdx/build-superhound/build.ninja; then\n  echo '[FAIL] OmniRig ActiveQt generation rule missing from Ninja graph'\n  exit 42\nfi\necho '[PASS] OmniRig configure/source/generator-rule gates'\n\ncmake --build jtdx/build-superhound --parallel\n\nif ! find jtdx/build-superhound -type f -iname 'OmniRig.h' -print -quit | grep -q .; then\n  echo '[FAIL] generated OmniRig ActiveQt wrapper header missing after build'\n  exit 43\nfi\nif ! find jtdx/build-superhound -type f -iname 'OmniRig.cpp' -print -quit | grep -q .; then\n  echo '[FAIL] generated OmniRig ActiveQt wrapper source missing after build'\n  exit 44\nfi\necho '[PASS] generated OmniRig ActiveQt wrapper files'\n'''
if "echo '[PASS] generated OmniRig ActiveQt wrapper files'" not in b:
    if b.count(post_anchor) != 1:
        raise SystemExit(f'[FAIL] OmniRig postcheck anchor count={b.count(post_anchor)}')
    b = b.replace(post_anchor, post_block, 1)

# Separate MSI identity for the R4 regression fix candidate.
if "MSI_VERSION='2.2.201'" not in b:
    if b.count("MSI_VERSION='2.2.199'") != 1:
        raise SystemExit('[FAIL] MSI version 2.2.199 anchor missing')
    b = b.replace("MSI_VERSION='2.2.199'", "MSI_VERSION='2.2.201'", 1)
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R4-win64'"
if new_name not in b:
    old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-SQ4KOU-FINAL-win64'"
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] baseline MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

for needle in [
    marker,
    "'600s',",
    '-DJTDX_ENABLE_OMNIRIG=ON',
    'lrelease-qt5 dumpcpp-qt5',
    '-DQt5_DIR=C:/msys64/mingw64/lib/cmake/Qt5',
    '[PASS] Qt5 CMake package present',
    '[PASS] OmniRig COM type library:',
    'JTDX_ENABLE_OMNIRIG:BOOL=ON',
    "MSI_VERSION='2.2.201'",
    new_name,
]:
    haystack = pp.read_text(encoding='utf-8') if needle == marker else bp.read_text(encoding='utf-8')
    if needle not in haystack:
        raise SystemExit(f'[FAIL] R4 overlay postcheck missing {needle!r}')

print('[PASS] R4 verified FINAL-TCI + native OmniRig overlay applied')
