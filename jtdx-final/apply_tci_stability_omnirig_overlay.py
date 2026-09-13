from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not pp.exists() or not bp.exists():
    raise SystemExit('[FAIL] FINAL-TCI patcher/builder missing')

s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU TCI stability/reconnect hardening over verified FINAL-TCI.'
if marker not in s:
    block = r"""

# SQ4KOU TCI stability/reconnect hardening over verified FINAL-TCI.
# Preserve the existing SuperHound/FT2/OmniRig source surface. Only TCI is changed.
p, t = load('TCITransceiver.cpp')

# 1) A disconnect must not carry an unfinished band/VFO transaction into the
# next WebSocket session.
old_disc = '''    busy_rx2_ = false;\n\n    // A lost TCI host must never leave JTDX logically in TX.\n'''
new_disc = '''    busy_rx2_ = false;\n\n    // Cancel any half-finished VFO/split transaction. These timers and\n    // band_change belong to the old socket session and must never survive it.\n    band_change = false;\n    if (tci_timer1_ && tci_timer1_->isActive()) tci_timer1_->stop();\n    if (tci_timer2_ && tci_timer2_->isActive()) tci_timer2_->stop();\n    if (tci_timer3_ && tci_timer3_->isActive()) tci_timer3_->stop();\n\n    // A lost TCI host must never leave JTDX logically in TX.\n'''
if new_disc not in t:
    if t.count(old_disc) != 1:
        raise SystemExit(f'[FAIL] reconnect disconnect anchor count={t.count(old_disc)}')
    t = t.replace(old_disc, new_disc, 1)

# 2) Restore VFO/split after Thetis restart through the native JTDX TCI state
# machine. Raw vfo/split writes bypass busy flags/timers and corrupt later QSY.
old_replay = '''    // Re-apply JTDX's requested rig state after a TCI server restart.  The\n    // requested_* values survive the drop, while *_ state is refreshed by\n    // the host snapshot received just after WebSocket connect.\n    if (!requested_mode_.isEmpty() && requested_mode_ != mode_)\n      sendTextMessage(mode_to_command(requested_mode_));\n\n    if (!requested_rx_frequency_.isEmpty() && requested_rx_frequency_ != rx_frequency_) {\n      const QString cmd = CmdVFO + SmDP + rx_ + SmCM + "0" + SmCM + requested_rx_frequency_ + SmTZ;\n      sendTextMessage(cmd);\n    }\n\n    if (requested_split_ != split_) {\n      const QString cmd = CmdSplitEnable + SmDP + rx_ + SmCM + (requested_split_ ? SmTrue : SmFalse) + SmTZ;\n      sendTextMessage(cmd);\n    }\n    if (requested_split_ && !requested_other_frequency_.isEmpty() && requested_other_frequency_ != other_frequency_) {\n      const QString cmd = CmdVFO + SmDP + rx_ + SmCM + "1" + SmCM + requested_other_frequency_ + SmTZ;\n      sendTextMessage(cmd);\n    }\n'''
new_replay = '''    // Re-apply JTDX's requested rig state after a TCI server restart through\n    // the native JTDX TCI state machine.\n    const QString restore_rx = requested_rx_frequency_;\n    const QString restore_tx = requested_other_frequency_;\n    const bool restore_split = requested_split_;\n    MODE restore_mode = get_mode(true);\n\n    band_change = false;\n    if (!restore_rx.isEmpty())\n      do_frequency(string_to_frequency(restore_rx), restore_mode, false);\n    else if (!requested_mode_.isEmpty() && requested_mode_ != mode_)\n      do_mode(restore_mode);\n\n    if (restore_split && !restore_tx.isEmpty())\n      do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false);\n    else if (restore_split != split_)\n      rig_split();\n'''
if new_replay not in t:
    if t.count(old_replay) != 1:
        raise SystemExit(f'[FAIL] reconnect replay anchor count={t.count(old_replay)}')
    t = t.replace(old_replay, new_replay, 1)

# 3) Qt UnknownSocketError can be -1. QVector::at(-1) aborts the process.
old_error = '    error_ = tr ("TCI websocket error: %1").arg (errortable.at (err));\n'
new_error = '''    int const err_index = static_cast<int>(err);\n    QString const err_text = (err_index >= 0 && err_index < errortable.size())\n                           ? errortable.at(err_index)\n                           : tr("UnknownSocket");\n    error_ = tr ("TCI websocket error: %1").arg (err_text);\n'''
if new_error not in t:
    if t.count(old_error) != 1:
        raise SystemExit(f'[FAIL] SocketError anchor count={t.count(old_error)}')
    t = t.replace(old_error, new_error, 1)

# 4) TCI frames are external input. Never index a short/malformed frame.
start = t.find('void TCITransceiver::onMessageReceived(const QString &str)')
end = t.find('\nvoid TCITransceiver::sendTextMessage', start)
if start < 0 or end < 0:
    raise SystemExit('[FAIL] TCI onMessageReceived boundaries missing')
mb = t[start:end]
old_head = '''void TCITransceiver::onMessageReceived(const QString &str)\n{\n//qDebug() << "From WEB" << str;\n    QStringList cmd_list = str.split(";", SkipEmptyParts);\n'''
new_head = '''void TCITransceiver::onMessageReceived(const QString &str)\n{\n//qDebug() << "From WEB" << str;\n    // A queued callback can arrive while the old socket is being torn down.\n    if (stopping_ || !tci_timer1_ || !tci_timer2_ || !tci_timer3_) return;\n    QStringList cmd_list = str.split(";", SkipEmptyParts);\n'''
if new_head not in mb:
    if mb.count(old_head) != 1:
        raise SystemExit(f'[FAIL] parser entry anchor count={mb.count(old_head)}')
    mb = mb.replace(old_head, new_head, 1)

old_parse = '''    for (QString cmds : cmd_list){\n        QStringList cmd = cmds.split(":", SkipEmptyParts);\n        QStringList args = cmd.last().split(",", SkipEmptyParts);\n        Tci_Cmd idCmd = mapCmd_[cmd.first()];\n'''
new_parse = '''    for (QString cmds : cmd_list){\n        QStringList cmd = cmds.split(":", SkipEmptyParts);\n        if (cmd.isEmpty()) continue;\n        QStringList args;\n        if (cmd.size() > 1) args = cmd.last().split(",", SkipEmptyParts);\n        Tci_Cmd idCmd = mapCmd_[cmd.first()];\n        auto arg = [&args](int index) -> QString {\n          return (index >= 0 && index < args.size()) ? args.value(index) : QString();\n        };\n'''
if new_parse not in mb:
    if mb.count(old_parse) != 1:
        raise SystemExit(f'[FAIL] parser command anchor count={mb.count(old_parse)}')
    mb = mb.replace(old_parse, new_parse, 1)
mb = mb.replace('args.at(', 'arg(')

num_repls = {
'''            power_ = 10 * arg(3).split(".")[0].toInt() + arg(3).split(".")[1].toInt();\n            swr_ = 10 * arg(4).split(".")[0].toInt() + arg(4).split(".")[1].toInt();\n''':
'''            power_ = qRound(arg(3).toDouble() * 10.0);\n            swr_ = qRound(arg(4).toDouble() * 10.0);\n''',
'''          swr_ = 10 * arg(0).split(".")[0].toInt() + arg(0).split(".")[1].toInt();\n''':
'''          swr_ = qRound(arg(0).toDouble() * 10.0);\n''',
'''          power_ = 10 * arg(0).split(".")[0].toInt() + arg(0).split(".")[1].toInt();\n''':
'''          power_ = qRound(arg(0).toDouble() * 10.0);\n''',
}
for oldn, newn in num_repls.items():
    if newn not in mb:
        if mb.count(oldn) != 1:
            raise SystemExit('[FAIL] numeric parser anchor missing')
        mb = mb.replace(oldn, newn, 1)

t = t[:start] + mb + t[end:]

# 5) Thetis/HPSDR does not require the old VFO1 echo coupling for a large QSY.
old_band = '      band_change = abs(rx_frequency_.toInt()-requested_rx_frequency_.toInt()) > 1000000;\n'
new_band = '      band_change = !HPSDR && abs(rx_frequency_.toInt()-requested_rx_frequency_.toInt()) > 1000000;\n'
if new_band not in t:
    if t.count(old_band) != 1:
        raise SystemExit(f'[FAIL] HPSDR band_change anchor count={t.count(old_band)}')
    t = t.replace(old_band, new_band, 1)

# 6) Never dereference a stale/null WebSocket while reconnecting.
old_send = '''void TCITransceiver::sendTextMessage(const QString &message)\n{\n    if (inConnected) commander_->sendTextMessage(message);\n}\n'''
new_send = '''void TCITransceiver::sendTextMessage(const QString &message)\n{\n    if (commander_ && inConnected && commander_->state() == QAbstractSocket::ConnectedState)\n      commander_->sendTextMessage(message);\n}\n'''
if new_send not in t:
    if t.count(old_send) != 1:
        raise SystemExit(f'[FAIL] safe send anchor count={t.count(old_send)}')
    t = t.replace(old_send, new_send, 1)

# 7) Do not drop a newer RX request while an older QSY waits for acknowledgement.
old_busy_rx = '''  if (busy_rx_frequency_) return;\n  else {\n    requested_rx_frequency_ = f_string;\n    requested_mode_ = map_mode (m);\n  }\n'''
new_busy_rx = '''  requested_rx_frequency_ = f_string;\n  requested_mode_ = map_mode (m);\n  if (busy_rx_frequency_) return;\n'''
if new_busy_rx not in t:
    if t.count(old_busy_rx) != 1:
        raise SystemExit(f'[FAIL] RX coalesce anchor count={t.count(old_busy_rx)}')
    t = t.replace(old_busy_rx, new_busy_rx, 1)

old_rx_result = '''      if (requested_rx_frequency_ == rx_frequency_) update_rx_frequency (f);\n      else {\n//        printf ("%s(%0.1f) TCI failed set rxfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),rx_frequency_.toStdString().c_str(),requested_rx_frequency_.toStdString().c_str());\n#if JTDX_DEBUG_TO_FILE\n        FILE * pFile = fopen (debug_file_.c_str(),"a");\n        fprintf (pFile,"%s(%0.1f) TCI failed set rxfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),rx_frequency_.toStdString().c_str(),requested_rx_frequency_.toStdString().c_str());\n        fclose (pFile);\n#endif\n        error_ = tr ("TCI failed set rxfreq");\n//        tci_Ready = false;\n//        throw error {tr ("TCI failed set rxfreq")};\n      }\n      busy_rx_frequency_ = false;\n'''
new_rx_result = '''      bool const rx_superseded = requested_rx_frequency_ != f_string;\n      if (f_string == rx_frequency_) update_rx_frequency (f);\n      else if (!rx_superseded) {\n#if JTDX_DEBUG_TO_FILE\n        FILE * pFile = fopen (debug_file_.c_str(),"a");\n        fprintf (pFile,"%s(%0.1f) TCI failed set rxfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),rx_frequency_.toStdString().c_str(),f_string.toStdString().c_str());\n        fclose (pFile);\n#endif\n        error_ = tr ("TCI failed set rxfreq");\n      }\n      busy_rx_frequency_ = false;\n      if (rx_superseded) {\n        QTimer::singleShot(0, this, [this]() {\n          if (!stopping_ && tci_Ready && _power_ && !busy_rx_frequency_ && !requested_rx_frequency_.isEmpty())\n            do_frequency(string_to_frequency(requested_rx_frequency_), get_mode(true), false);\n        });\n      }\n'''
if new_rx_result not in t:
    if t.count(old_rx_result) != 1:
        raise SystemExit(f'[FAIL] RX completion anchor count={t.count(old_rx_result)}')
    t = t.replace(old_rx_result, new_rx_result, 1)

# 8) Apply the same newest-request-wins rule to TX VFO/split.
old_busy_tx = '''  if (busy_other_frequency_) return;\n  requested_other_frequency_ = f_string;\n  requested_mode_ = map_mode (mode);\n  if (tx)\n    {\n      requested_split_ = true;\n'''
new_busy_tx = '''  requested_mode_ = map_mode (mode);\n  requested_split_ = tx != 0;\n  requested_other_frequency_ = tx ? f_string : QString();\n  if (busy_other_frequency_) return;\n  if (tx)\n    {\n'''
if new_busy_tx not in t:
    if t.count(old_busy_tx) != 1:
        raise SystemExit(f'[FAIL] TX coalesce anchor count={t.count(old_busy_tx)}')
    t = t.replace(old_busy_tx, new_busy_tx, 1)

t = t.replace('''  else {\n    requested_split_ = false;\n    requested_other_frequency_ = "";\n''', '''  else {\n''', 1)

old_tx_result = '''          if (requested_other_frequency_ == other_frequency_) update_other_frequency (tx);\n          else {\n//            printf ("%s(%0.1f) TCI failed set txfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),other_frequency_.toStdString().c_str(),requested_other_frequency_.toStdString().c_str());\n#if JTDX_DEBUG_TO_FILE\n            FILE * pFile = fopen (debug_file_.c_str(),"a");\n            fprintf (pFile,"%s(%0.1f) TCI failed set txfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),other_frequency_.toStdString().c_str(),requested_other_frequency_.toStdString().c_str());\n            fclose (pFile);\n#endif\n            error_ = tr ("TCI failed set txfreq");\n//            tci_Ready = false;\n//            throw error {tr ("TCI failed set txfreq")};\n          }\n          busy_other_frequency_ = false;\n'''
new_tx_result = '''          bool const tx_superseded = !requested_split_ || requested_other_frequency_ != f_string;\n          if (f_string == other_frequency_) update_other_frequency (tx);\n          else if (!tx_superseded) {\n#if JTDX_DEBUG_TO_FILE\n            FILE * pFile = fopen (debug_file_.c_str(),"a");\n            fprintf (pFile,"%s(%0.1f) TCI failed set txfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),other_frequency_.toStdString().c_str(),f_string.toStdString().c_str());\n            fclose (pFile);\n#endif\n            error_ = tr ("TCI failed set txfreq");\n          }\n          busy_other_frequency_ = false;\n          if (tx_superseded) {\n            QTimer::singleShot(0, this, [this]() {\n              if (stopping_ || !tci_Ready || !_power_ || busy_other_frequency_) return;\n              Frequency const pending_tx = (requested_split_ && !requested_other_frequency_.isEmpty())\n                                         ? string_to_frequency(requested_other_frequency_) : 0;\n              do_tx_frequency(pending_tx, get_mode(true), false);\n            });\n          }\n'''
if new_tx_result not in t:
    if t.count(old_tx_result) != 1:
        raise SystemExit(f'[FAIL] TX completion anchor count={t.count(old_tx_result)}')
    t = t.replace(old_tx_result, new_tx_result, 1)

save(p, t)
for needle in [
    'Cancel any half-finished VFO/split transaction.',
    'do_frequency(string_to_frequency(restore_rx), restore_mode, false)',
    'do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)',
    'err_index >= 0 && err_index < errortable.size()',
    'auto arg = [&args](int index) -> QString',
    'qRound(arg(3).toDouble() * 10.0)',
    'band_change = !HPSDR &&',
    'commander_ && inConnected && commander_->state() == QAbstractSocket::ConnectedState',
    'bool const rx_superseded',
    'bool const tx_superseded',
]:
    if needle not in t:
        raise SystemExit(f'[FAIL] TCI stability postcheck missing {needle!r}')
print('[PASS] selective TCI stability/reconnect hardening')
"""
    s += block
    pp.write_text(s, encoding='utf-8', newline='\n')

