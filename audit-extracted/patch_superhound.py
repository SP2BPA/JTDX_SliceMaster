#!/usr/bin/env python3
from pathlib import Path
import sys, re

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_superhound.py <jtdx-source>')
root = Path(sys.argv[1]).resolve()


def load(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'[FAIL] missing: {p}')
    return p, p.read_text(encoding='utf-8', errors='strict')


def save(p, s):
    p.write_text(s, encoding='utf-8', newline='\n')


def replace_once(rel, old, new, label):
    p, s = load(rel)
    if new in s:
        print(f'[SKIP] {label}: already patched')
        return
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'[FAIL] {label}: expected exactly 1 anchor, got {n}')
    s = s.replace(old, new, 1)
    save(p, s)
    print(f'[OK] {label}')



def replace_upgrade_once(rel, clean_old, stage1_old, new, label):
    p, s = load(rel)
    if new in s:
        print(f'[SKIP] {label}: already patched')
        return
    if stage1_old and stage1_old in s:
        if s.count(stage1_old) != 1:
            raise SystemExit(f'[FAIL] {label}: Stage1 anchor is not unique')
        s = s.replace(stage1_old, new, 1)
    else:
        n = s.count(clean_old)
        if n != 1:
            raise SystemExit(f'[FAIL] {label}: expected clean or Stage1 anchor, got clean={n}')
        s = s.replace(clean_old, new, 1)
    save(p, s)
    print(f'[OK] {label}')


def insert_before_once(rel, marker, block, label):
    p, s = load(rel)
    if block.strip() in s:
        print(f'[SKIP] {label}: already patched')
        return
    n = s.count(marker)
    if n != 1:
        raise SystemExit(f'[FAIL] {label}: expected exactly 1 anchor, got {n}')
    s = s.replace(marker, block + marker, 1)
    save(p, s)
    print(f'[OK] {label}')


def insert_after_once(rel, marker, block, label):
    p, s = load(rel)
    if block.strip() in s:
        print(f'[SKIP] {label}: already patched')
        return
    n = s.count(marker)
    if n != 1:
        raise SystemExit(f'[FAIL] {label}: expected exactly 1 anchor, got {n}')
    s = s.replace(marker, marker + block, 1)
    save(p, s)
    print(f'[OK] {label}')


# 1) Shared C++/Fortran ABI: append new bool at the END to preserve offsets of every existing field.
replace_once('commons.h',
    '    bool learlystart;\n',
    '    bool learlystart;\n    bool lsuperhound;\n',
    'commons.h ABI lsuperhound')
replace_once('lib/jt9com.f90',
    '     logical(c_bool) :: learlystart\n',
    '     logical(c_bool) :: learlystart\n     logical(c_bool) :: lsuperhound\n',
    'jt9com.f90 ABI lsuperhound')

# 2) MainWindow state + slot.
replace_once('mainwindow.h',
    '  void on_actionEnable_hound_mode_toggled(bool checked);\n',
    '  void on_actionEnable_hound_mode_toggled(bool checked);\n  void on_actionEnable_superhound_mode_toggled(bool checked);\n',
    'mainwindow.h slot')
replace_upgrade_once('mainwindow.h',
    '  bool m_houndMode;\n  bool m_commonFT8b;\n',
    '  bool m_houndMode;\n  bool m_superHoundMode;\n  int m_superHoundSavedRxFreq;\n  bool m_commonFT8b;\n',
    '  bool m_houndMode;\n  bool m_superHoundMode;\n  bool m_superHoundArmed;\n  int m_superHoundSavedRxFreq;\n  QString m_superHoundFoxCall;\n  bool m_commonFT8b;\n',
    'mainwindow.h members')
replace_upgrade_once('mainwindow.cpp',
    '  m_houndMode {false},\n  m_commonFT8b {true},\n',
    '  m_houndMode {false},\n  m_superHoundMode {false},\n  m_superHoundSavedRxFreq {1500},\n  m_commonFT8b {true},\n',
    '  m_houndMode {false},\n  m_superHoundMode {false},\n  m_superHoundArmed {false},\n  m_superHoundSavedRxFreq {1500},\n  m_superHoundFoxCall {""},\n  m_commonFT8b {true},\n',
    'mainwindow.cpp initializer')

# Integrate the existing Wide Graph/monitor into the main window. No monitor
# code is duplicated: the same WideGraph instance is re-parented and inserted
# below the existing main controls. Its controls_widget is already the bottom
# row of WideGraph, so monitor controls remain below the plot.
monitor_block = r'''  // SQ4KOU: integrated monitor at the bottom of the main JTDX window.
  // Reuse the existing WideGraph instance. A vertical splitter gives one
  // resizable window: JTDX controls above, spectrum/waterfall monitor below.
  QSplitter *integratedMonitorSplitter=new QSplitter(Qt::Vertical,ui->centralWidget);
  integratedMonitorSplitter->setChildrenCollapsible(false);
  ui->gridLayout_3->removeWidget(ui->splitter);
  integratedMonitorSplitter->addWidget(ui->splitter);

  m_wideGraph->setParent(integratedMonitorSplitter);
  m_wideGraph->setWindowFlags(Qt::Widget);
  m_wideGraph->setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Expanding);
  m_wideGraph->setMinimumHeight(190);
  integratedMonitorSplitter->addWidget(m_wideGraph.data());
  integratedMonitorSplitter->setStretchFactor(0,3);
  integratedMonitorSplitter->setStretchFactor(1,2);
  QList<int> integratedMonitorSizes;
  integratedMonitorSizes << 520 << 260;
  integratedMonitorSplitter->setSizes(integratedMonitorSizes);
  ui->gridLayout_3->addWidget(integratedMonitorSplitter,0,0);
  m_wideGraph->show();
  if(width()<900 || height()<760) resize(qMax(width(),900),qMax(height(),760));
'''
insert_after_once('mainwindow.cpp',
    '  ui->setupUi(this);\n',
    monitor_block,
    'mainwindow.cpp integrated bottom monitor')
insert_after_once('mainwindow.cpp',
    'MainWindow::~MainWindow()\n{\n',
    '  m_wideGraph->saveSettings(); // embedded monitor has no separate closeEvent\n',
    'mainwindow.cpp save embedded monitor settings')

# Make decoder flag follow GUI state.
replace_once('mainwindow.cpp',
    '  dec_data.params.lhound=m_houndMode ? 1 : 0;\n',
    '  dec_data.params.lhound=m_houndMode ? 1 : 0;\n  dec_data.params.lsuperhound=m_superHoundMode ? 1 : 0;\n',
    'mainwindow.cpp decoder flag')

# If ordinary Hound is switched off, SuperHound cannot remain armed.
replace_once('mainwindow.cpp',
    '  m_houndMode=checked;\n  m_wideGraph->setHoundFilter(m_houndMode);\n',
    '  m_houndMode=checked;\n  if(!m_houndMode && m_superHoundMode) ui->actionEnable_superhound_mode->setChecked(false);\n  m_wideGraph->setHoundFilter(m_houndMode);\n',
    'mainwindow.cpp hound/superhound consistency')

super_slot = r'''void MainWindow::on_actionEnable_superhound_mode_toggled(bool checked)
{
  if(checked) {
    if(m_mode != "FT8") {
      m_superHoundMode=false;
      m_superHoundArmed=false;
      m_superHoundFoxCall.clear();
      ui->actionEnable_superhound_mode->setChecked(false);
      statusBar()->showMessage(tr("SuperHound requires FT8 mode"), 5000);
      return;
    }

    // Set SuperHound before ordinary Hound. SuperHound uses normal FT8 TX
    // and must not inherit old-Hound split/QSY restrictions.
    m_superHoundSavedRxFreq=ui->RxFreqSpinBox->value();
    m_superHoundMode=true;
    m_superHoundArmed=false;
    m_superHoundFoxCall.clear();
    if(!m_houndMode) ui->actionEnable_hound_mode->setChecked(true);
    if(!m_houndMode) {
      m_superHoundMode=false;
      ui->actionEnable_superhound_mode->setChecked(false);
      return;
    }

    if(m_enableTx) enableTx_mode(false);
    m_houndTXfreqJumps=false;
    ui->actionUse_TX_frequency_jumps->setChecked(false);
    ui->actionUse_TX_frequency_jumps->setEnabled(false);
    ui->RxFreqSpinBox->setValue(750);
    ui->HoundButton->setText("SuperHound WAIT");
    statusBar()->showMessage(tr("SuperHound RX active at 750 Hz - double-click a SuperFox decode (~) to arm TX"), 8000);
  } else {
    bool wasSuper=m_superHoundMode;
    m_superHoundMode=false;
    m_superHoundArmed=false;
    m_superHoundFoxCall.clear();
    if(wasSuper && m_superHoundSavedRxFreq>0) ui->RxFreqSpinBox->setValue(m_superHoundSavedRxFreq);
    ui->HoundButton->setText("Hound");
    setHoundAppearance(m_houndMode);
    if(m_houndMode) {
      bool allowJumps=!m_commonFT8b && m_config.split_mode() && m_config.rig_name() != "None";
      m_houndTXfreqJumps=false;
      ui->actionUse_TX_frequency_jumps->setChecked(false);
      ui->actionUse_TX_frequency_jumps->setEnabled(allowJumps);
    }
  }
}

'''
# Insert on a clean tree or replace the Stage1 implementation in an existing
# V11/V14 incremental build tree.
p, s = load('mainwindow.cpp')
old_super_slot = r'''void MainWindow::on_actionEnable_superhound_mode_toggled(bool checked)
{
  if(checked) {
    if(m_mode != "FT8") {
      m_superHoundMode=false;
      ui->actionEnable_superhound_mode->setChecked(false);
      statusBar()->showMessage(tr("SuperHound requires FT8 mode"), 5000);
      return;
    }

    // SuperHound extends JTDX's existing Hound state. Hound TX stays normal FT8.
    if(!m_houndMode) ui->actionEnable_hound_mode->setChecked(true);
    if(!m_houndMode) {
      m_superHoundMode=false;
      ui->actionEnable_superhound_mode->setChecked(false);
      return;
    }

    m_superHoundSavedRxFreq=ui->RxFreqSpinBox->value();
    m_superHoundMode=true;
    ui->RxFreqSpinBox->setValue(750);
    ui->HoundButton->setText("SuperHound");
    statusBar()->showMessage(tr("SuperHound RX enabled at 750 Hz"), 5000);
  } else {
    bool wasSuper=m_superHoundMode;
    m_superHoundMode=false;
    if(wasSuper && m_superHoundSavedRxFreq>0) ui->RxFreqSpinBox->setValue(m_superHoundSavedRxFreq);
    ui->HoundButton->setText("Hound");
  }
}

'''
if super_slot.strip() in s:
    print('[SKIP] mainwindow.cpp SuperHound slot: already patched')
elif old_super_slot in s:
    s=s.replace(old_super_slot,super_slot,1)
    save(p,s)
    print('[OK] mainwindow.cpp SuperHound slot upgraded from Stage1')
else:
    marker='void MainWindow::on_actionUse_TX_frequency_jumps_triggered (bool checked)'
    if s.count(marker) != 1 or 'void MainWindow::on_actionEnable_superhound_mode_toggled' in s:
        raise SystemExit('[FAIL] mainwindow.cpp SuperHound slot anchor/migration mismatch')
    s=s.replace(marker,super_slot+marker,1)
    save(p,s)
    print('[OK] mainwindow.cpp SuperHound slot')

# SuperHound uses normal FT8 Hound TX, without old-Hound split-frequency jumps.
p, s = load('mainwindow.cpp')
s2 = s.replace('if(!m_config.split_mode() && !m_commonFT8b && m_config.rig_name() != "None") {',
               'if(!m_superHoundMode && !m_config.split_mode() && !m_commonFT8b && m_config.rig_name() != "None") {')
s2 = s2.replace('if(checked && !m_config.split_mode() && !m_commonFT8b && m_config.rig_name() != "None") {',
                'if(checked && !m_superHoundMode && !m_config.split_mode() && !m_commonFT8b && m_config.rig_name() != "None") {')
s2 = s2.replace('m_houndTXfreqJumps=!m_commonFT8b && m_config.split_mode() && m_config.rig_name() != "None";',
                'm_houndTXfreqJumps=!m_superHoundMode && !m_commonFT8b && m_config.split_mode() && m_config.rig_name() != "None";')
s2 = s2.replace('m_houndTXfreqJumps=checked && !m_commonFT8b && m_config.split_mode() && m_config.rig_name() != "None";',
                'm_houndTXfreqJumps=checked && !m_superHoundMode && !m_commonFT8b && m_config.split_mode() && m_config.rig_name() != "None";')
if s2 == s:
    required = ['!m_superHoundMode && !m_config.split_mode()',
                'm_houndTXfreqJumps=checked && !m_superHoundMode',
                'm_houndTXfreqJumps=!m_superHoundMode && !m_commonFT8b']
    if not all(x in s for x in required):
        raise SystemExit('[FAIL] mainwindow.cpp SuperHound split/QSY gate anchors not found')
else:
    save(p, s2)
    print('[OK] mainwindow.cpp SuperHound disables old Hound split/QSY jumps')