b = bp.read_text(encoding='utf-8')

# Builder gates must follow the new reconnect state-machine markers.
old_reconnect_gates = "grep -Fq 'requested_rx_frequency_ != rx_frequency_' jtdx/TCITransceiver.cpp\ngrep -Fq 'requested_split_ != split_' jtdx/TCITransceiver.cpp\n"
new_reconnect_gates = "grep -Fq 'Cancel any half-finished VFO/split transaction.' jtdx/TCITransceiver.cpp\ngrep -Fq 'do_frequency(string_to_frequency(restore_rx), restore_mode, false)' jtdx/TCITransceiver.cpp\ngrep -Fq 'do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)' jtdx/TCITransceiver.cpp\n"
if new_reconnect_gates not in b:
    if b.count(old_reconnect_gates) != 1:
        raise SystemExit(f'[FAIL] builder reconnect gate anchor count={b.count(old_reconnect_gates)}')
    b = b.replace(old_reconnect_gates, new_reconnect_gates, 1)

gate_anchor = "grep -Fq 'Fail safe: a reconnect can never arm TX.' jtdx/TCITransceiver.cpp\n"
stability_gates = gate_anchor + """grep -Fq 'err_index >= 0 && err_index < errortable.size()' jtdx/TCITransceiver.cpp
grep -Fq 'auto arg = [&args](int index) -> QString' jtdx/TCITransceiver.cpp
grep -Fq 'qRound(arg(3).toDouble() * 10.0)' jtdx/TCITransceiver.cpp
grep -Fq 'band_change = !HPSDR &&' jtdx/TCITransceiver.cpp
grep -Fq 'commander_ && inConnected && commander_->state() == QAbstractSocket::ConnectedState' jtdx/TCITransceiver.cpp
grep -Fq 'bool const rx_superseded' jtdx/TCITransceiver.cpp
grep -Fq 'bool const tx_superseded' jtdx/TCITransceiver.cpp
"""
if "grep -Fq 'bool const rx_superseded'" not in b:
    if b.count(gate_anchor) != 1:
        raise SystemExit(f'[FAIL] builder TCI gate anchor count={b.count(gate_anchor)}')
    b = b.replace(gate_anchor, stability_gates, 1)