replace_once('mainwindow.cpp',
    'void MainWindow::on_actionUse_TX_frequency_jumps_triggered (bool checked) { m_houndTXfreqJumps=checked; }',
    '''void MainWindow::on_actionUse_TX_frequency_jumps_triggered (bool checked)
{
  if(m_superHoundMode) {
    m_houndTXfreqJumps=false;
    if(checked) ui->actionUse_TX_frequency_jumps->setChecked(false);
    return;
  }
  m_houndTXfreqJumps=checked;
}''',
    'mainwindow.cpp block TX frequency jumps in SuperHound')

# Blind calling is blocked until a decoded SuperFox line is double-clicked.
insert_after_once('mainwindow.cpp',
    'void MainWindow::on_enableTxButton_clicked (bool checked)\n{\n',
    '''  if(checked && m_superHoundMode) {
    bool validSuperFoxTarget=m_superHoundArmed && !m_superHoundFoxCall.isEmpty() &&
      Radio::base_callsign(ui->dxCallEntry->text())==Radio::base_callsign(m_superHoundFoxCall);
    if(!validSuperFoxTarget) {
      ui->enableTxButton->setChecked(false);
      statusBar()->showMessage(tr("SuperHound: first double-click a decoded SuperFox message (~)"), 7000);
      return;
    }
  }
''',
    'mainwindow.cpp SuperHound blind-TX gate')

super_click_gate = r'''  if(m_superHoundMode) {
    if(!t2.contains(" ~ ")) {
      statusBar()->showMessage(tr("SuperHound: QSO must start by double-clicking a SuperFox decode (~)"), 7000);
      return;
    }

    QString sfMessage=t2.section('~',1).trimmed();
    QStringList sfWords=sfMessage.split(' ', SkipEmptyParts);
    QString foxCall;
    if(sfWords.size()>=2 && sfWords.at(0)!="$VERIFY$") foxCall=sfWords.at(1);
    if(foxCall.isEmpty() || !Radio::is_callsign(foxCall)) {
      statusBar()->showMessage(tr("SuperHound: selected SuperFox decode has no callable Fox callsign"), 7000);
      return;
    }

    m_superHoundArmed=true;
    m_superHoundFoxCall=foxCall;
    ui->RxFreqSpinBox->setValue(750);
    ui->HoundButton->setText("SuperHound");
    statusBar()->showMessage(tr("SuperHound armed for %1").arg(foxCall), 7000);

    // SuperFox payloads can contain another Hound as the first callsign.
    // The QSO target is always the Fox, the second payload word.
    hiscall=foxCall;
    if(sfWords.at(0)!="CQ") hisgrid.clear();
  }
'''
insert_after_once('mainwindow.cpp',
    '  decodedtext.deCallAndGrid(/*out*/hiscall,hisgrid);\n',
    super_click_gate,
    'mainwindow.cpp SuperHound double-click arm gate')

replace_once('mainwindow.cpp',
    '  if (m_lockTxFreq or ctrl or TxModeChanged) {\n',
    '  if ((m_lockTxFreq or ctrl or TxModeChanged) && !m_superHoundMode) {\n',
    'mainwindow.cpp keep SuperHound TX frequency on decode click')
replace_once('mainwindow.cpp',
    '  if (ui->RxFreqSpinBox->isEnabled ())\n    {\n      ui->RxFreqSpinBox->setValue (frequency); //Set Rx freq\n    }\n',
    '  if (ui->RxFreqSpinBox->isEnabled ())\n    {\n      if(m_superHoundMode) ui->RxFreqSpinBox->setValue(750);\n      else ui->RxFreqSpinBox->setValue (frequency); //Set Rx freq\n    }\n',
    'mainwindow.cpp keep SuperHound RX at 750 Hz')

# 3) GUI action in DXpedition menu.
replace_once('mainwindow.ui',
    '    <addaction name="actionEnable_hound_mode"/>\n    <addaction name="actionUse_TX_frequency_jumps"/>\n',
    '    <addaction name="actionEnable_hound_mode"/>\n    <addaction name="actionEnable_superhound_mode"/>\n    <addaction name="actionUse_TX_frequency_jumps"/>\n',
    'mainwindow.ui menu action')

super_action = '''  <action name="actionEnable_superhound_mode">\n   <property name="checkable">\n    <bool>true</bool>\n   </property>\n   <property name="toolTip">\n    <string>Decode SuperFox with normal FT8 Hound TX. RX stays at 750 Hz; TX is armed only after double-clicking a SuperFox decode.</string>\n   </property>\n   <property name="text">\n    <string>Enable SuperHound mode</string>\n   </property>\n  </action>\n'''
old_super_action = '''  <action name="actionEnable_superhound_mode">\n   <property name="checkable">\n    <bool>true</bool>\n   </property>\n   <property name="toolTip">\n    <string>Decode SuperFox while using the existing JTDX Hound transmit sequence. RX audio is set to 750 Hz while enabled.</string>\n   </property>\n   <property name="text">\n    <string>Enable SuperHound mode</string>\n   </property>\n  </action>\n'''
p, s = load('mainwindow.ui')
if super_action in s:
    print('[SKIP] mainwindow.ui SuperHound action definition: already patched')
elif old_super_action in s:
    s=s.replace(old_super_action,super_action,1)
    save(p,s)
    print('[OK] mainwindow.ui SuperHound action upgraded from Stage1')
else:
    marker='  <action name="actionEnable_hound_mode">\n'
    # A menu reference <addaction name="actionEnable_superhound_mode"/> is
    # inserted one step earlier. Only an existing QAction DEFINITION is a
    # migration conflict; the menu reference itself is expected here.
    definition_marker='  <action name="actionEnable_superhound_mode">\n'
    if s.count(marker)!=1 or definition_marker in s:
        raise SystemExit('[FAIL] mainwindow.ui SuperHound action definition anchor/migration mismatch')
    s=s.replace(marker,super_action+marker,1)
    save(p,s)
    print('[OK] mainwindow.ui SuperHound action definition')

# 4) JTDX-adapted SuperFox RX wrapper. Deliberately omits WSJT-X sfox_remove_ft8(),
# whose sync8 API is incompatible with JTDX 2.2.159. Core QPC SuperFox decoding is retained.
superdir = root / 'lib' / 'superfox'
if not superdir.exists():
    raise SystemExit('[FAIL] lib/superfox missing: copy it from pinned WSJT-X 2.7 before patching')
wrapper = superdir / 'sfrx_sub_jtdx.f90'
wrapper_text = r'''subroutine sfrx_sub_jtdx(nutc,nfqso,ntol,iwave)

  use sfox_mod

  real iwave(NMAX)
  integer*1 xdec(0:49)
  character*13 foxcall
  complex c0(NMAX)
  real dd(NMAX)
  logical crc_ok

  fsync=nfqso
  ftol=ntol
  fsample=12000.0
  call sfox_init(7,127,50,'no',fspread,delay,fsample,24)
  npts=15*12000

  dd=iwave

  ! WSJT-X calls sfox_remove_ft8() here. JTDX 2.2.159 has a different
  ! sync8() interface, so interference cancellation is intentionally omitted
  ! in Stage 1. The SuperFox/QPC decoder itself is unchanged.
  call sfox_ana(dd,npts,c0,npts)
  call sfox_remove_tone(c0,fsync)

  ndepth=3
  dth=0.5
  damp=1.0

  call qpc_decode2(c0,fsync,ftol,xdec,ndepth,dth,damp,crc_ok,   &
       snrsync,fbest,tbest,snr)
  if(crc_ok) then
     nsnr=nint(snr)
     nsignature=1
     call sfox_unpack(nutc,xdec,nsnr,fbest-750.0,tbest,foxcall,nsignature)
  endif

  return
end subroutine sfrx_sub_jtdx
'''
if wrapper.exists() and wrapper.read_text(encoding='utf-8') == wrapper_text:
    print('[SKIP] lib/superfox/sfrx_sub_jtdx.f90 unchanged')
else:
    wrapper.write_text(wrapper_text, encoding='utf-8', newline='\n')
    print('[OK] generated lib/superfox/sfrx_sub_jtdx.f90')

# JTDX packjt77 uses an extra nthr argument for unpack28().  Also, unlike
# WSJT-X 2.7, JTDX keeps unpackgrid() inside module packjt; importing it
# explicitly avoids an unresolved external symbol unpackgrid_ at link time.
p, s = load('lib/superfox/sfox_unpack.f90')
s2 = s.replace('call unpack28(n28,foxcall,success)', 'call unpack28(n28,foxcall,success,1)')
s2 = s2.replace('call unpack28(n28,c13,success)', 'call unpack28(n28,c13,success,1)')
if '  use packjt, only : unpackgrid\n' not in s2:
    if s2.count('  use packjt77\n') != 1:
        raise SystemExit('[FAIL] sfox_unpack.f90: packjt77 use anchor not found')
    s2 = s2.replace('  use packjt77\n', '  use packjt77\n  use packjt, only : unpackgrid\n', 1)
if s2 == s and ('unpack28(n28,foxcall,success,1)' not in s or 'use packjt, only : unpackgrid' not in s):
    raise SystemExit('[FAIL] sfox_unpack.f90: JTDX adaptation anchors not found')
if s2 != s:
    save(p, s2)
    print('[OK] adapted sfox_unpack.f90 to JTDX packjt77 + packjt::unpackgrid')
else:
    print('[SKIP] sfox_unpack.f90 JTDX adaptation unchanged')

# Old JTDX deliberately skipped FFTW thread libraries on WIN32 because the
# historical Windows FFTW bundle exposed thread entry points differently.
# Current MSYS2 ships libfftw3f_threads as a separate import library, so the
# existing FindFFTW3 module must include it when the requested 'threads'
# component is present.  Otherwise jtdxjt9 links only libfftw3f and misses
# fftwf_init_threads/fftwf_plan_with_nthreads/fftwf_cleanup_threads.
replace_once('CMake/Modules/FindFFTW3.cmake',
    '''# If using threads, we need to link against threaded libraries as well - except on Windows.
if (NOT WIN32 AND _use_threads)
  set (_thread_libs)
  foreach (_lib ${_libraries})
    list (APPEND _thread_libs ${_lib}_threads)
  endforeach (_lib ${_libraries})
  set (_libraries ${_thread_libs} ${_libraries})
endif (NOT WIN32 AND _use_threads)
''',
    '''# Modern MSYS2/MinGW also ships separate FFTW thread import libraries.
if (_use_threads)
  set (_thread_libs)
  foreach (_lib ${_libraries})
    list (APPEND _thread_libs ${_lib}_threads)
  endforeach (_lib ${_libraries})
  set (_libraries ${_thread_libs} ${_libraries})
endif (_use_threads)
''',
    'FindFFTW3 modern MinGW thread library')

# 5) Invoke SuperFox RX from JTDX's jt9 shared-memory backend only on the even FT8 sequence.
call_block = '''  if(local_params%nmode.eq.8 .and. local_params%lsuperhound .and. &\n       .not.local_params%nagain .and. .not.local_params%nagainfil .and. local_params%nzhsym.ge.50 .and. &\n       mod(local_params%nutc,10).eq.0) then\n     call sfrx_sub_jtdx(local_params%nutc,local_params%nfqso,local_params%ntol,dd)\n  endif\n\n'''
insert_before_once('lib/jt9a.f90',
    '  call multimode_decoder(local_params)\n',
    call_block,
    'jt9a.f90 SuperFox RX call')

# 6) Add only the decoder-side SuperFox sources; no SuperFox transmitter/simulator sources.
fort = '''  lib/superfox/qpc/qpc_mod.f90\n  lib/superfox/sfox_mod.f90\n  lib/superfox/qpc_decode2.f90\n  lib/superfox/qpc_likelihoods2.f90\n  lib/superfox/qpc_snr.f90\n  lib/superfox/qpc_sync.f90\n  lib/superfox/smo121.f90\n  lib/superfox/sfox_ana.f90\n  lib/superfox/sfox_demod.f90\n  lib/superfox/sfox_remove_tone.f90\n  lib/superfox/sfox_unpack.f90\n  lib/superfox/sfrx_sub_jtdx.f90\n  lib/superfox/twkfreq2.f90\n'''
insert_before_once('CMakeLists.txt', 'set (wsjt_FSRCS\n', 'set (wsjt_superhound_FSRCS\n'+fort+'  )\n\n', 'CMake SuperHound Fortran list')
# Inject the list into wsjt_FSRCS immediately after its opening.
replace_once('CMakeLists.txt', 'set (wsjt_FSRCS\n', 'set (wsjt_FSRCS\n  ${wsjt_superhound_FSRCS}\n', 'CMake include SuperHound Fortran')

csrc = '''  lib/superfox/qpc/dbgprintf.c\n  lib/superfox/qpc/nhash2.c\n  lib/superfox/qpc/np_qpc.c\n  lib/superfox/qpc/np_rnd.c\n  lib/superfox/qpc/qpc_fwht.c\n  lib/superfox/qpc/qpc_n127k50q128.c\n  lib/superfox/qpc/qpc_subs.c\n'''
insert_before_once('CMakeLists.txt', 'set (wsjt_CSRCS\n', 'set (wsjt_superhound_CSRCS\n'+csrc+'  )\n\n', 'CMake SuperHound C list')
replace_once('CMakeLists.txt', 'set (wsjt_CSRCS\n', 'set (wsjt_CSRCS\n  ${wsjt_superhound_CSRCS}\n', 'CMake include SuperHound C')