# Keep the known-good native JTDX OmniRig backend; do not add a parallel CAT path.
if '-DJTDX_ENABLE_OMNIRIG=ON' not in b:
    if b.count('-DJTDX_ENABLE_OMNIRIG=OFF') != 1:
        raise SystemExit('[FAIL] OmniRig CMake flag anchor missing')
    b = b.replace('-DJTDX_ENABLE_OMNIRIG=OFF', '-DJTDX_ENABLE_OMNIRIG=ON', 1)

old_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5; do\n'
new_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5 dumpcpp; do\n'
if new_tools not in b:
    if b.count(old_tools) != 1:
        raise SystemExit(f'[FAIL] OmniRig tool gate anchor count={b.count(old_tools)}')
    b = b.replace(old_tools, new_tools, 1)

cmake_anchor = 'rm -rf jtdx/build-superhound\ncmake -S jtdx -B jtdx/build-superhound -G Ninja \\\n'
preflight = '''# Native OmniRig COM preflight.\nOMNIRIG_AXSERVER="$(dumpcpp -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270} 2>/dev/null | tr -d '\\r' || true)"\nif [ -z "$OMNIRIG_AXSERVER" ]; then\n  echo '[FAIL] OmniRig COM server/type library is not registered on this Windows host'\n  exit 38\nfi\necho "[PASS] OmniRig COM type library: $OMNIRIG_AXSERVER"\n\nrm -rf jtdx/build-superhound\ncmake -S jtdx -B jtdx/build-superhound -G Ninja \\\n'''
if '[PASS] OmniRig COM type library:' not in b:
    if b.count(cmake_anchor) != 1:
        raise SystemExit(f'[FAIL] OmniRig CMake preflight anchor count={b.count(cmake_anchor)}')
    b = b.replace(cmake_anchor, preflight, 1)