# 6b) Make legacy OmniRig support optional. Upstream JTDX 2.2.159 makes
# OmniRig a hard build-time dependency on Windows, even for users who use
# Hamlib/TCI/HRD/Commander. ONECLICK builds with JTDX_ENABLE_OMNIRIG=OFF,
# so the normal JTDX radio-control paths remain available without requiring
# a COM server to be installed merely to compile the program.
replace_once('CMakeLists.txt',
    'option (JTDX_DEBUG_TO_FILE "Write debu to jtdx_debug.txt.")\n',
    'option (JTDX_DEBUG_TO_FILE "Write debu to jtdx_debug.txt.")\noption (JTDX_ENABLE_OMNIRIG "Build legacy OmniRig ActiveX/COM support on Windows." ON)\n',
    'CMake optional OmniRig switch')

replace_once('CMakeLists.txt',
    '''if (WIN32)
  set (wsjt_CXXSRCS
    ${wsjt_CXXSRCS}
    killbyname.cpp
    )

  set (wsjt_qt_CXXSRCS
    ${wsjt_qt_CXXSRCS}
    OmniRigTransceiver.cpp
    )
endif (WIN32)
''',
    '''if (WIN32)
  set (wsjt_CXXSRCS
    ${wsjt_CXXSRCS}
    killbyname.cpp
    )
endif (WIN32)

if (WIN32 AND JTDX_ENABLE_OMNIRIG)
  set (wsjt_qt_CXXSRCS
    ${wsjt_qt_CXXSRCS}
    OmniRigTransceiver.cpp
    )
endif ()
''',
    'CMake conditional OmniRig source')

replace_once('CMakeLists.txt',
    '''if (WIN32)
  # generate the OmniRig COM interface source
  find_program (DUMPCPP dumpcpp)
  if (DUMPCPP-NOTFOUND)
    message (FATAL_ERROR "dumpcpp tool not found")
  endif (DUMPCPP-NOTFOUND)
  execute_process (
    COMMAND ${DUMPCPP} -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270}
    OUTPUT_VARIABLE AXSERVER
    OUTPUT_STRIP_TRAILING_WHITESPACE
    )
  string (STRIP "${AXSERVER}" AXSERVER)
  if (NOT AXSERVER)
    message (FATAL_ERROR "You need to install OmniRig on this computer")
  endif (NOT AXSERVER)
  string (REPLACE "\\\"" "" AXSERVER ${AXSERVER})
  file (TO_CMAKE_PATH ${AXSERVER} AXSERVERSRCS)
endif (WIN32)
''',
    '''if (WIN32 AND JTDX_ENABLE_OMNIRIG)
  # generate the OmniRig COM interface source only when explicitly enabled
  find_program (DUMPCPP dumpcpp)
  if (DUMPCPP-NOTFOUND)
    message (FATAL_ERROR "dumpcpp tool not found")
  endif (DUMPCPP-NOTFOUND)
  execute_process (
    COMMAND ${DUMPCPP} -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270}
    OUTPUT_VARIABLE AXSERVER
    OUTPUT_STRIP_TRAILING_WHITESPACE
    )
  string (STRIP "${AXSERVER}" AXSERVER)
  if (NOT AXSERVER)
    message (FATAL_ERROR "You need to install OmniRig on this computer")
  endif (NOT AXSERVER)
  string (REPLACE "\\\"" "" AXSERVER ${AXSERVER})
  file (TO_CMAKE_PATH ${AXSERVER} AXSERVERSRCS)
endif ()
''',
    'CMake conditional OmniRig COM discovery')

replace_once('CMakeLists.txt',
    '''# AX COM servers
if (WIN32)
  include (QtAxMacros)
  wrap_ax_server (GENAXSRCS ${AXSERVERSRCS})
endif (WIN32)
''',
    '''# AX COM servers
if (WIN32 AND JTDX_ENABLE_OMNIRIG)
  include (QtAxMacros)
  wrap_ax_server (GENAXSRCS ${AXSERVERSRCS})
endif ()
''',
    'CMake conditional OmniRig wrapper generation')

replace_once('CMakeLists.txt',
    '''if (WIN32)
  target_link_libraries (wsjt_qt Qt5::AxContainer Qt5::AxBase)
endif (WIN32)
''',
    '''if (WIN32 AND JTDX_ENABLE_OMNIRIG)
  target_compile_definitions (wsjt_qt PRIVATE JTDX_ENABLE_OMNIRIG)
  target_link_libraries (wsjt_qt Qt5::AxContainer Qt5::AxBase)
endif ()
''',
    'CMake conditional OmniRig ActiveQt link')

replace_once('TransceiverFactory.cpp',
    '#if defined (WIN32)\n#include "OmniRigTransceiver.hpp"\n#endif\n',
    '#if defined (WIN32) && defined (JTDX_ENABLE_OMNIRIG)\n#include "OmniRigTransceiver.hpp"\n#endif\n',
    'TransceiverFactory OmniRig include guard')
replace_once('TransceiverFactory.cpp',
    '#if defined (WIN32)\n  // OmniRig is ActiveX/COM server so only on Windows\n  OmniRigTransceiver::register_transceivers (&transceivers_, OmniRigOneId, OmniRigTwoId);\n#endif\n',
    '#if defined (WIN32) && defined (JTDX_ENABLE_OMNIRIG)\n  // OmniRig is ActiveX/COM server so only on Windows when compiled in.\n  OmniRigTransceiver::register_transceivers (&transceivers_, OmniRigOneId, OmniRigTwoId);\n#endif\n',
    'TransceiverFactory OmniRig registration guard')
replace_once('TransceiverFactory.cpp',
    '#if defined (WIN32)\n    case OmniRigOneId:\n',
    '#if defined (WIN32) && defined (JTDX_ENABLE_OMNIRIG)\n    case OmniRigOneId:\n',
    'TransceiverFactory OmniRig switch guard')

# Ensure CPack/BundleUtilities can resolve the separately built JTDX Hamlib DLL.
replace_once('CMakeLists.txt',
    '    if (WIN32)\n      # DLL directory\n      #set (hamlib_lib_dir ${hamlib_lib_dir}/../bin)\n\n      get_filename_component (fftw_lib_dir ${FFTW3F_LIBRARY} PATH)\n',
    '    if (WIN32)\n      # DLL directories: JTDX Hamlib is built into a private prefix by ONECLICK.\n      get_filename_component (hamlib_import_lib_dir "${Hamlib_LIBRARY}" DIRECTORY)\n      get_filename_component (hamlib_prefix_dir "${hamlib_import_lib_dir}" DIRECTORY)\n      set (hamlib_bin_dir "${hamlib_prefix_dir}/bin")\n      list (APPEND fixup_library_dirs ${hamlib_bin_dir})\n\n      get_filename_component (fftw_lib_dir ${FFTW3F_LIBRARY} PATH)\n',
    'CMake package Hamlib DLL search path')

# 7) Real MSI via CPack WiX instead of upstream NSIS EXE.
replace_once('CMakeLists.txt',
    'if (WIN32)\n  set (CPACK_GENERATOR "NSIS")\n',
    'if (WIN32)\n  set (CPACK_GENERATOR "WIX")\n  set (CPACK_PACKAGE_NAME "JTDX-SuperHound")\n  set (CPACK_PACKAGE_FILE_NAME "JTDX-SuperHound-${wsjtx_VERSION}-win64")\n',
    'CMake Windows CPack -> WiX MSI')

# 7b) GCC/GFortran 16 implements the Fortran SPLIT intrinsic.  The legacy
# JPL ephemeris source bundled with JTDX defines its own SUBROUTINE SPLIT,
# so modern gfortran resolves the old CALL SPLIT(...) statements as the
# intrinsic and reports a missing POS argument.  Rename only this private
# JPL helper and its three call sites; behavior is otherwise unchanged.
p, s = load('lib/jplsubs.f')
if 'SUBROUTINE JPL_SPLIT(TT,FR)' not in s:
    if s.count('SUBROUTINE SPLIT(TT,FR)') != 1:
        raise SystemExit('[FAIL] jplsubs.f: expected one legacy SUBROUTINE SPLIT anchor')
    if s.count('CALL SPLIT(') != 3:
        raise SystemExit(f'[FAIL] jplsubs.f: expected 3 CALL SPLIT anchors, got {s.count("CALL SPLIT(")}')
    s = s.replace('SUBROUTINE SPLIT(TT,FR)', 'SUBROUTINE JPL_SPLIT(TT,FR)', 1)
    s = s.replace('CALL SPLIT(', 'CALL JPL_SPLIT(')
    save(p, s)
    print('[OK] jplsubs.f modern-gfortran SPLIT collision')
else:
    if 'CALL SPLIT(' in s:
        s = s.replace('CALL SPLIT(', 'CALL JPL_SPLIT(')
        save(p, s)
    print('[SKIP] jplsubs.f modern-gfortran SPLIT collision: already patched')


# 7b) TCI reliability: automatic WebSocket reconnect + heartbeat.
# The original JTDX 2.2.159 client only records disconnected/error state;
# do_poll() then throws and the user must manually reopen the TCI connection.
# Keep the implementation deliberately small: one 2 s watchdog timer, WebSocket
# ping/pong heartbeat, safe RX on disconnect, and automatic audio/sensor restore.

replace_once('TCITransceiver.hpp',
    '#include <QTimer>\n#include <QEventLoop>\n',
    '#include <QTimer>\n#include <QEventLoop>\n#include <QElapsedTimer>\n',
    'TCI header QElapsedTimer')

replace_once('TCITransceiver.hpp',
    '  void onError(QAbstractSocket::SocketError err);\n  void onConnected();\n  void onDisconnected();\n',
    '  void onError(QAbstractSocket::SocketError err);\n  void onConnected();\n  void onDisconnected();\n  void onReconnectTimer();\n  void onReconnectReady();\n  void onPong(quint64 elapsedTime, const QByteArray &payload);\n',
    'TCI reconnect slots')

replace_once('TCITransceiver.hpp',
    '  QTimer * tci_timer3_;\n  QEventLoop * tci_loop3_;\n  int nIqBytes;\n',
    '  QTimer * tci_timer3_;\n  QEventLoop * tci_loop3_;\n  QTimer * reconnect_timer_;\n  QElapsedTimer reconnect_clock_;\n  qint64 last_ping_ms_;\n  qint64 last_pong_ms_;\n  bool reconnecting_;\n  bool stopping_;\n  bool startup_complete_;\n  int nIqBytes;\n',
    'TCI reconnect members')

replace_once('TCITransceiver.cpp',
    '  , tci_timer3_ {nullptr}\n  , tci_loop3_ {nullptr}\n  , wavptr_ {nullptr} \n',
    '  , tci_timer3_ {nullptr}\n  , tci_loop3_ {nullptr}\n  , reconnect_timer_ {nullptr}\n  , last_ping_ms_ {0}\n  , last_pong_ms_ {0}\n  , reconnecting_ {false}\n  , stopping_ {false}\n  , startup_complete_ {false}\n  , wavptr_ {nullptr} \n',
    'TCI constructor reconnect state')

old_connected = r'''void TCITransceiver::onConnected()
{
    inConnected = true;
//    printf("%s(%0.1f) TCI connected\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
#if JTDX_DEBUG_TO_FILE
    FILE * pFile = fopen (debug_file_.c_str(),"a");
    fprintf (pFile,"%s(%0.1f) TCI connected\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
    fclose (pFile);
#endif
}
'''
new_connected = r'''void TCITransceiver::onConnected()
{
    inConnected = true;
    error_.clear();
    if (reconnect_clock_.isValid()) {
      qint64 now = reconnect_clock_.elapsed();
      last_ping_ms_ = now;
      last_pong_ms_ = now;
    }
    if (startup_complete_ && reconnecting_ && !stopping_) {
      // Let the TCI host send its initial state snapshot first.
      QTimer::singleShot(700, this, SLOT(onReconnectReady()));
    }
//    printf("%s(%0.1f) TCI connected\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
#if JTDX_DEBUG_TO_FILE
    FILE * pFile = fopen (debug_file_.c_str(),"a");
    fprintf (pFile,"%s(%0.1f) TCI connected%s\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(), reconnecting_ ? " (reconnect)" : "");
    fclose (pFile);
#endif
}
'''
replace_once('TCITransceiver.cpp', old_connected, new_connected, 'TCI onConnected reconnect')