post_anchor = "echo '[PASS] CMake FFTW threads link gate'\n\ncmake --build jtdx/build-superhound --parallel\n"
post_block = '''echo '[PASS] CMake FFTW threads link gate'\n\ngrep -Fq 'JTDX_ENABLE_OMNIRIG:BOOL=ON' jtdx/build-superhound/CMakeCache.txt || {\n  echo '[FAIL] OmniRig CMake option is not ON'\n  exit 39\n}\ngrep -Fq 'OmniRigTransceiver.cpp' jtdx/build-superhound/build.ninja || {\n  echo '[FAIL] OmniRigTransceiver.cpp is absent from Ninja build graph'\n  exit 40\n}\ngrep -Fq 'JTDX_ENABLE_OMNIRIG' jtdx/build-superhound/build.ninja || {\n  echo '[FAIL] OmniRig compile definition is absent from Ninja build graph'\n  exit 41\n}\nif ! find jtdx/build-superhound -type f -iname 'OmniRig.h' -print -quit | grep -q .; then\n  echo '[FAIL] generated OmniRig ActiveQt wrapper header missing'\n  exit 42\nfi\necho '[PASS] OmniRig configure/source/generator gates'\n\ncmake --build jtdx/build-superhound --parallel\n'''
if "echo '[PASS] OmniRig configure/source/generator gates'" not in b:
    if b.count(post_anchor) != 1:
        raise SystemExit(f'[FAIL] OmniRig postcheck anchor count={b.count(post_anchor)}')
    b = b.replace(post_anchor, post_block, 1)

# Separate MSI identity for this regression-fix candidate.
if "MSI_VERSION='2.2.200'" not in b:
    if b.count("MSI_VERSION='2.2.199'") != 1:
        raise SystemExit('[FAIL] MSI version 2.2.199 anchor missing')
    b = b.replace("MSI_VERSION='2.2.199'", "MSI_VERSION='2.2.200'", 1)
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-STABILITY-OMNIRIG-win64'"
if new_name not in b:
    old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-SQ4KOU-FINAL-win64'"
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] baseline MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

for needle in [
    marker,
    '-DJTDX_ENABLE_OMNIRIG=ON',
    'lrelease-qt5 dumpcpp',
    '[PASS] OmniRig COM type library:',
    'JTDX_ENABLE_OMNIRIG:BOOL=ON',
    "MSI_VERSION='2.2.200'",
    new_name,
]:
    haystack = pp.read_text(encoding='utf-8') if needle == marker else bp.read_text(encoding='utf-8')
    if needle not in haystack:
        raise SystemExit(f'[FAIL] final overlay postcheck missing {needle!r}')

print('[PASS] FINAL-TCI stability + native OmniRig overlay applied')