old_disconnected = r'''void TCITransceiver::onDisconnected()
{
    inConnected = false;
//    printf("%s(%0.1f) TCI disconnected\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
#if JTDX_DEBUG_TO_FILE
    FILE * pFile = fopen (debug_file_.c_str(),"a");
    fprintf (pFile,"%s(%0.1f) TCI disconnected\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
    fclose (pFile);
#endif
}
'''
new_disconnected = r'''void TCITransceiver::onDisconnected()
{
    inConnected = false;
    tci_Ready = false;
    stream_audio_ = false;
    _power_ = false;
    busy_rx_frequency_ = false;
    busy_mode_ = false;
    busy_other_frequency_ = false;
    busy_split_ = false;
    busy_drive_ = false;
    busy_PTT_ = false;
    busy_rx2_ = false;

    // A lost TCI host must never leave JTDX logically in TX.
    PTT_ = false;
    requested_PTT_ = false;
    m_state = Idle;
    update_PTT(false);
    power_ = 0;
    swr_ = 0;
    if (do_pwr_) {
      update_power(0);
      update_swr(0);
    }
    Q_EMIT tci_mod_active(false);

    // Release any short synchronous waits that were active when the socket died.
    Q_EMIT tci_done1();
    Q_EMIT tci_done2();
    Q_EMIT tci_done3();

    if (startup_complete_ && !stopping_) reconnecting_ = true;
//    printf("%s(%0.1f) TCI disconnected\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
#if JTDX_DEBUG_TO_FILE
    FILE * pFile = fopen (debug_file_.c_str(),"a");
    fprintf (pFile,"%s(%0.1f) TCI disconnected - automatic reconnect=%d\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(), reconnecting_);
    fclose (pFile);
#endif
}
'''
replace_once('TCITransceiver.cpp', old_disconnected, new_disconnected, 'TCI onDisconnected safe reconnect')

reconnect_funcs = r'''
void TCITransceiver::onPong(quint64 elapsedTime, const QByteArray &payload)
{
    (void)elapsedTime;
    (void)payload;
    if (reconnect_clock_.isValid()) last_pong_ms_ = reconnect_clock_.elapsed();
}

void TCITransceiver::onReconnectTimer()
{
    if (stopping_ || !startup_complete_ || !commander_) return;

    QAbstractSocket::SocketState socketState = commander_->state();
    if (socketState == QAbstractSocket::UnconnectedState) {
      inConnected = false;
      tci_Ready = false;
      reconnecting_ = true;
      error_.clear();
      commander_->open(url_);
      return;
    }

    if (socketState != QAbstractSocket::ConnectedState) return;

    if (!reconnect_clock_.isValid()) {
      reconnect_clock_.start();
      last_ping_ms_ = 0;
      last_pong_ms_ = 0;
    }

    qint64 now = reconnect_clock_.elapsed();

    // A TCP/WebSocket connection can remain nominally "connected" after a
    // network failure. Ping detects this stale-socket case.
    if (now - last_pong_ms_ > 30000) {
      inConnected = false;
      tci_Ready = false;
      reconnecting_ = true;
      commander_->abort();
      return;
    }

    if (now - last_ping_ms_ >= 10000) {
      last_ping_ms_ = now;
      commander_->ping(QByteArray("JTDX-TCI"));
    }
}

void TCITransceiver::onReconnectReady()
{
    if (stopping_ || !startup_complete_ || !reconnecting_ || !inConnected || !commander_) return;

    // Wait for the host's "start" state. If it arrives later, Cmd_Start
    // schedules this routine again.
    if (!_power_) return;

    error_.clear();
    tci_Ready = true;

    // Never restore a pre-drop TX state.
    if (PTT_ && use_for_ptt_) {
      QString cmd;
      if (ESDR3) cmd = CmdTrx + SmDP + rx_ + SmCM + SmFalse + SmCM + "tci" + SmTZ;
      else cmd = CmdTrx + SmDP + rx_ + SmCM + SmFalse + SmTZ;
      sendTextMessage(cmd);
    }
    PTT_ = false;
    requested_PTT_ = false;
    busy_PTT_ = false;
    update_PTT(false);
    m_state = Idle;
    Q_EMIT tci_mod_active(false);

    // Re-apply JTDX's requested rig state after a TCI server restart.  The
    // requested_* values survive the drop, while *_ state is refreshed by
    // the host snapshot received just after WebSocket connect.
    if (!requested_mode_.isEmpty() && requested_mode_ != mode_)
      sendTextMessage(mode_to_command(requested_mode_));

    if (!requested_rx_frequency_.isEmpty() && requested_rx_frequency_ != rx_frequency_) {
      const QString cmd = CmdVFO + SmDP + rx_ + SmCM + "0" + SmCM + requested_rx_frequency_ + SmTZ;
      sendTextMessage(cmd);
    }

    if (requested_split_ != split_) {
      const QString cmd = CmdSplitEnable + SmDP + rx_ + SmCM + (requested_split_ ? SmTrue : SmFalse) + SmTZ;
      sendTextMessage(cmd);
    }
    if (requested_split_ && !requested_other_frequency_.isEmpty() && requested_other_frequency_ != other_frequency_) {
      const QString cmd = CmdVFO + SmDP + rx_ + SmCM + "1" + SmCM + requested_other_frequency_ + SmTZ;
      sendTextMessage(cmd);
    }

    if (!requested_drive_.isEmpty() && requested_drive_ != drive_) {
      QString cmd;
      if (ESDR3) cmd = CmdDrive + SmDP + rx_ + SmCM + requested_drive_ + SmTZ;
      else cmd = CmdDrive + SmDP + requested_drive_ + SmTZ;
      sendTextMessage(cmd);
    }

    // Re-arm subscriptions that are lost when the TCI server process restarts.
    if (HPSDR) {
      const QString cmd = CmdSplitEnable + SmDP + rx_ + SmTZ;
      sendTextMessage(cmd);
    }
    if (ESDR3) {
      const QString rxSensors = CmdRxSensorsEnable + SmDP + (do_snr_ ? SmTrue : SmFalse) + SmCM + "500" + SmTZ;
      sendTextMessage(rxSensors);
      const QString txSensors = CmdTxSensorsEnable + SmDP + (do_pwr_ ? SmTrue : SmFalse) + SmCM + "500" + SmTZ;
      sendTextMessage(txSensors);
    } else if (do_snr_) {
      const QString cmd = CmdSmeter + SmDP + rx_ + SmCM + "0" + SmTZ;
      sendTextMessage(cmd);
    }

    if (tci_audio_) {
      stream_audio_ = false;
      requested_stream_audio_ = true;
      stream_audio(true);
    }

    reconnecting_ = false;
#if JTDX_DEBUG_TO_FILE
    FILE * pFile = fopen (debug_file_.c_str(),"a");
    fprintf (pFile,"%s(%0.1f) TCI automatic reconnect complete\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset());
    fclose (pFile);
#endif
}

'''
insert_after_once('TCITransceiver.cpp', new_disconnected, reconnect_funcs, 'TCI reconnect timer/heartbeat functions')

replace_once('TCITransceiver.cpp',
    '  m_jtdxtime = jtdxtime;\n  if (wrapped_) wrapped_->start (0,m_jtdxtime);\n',
    '  m_jtdxtime = jtdxtime;\n  stopping_ = false;\n  startup_complete_ = false;\n  reconnecting_ = false;\n  error_.clear();\n  if (wrapped_) wrapped_->start (0,m_jtdxtime);\n',
    'TCI do_start reconnect reset')

replace_once('TCITransceiver.cpp',
    '      connect(commander_,SIGNAL(error(QAbstractSocket::SocketError)),this,SLOT(onError(QAbstractSocket::SocketError)));\n',
    '      connect(commander_,SIGNAL(error(QAbstractSocket::SocketError)),this,SLOT(onError(QAbstractSocket::SocketError)));\n      connect(commander_, &QWebSocket::pong, this, &TCITransceiver::onPong);\n',
    'TCI WebSocket pong connection')

replace_once('TCITransceiver.cpp',
    '    if (stream_audio_) do_audio(true);\n\n    TRACE_CAT ("TCITransceiver", "started");\n',
    '''    if (stream_audio_) do_audio(true);

    if (!reconnect_timer_) {
      reconnect_timer_ = new QTimer {this};
      reconnect_timer_->setInterval(2000);
      connect(reconnect_timer_, &QTimer::timeout, this, &TCITransceiver::onReconnectTimer);
    }
    reconnect_clock_.start();
    last_ping_ms_ = 0;
    last_pong_ms_ = 0;
    startup_complete_ = true;
    reconnecting_ = false;
    reconnect_timer_->start();

    TRACE_CAT ("TCITransceiver", "started");
''',
    'TCI start reconnect watchdog')

replace_once('TCITransceiver.cpp',
    'void TCITransceiver::do_stop ()\n{\n//  printf ("TCI close\\n");\n  if (!commander_) return;\n',
    '''void TCITransceiver::do_stop ()
{
  stopping_ = true;
  startup_complete_ = false;
  reconnecting_ = false;
  if (reconnect_timer_) {
    reconnect_timer_->stop();
    delete reconnect_timer_;
    reconnect_timer_ = nullptr;
  }
//  printf ("TCI close\\n");
  if (!commander_) return;
''',
    'TCI stop disables reconnect')

replace_once('TCITransceiver.cpp',
    '  if (/*!inConnected && */!error_.isEmpty()) {tci_Ready = false; throw error {error_};}\n  else if (!tci_Ready) throw error {tr ("TCI could not be opened")};\n',
    '''  // During a temporary TCI outage keep the transceiver object alive.
  // The reconnect watchdog restores the socket; do not force the user to
  // reopen Settings | Radio.
  if (!inConnected || !tci_Ready) return;
  if (!error_.isEmpty()) {tci_Ready = false; throw error {error_};}
''',
    'TCI do_poll nonfatal outage')

replace_once('TCITransceiver.cpp',
    '        if (!inConnected && !error_.isEmpty()) throw error {error_};\n//        if (!inConnected){ PTT_ = on; update_PTT(on); return; }\n        else if (busy_PTT_ || !tci_Ready || !_power_) return;\n',
    '''        if (!inConnected || !tci_Ready || !_power_) {
          // Fail safe: a reconnect can never arm TX.
          requested_PTT_ = false;
          return;
        }
        else if (busy_PTT_) return;
''',
    'TCI PTT fail-safe during reconnect')

replace_once('TCITransceiver.cpp',
    '          _power_ = true;\n//          printf ("cmdstart done1\\n");\n          if (tci_Ready) tci_done1();\n',
    '''          _power_ = true;
          if (startup_complete_ && reconnecting_ && inConnected && !stopping_)
            QTimer::singleShot(250, this, SLOT(onReconnectReady()));
//          printf ("cmdstart done1\\n");
          if (tci_Ready) tci_done1();
''',
    'TCI Cmd_Start resumes reconnect')

replace_once('TCITransceiver.cpp',
    '''          _power_ = false;
          if (tci_timer1_->isActive()) { /*printf ("cmdstop done1\\n");*/ tci_done1();}
          else {
            tci_Ready = false;
          }
''',
    '''          _power_ = false;
          if (startup_complete_ && !stopping_) reconnecting_ = true;
          if (tci_timer1_->isActive()) { /*printf ("cmdstop done1\\n");*/ tci_done1();}
          else {
            tci_Ready = false;
          }
''',
    'TCI Cmd_Stop marks reconnecting')


# 8) Postchecks.
checks = {
    'commons.h': ['bool lsuperhound;'],
    'lib/jt9com.f90': ['logical(c_bool) :: lsuperhound'],
    'mainwindow.h': ['on_actionEnable_superhound_mode_toggled', 'm_superHoundMode', 'm_superHoundArmed', 'm_superHoundFoxCall'],
    'mainwindow.cpp': ['dec_data.params.lsuperhound', 'SuperHound RX active at 750 Hz', 'SuperHound armed for %1', 'integrated monitor at the bottom', 'embedded monitor has no separate closeEvent', '!m_superHoundMode && !m_config.split_mode()'],
    'mainwindow.ui': ['actionEnable_superhound_mode', 'Enable SuperHound mode'],
    'lib/jt9a.f90': ['call sfrx_sub_jtdx'],
    'CMakeLists.txt': ['wsjt_superhound_FSRCS', 'wsjt_superhound_CSRCS', 'JTDX_ENABLE_OMNIRIG', 'hamlib_bin_dir', 'CPACK_GENERATOR "WIX"'],
    'TransceiverFactory.cpp': ['defined (JTDX_ENABLE_OMNIRIG)'],
    'lib/superfox/sfrx_sub_jtdx.f90': ['call qpc_decode2', 'call sfox_unpack'],
    'lib/superfox/sfox_unpack.f90': ['use packjt, only : unpackgrid', 'unpack28(n28,foxcall,success,1)'],
    'CMake/Modules/FindFFTW3.cmake': ['Modern MSYS2/MinGW also ships separate FFTW thread import libraries.', 'if (_use_threads)'],
    'lib/jplsubs.f': ['SUBROUTINE JPL_SPLIT(TT,FR)', 'CALL JPL_SPLIT(S,PJD(1))'],
    'TCITransceiver.hpp': ['onReconnectTimer', 'QElapsedTimer reconnect_clock_', 'startup_complete_'],
    'TCITransceiver.cpp': ['TCI automatic reconnect complete', 'commander_->ping(QByteArray("JTDX-TCI"))', 'requested_rx_frequency_ != rx_frequency_', 'requested_split_ != split_', 'if (!inConnected || !tci_Ready) return;', 'if (!error_.isEmpty()) {tci_Ready = false; throw error {error_};}', 'Fail safe: a reconnect can never arm TX.'],
}
for rel, needles in checks.items():
    _, s = load(rel)
    for needle in needles:
        if needle not in s:
            raise SystemExit(f'[FAIL] postcheck {rel}: missing {needle!r}')
print('[PASS] all source postchecks')
