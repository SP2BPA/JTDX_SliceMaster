$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Work = Join-Path $Here 'WORK'
$Out  = Join-Path $Here 'OUTPUT'
$LogDir = Join-Path $Here 'LOGS'
New-Item -ItemType Directory -Force -Path $Work,$Out,$LogDir | Out-Null
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Log = Join-Path $LogDir "JTDX_SUPERHOUND_MSI_$Stamp.log"

function Log([string]$s) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $s
    $line | Tee-Object -FilePath $Log -Append
}
function Run([scriptblock]$cmd, [string]$name) {
    Log "START $name"

    # Pacman and several GNU tools legitimately write warnings/progress to
    # STDERR even when they exit with code 0. With $ErrorActionPreference=Stop,
    # Windows PowerShell can turn such native STDERR records into terminating
    # NativeCommandError exceptions. That caused V5 to report harmless pacman
    # warnings (for example "git ... is up to date") as a failed install.
    # Native command success is therefore decided ONLY by its process exit code.
    $savedEap = $ErrorActionPreference
    $nativePrefExists = $null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue)
    if ($nativePrefExists) { $savedNativePref = $PSNativeCommandUseErrorActionPreference }

    try {
        $ErrorActionPreference = 'Continue'
        if ($nativePrefExists) { $PSNativeCommandUseErrorActionPreference = $false }
        $global:LASTEXITCODE = 0
        & $cmd 2>&1 | Tee-Object -FilePath $Log -Append
        $rc = $LASTEXITCODE
    }
    finally {
        if ($nativePrefExists) { $PSNativeCommandUseErrorActionPreference = $savedNativePref }
        $ErrorActionPreference = $savedEap
    }

    if ($rc -ne 0) { throw "$name failed, exit=$rc" }
    Log "PASS  $name"
}

try {
    Log 'JTDX SuperHound FT2 FINAL - START'

    $MsysShell = 'C:\msys64\msys2_shell.cmd'
    if (!(Test-Path $MsysShell)) {
        Log 'MSYS2 not found - installing with winget'
        Run { winget install --id MSYS2.MSYS2 -e --accept-package-agreements --accept-source-agreements --silent } 'Install MSYS2'
    }
    if (!(Test-Path $MsysShell)) { throw 'MSYS2 installation not found at C:\msys64' }

    # V7: never pass complex Bash code through msys2_shell.cmd -c.
    # Windows cmd.exe parses shell metacharacters before Bash receives them.
    $BashExe    = 'C:\msys64\usr\bin\bash.exe'
    $PacmanExe  = 'C:\msys64\usr\bin\pacman.exe'
    $TimeoutExe = 'C:\msys64\usr\bin\timeout.exe'
    $CygpathExe = 'C:\msys64\usr\bin\cygpath.exe'
    foreach($p in @($BashExe,$PacmanExe,$TimeoutExe,$CygpathExe)) {
        if(!(Test-Path $p)) { throw "Required MSYS2 executable missing: $p" }
    }

    $env:MSYSTEM='MINGW64'
    $env:CHERE_INVOKING='1'
    $env:MSYS2_PATH_TYPE='inherit'

    function To-MsysPath([string]$WindowsPath) {
        $savedEap = $ErrorActionPreference
        try {
            $ErrorActionPreference='Continue'
            $r = & $CygpathExe -u $WindowsPath 2>&1
            $rc = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference=$savedEap
        }
        if($rc -ne 0) { throw "cygpath failed for: $WindowsPath" }
        $line = @($r | ForEach-Object { "$_" }) | Select-Object -First 1
        if([string]::IsNullOrWhiteSpace($line)) { throw "cygpath returned empty path for: $WindowsPath" }
        return $line.Trim()
    }

    $wixCandidates = @(
        'C:\Program Files (x86)\WiX Toolset v3.14\bin',
        'C:\Program Files\WiX Toolset v3.14\bin'
    )
    $WixBin = $wixCandidates | Where-Object { Test-Path (Join-Path $_ 'candle.exe') } | Select-Object -First 1
    if (!$WixBin) {
        Log 'WiX 3.14 not found - installing with winget'
        Run { winget install --id WiXToolset.WiXToolset -e --accept-package-agreements --accept-source-agreements --silent } 'Install WiX 3.14'
        $WixBin = $wixCandidates | Where-Object { Test-Path (Join-Path $_ 'candle.exe') } | Select-Object -First 1
    }
    if (!$WixBin) { throw 'WiX candle.exe not found after installation' }
    $env:PATH = "$WixBin;$env:PATH"
    Log "WiX: $WixBin"

    # Recover automatically from an interrupted previous build. pacman keeps
    # /var/lib/pacman/db.lck while it owns the package database. A Ctrl+C in
    # the outer PowerShell/cmd can leave pacman.exe alive or leave a stale
    # lock behind. Never delete the lock while a live pacman process exists.
    function Ensure-PacmanReady {
        $pacmanLock = 'C:\msys64\var\lib\pacman\db.lck'
        $running = @(Get-Process -Name 'pacman' -ErrorAction SilentlyContinue)
        if ($running.Count -gt 0) {
            Log "Found existing pacman process(es): $($running.Id -join ', ') - waiting up to 30 s"
            $deadline = (Get-Date).AddSeconds(30)
            do {
                Start-Sleep -Seconds 1
                $running = @(Get-Process -Name 'pacman' -ErrorAction SilentlyContinue)
            } while ($running.Count -gt 0 -and (Get-Date) -lt $deadline)

            if ($running.Count -gt 0) {
                Log "Previous pacman still blocks MSYS2 - terminating orphaned process(es): $($running.Id -join ', ')"
                $running | Stop-Process -Force -ErrorAction Stop
                Start-Sleep -Seconds 2
            }
        }

        $running = @(Get-Process -Name 'pacman' -ErrorAction SilentlyContinue)
        if ($running.Count -gt 0) {
            throw "pacman.exe is still running; refusing to remove package database lock"
        }

        if (Test-Path $pacmanLock) {
            Log "Removing stale pacman database lock: $pacmanLock"
            Remove-Item -Force $pacmanLock
        }
    }

    # Hamlib is intentionally NOT requested from pacman. Current MSYS2 mingw64
    # does not provide mingw-w64-x86_64-hamlib; the JTDX fork is built below.
    # Install only concrete packages: no interactive pacman groups.
    $depPackages = @(
      'git','python','autoconf','automake','libtool','make','pkgconf','texinfo','gettext-devel','patch','diffutils',
      'mingw-w64-x86_64-gcc','mingw-w64-x86_64-gcc-fortran','mingw-w64-x86_64-cmake','mingw-w64-x86_64-ninja',
      'mingw-w64-x86_64-boost','mingw-w64-x86_64-fftw','mingw-w64-x86_64-libusb',
      'mingw-w64-x86_64-qt5-base','mingw-w64-x86_64-qt5-tools','mingw-w64-x86_64-qt5-multimedia',
      'mingw-w64-x86_64-qt5-websockets','mingw-w64-x86_64-qt5-serialport','mingw-w64-x86_64-qt5-activeqt'
    )

    # Fast local package gate. If V6 already installed everything, skip all
    # repository synchronization and go directly to the actual source build.
    $savedEap=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        & $PacmanExe -Q @depPackages *> $null
        $pkgGateRc=$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference=$savedEap
    }

    if($pkgGateRc -eq 0) {
        Log 'PASS  Required MSYS2 packages already installed - repository sync skipped'
    }
    else {
        Ensure-PacmanReady

        $PacmanConf = 'C:\msys64\etc\pacman-superhound.conf'
        function Write-SuperHoundPacmanConfig([string]$MingwServer, [string]$MsysServer, [string]$Label) {
            $cfg = @(
                '[options]',
                'Architecture = auto',
                'CheckSpace',
                'SigLevel = Required DatabaseOptional',
                'LocalFileSigLevel = Optional',
                'ParallelDownloads = 5',
                '',
                '[mingw64]',
                "Server = $MingwServer",
                '',
                '[msys]',
                "Server = $MsysServer",
                ''
            ) -join "`r`n"
            [IO.File]::WriteAllText($PacmanConf, $cfg, (New-Object Text.ASCIIEncoding))
            Log "pacman repository profile: $Label (mingw64 + msys only)"
        }

        $repoProfiles = @(
            @{
                Label = 'MSYS2 primary repo.msys2.org'
                Mingw = 'https://repo.msys2.org/mingw/$repo/'
                Msys  = 'https://repo.msys2.org/msys/$arch/'
            },
            @{
                Label = 'MSYS2 Tier-1 NLUUG fallback'
                Mingw = 'https://ftp.nluug.nl/pub/os/windows/msys2/builds/mingw/$repo/'
                Msys  = 'https://ftp.nluug.nl/pub/os/windows/msys2/builds/msys/$arch/'
            }
        )

        $depsInstalled=$false
        for($attempt=1; $attempt -le $repoProfiles.Count; $attempt++) {
            $profile=$repoProfiles[$attempt-1]
            try {
                Ensure-PacmanReady
                Write-SuperHoundPacmanConfig $profile.Mingw $profile.Msys $profile.Label

                # Invoke GNU timeout + pacman directly. No cmd.exe, no -c quoting layer.
                $pacmanArgs = @(
                    '--foreground','--signal=TERM','180s',
                    '/usr/bin/pacman','--config','/etc/pacman-superhound.conf',
                    '-Sy','--needed','--noconfirm'
                ) + $depPackages

                Run { & $TimeoutExe @pacmanArgs } "Install/update MSYS2 build dependencies (attempt $attempt)"
                $depsInstalled=$true
                break
            }
            catch {
                Ensure-PacmanReady
                Log "Dependency installation attempt $attempt failed/timed out: $($_.Exception.Message)"
                if($attempt -lt $repoProfiles.Count) {
                    Log 'Switching pacman to the next official mirror'
                    Start-Sleep -Seconds 2
                }
                else {
                    throw
                }
            }
        }
        if(!$depsInstalled) { throw 'MSYS2 dependency installation did not complete' }
    }

    # Hard dependency gate as a real Bash file. This removes the exact V6 failure:
    # cmd.exe no longer sees Bash redirections such as >/dev/null 2>&1.
    $ToolGateWin = Join-Path $Work 'verify_msys2_tools.sh'
    $toolGateScript = @'
#!/usr/bin/env bash
set -euo pipefail
export PATH="/mingw64/bin:/usr/bin:$PATH"
for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5; do
  if ! command -v "$t" >/dev/null 2>&1; then
    echo "[FAIL] missing tool: $t"
    exit 91
  fi
done
if [ ! -x /usr/bin/python3 ]; then
  echo "[FAIL] missing MSYS Python: /usr/bin/python3"
  exit 92
fi
/usr/bin/python3 -c 'import encodings,sys; print("[PASS] MSYS Python:",sys.executable)'
echo "[PASS] MSYS2 tool gate"
gcc --version | head -n 1
gfortran --version | head -n 1
cmake --version | head -n 1
qmake-qt5 --version | head -n 2
'@
    $toolGateScript = $toolGateScript -replace "`r`n","`n"
    [IO.File]::WriteAllText($ToolGateWin,$toolGateScript,(New-Object Text.UTF8Encoding($false)))
    $ToolGateMsys = To-MsysPath $ToolGateWin
    Run { & $BashExe --login $ToolGateMsys } 'Verify MSYS2 build tools'

    $env:SH_WORK_WIN = $Work
    $env:SH_HERE_WIN = $Here
    $env:SH_OUT_WIN = $Out
    $env:SH_WIX_WIN = $WixBin

    $bash = @'
set -euo pipefail
# R9: one source of truth for all WiX/CPack version checks.
# Exported so the quoted Python heredoc and shell gates read the same values.
MSI_VERSION='2.2.199'
MSI_NAME='JTDX-SuperHound-2.2.159-SQ4KOU-FINAL-win64'
export MSI_VERSION MSI_NAME
export PATH="/mingw64/bin:/usr/bin:$PATH"
# Current MSYS2 Qt5 packages version their helper executables (qmake-qt5,
# lrelease-qt5, ...).  Older JTDX/CMake logic may still look for the
# historical generic names, so create private aliases only inside WORK/bin.
WORK="$(cygpath -u "$SH_WORK_WIN")"
mkdir -p "$WORK/bin"
ln -sf /mingw64/bin/qmake-qt5.exe "$WORK/bin/qmake.exe"
ln -sf /mingw64/bin/lrelease-qt5.exe "$WORK/bin/lrelease.exe"
ln -sf /mingw64/bin/lupdate-qt5.exe "$WORK/bin/lupdate.exe"
ln -sf /mingw64/bin/windeployqt-qt5.exe "$WORK/bin/windeployqt.exe"
export PATH="$WORK/bin:$PATH"
HERE="$(cygpath -u "$SH_HERE_WIN")"
OUT="$(cygpath -u "$SH_OUT_WIN")"
WIX="$(cygpath -u "$SH_WIX_WIN")"
export PATH="$WIX:$PATH"
mkdir -p "$WORK" "$OUT"
cd "$WORK"

echo '[INFO] build tool versions'
gcc --version | head -n 1
gfortran --version | head -n 1
cmake --version | head -n 1
qmake-qt5 --version | head -n 2

# WiX accepts the CPack license source only as .txt or .rtf.  Upstream JTDX
# points CPACK_RESOURCE_FILE_LICENSE at extensionless COPYING (fine for NSIS,
# rejected by WiX).  Prepare a .txt copy and patch the generated CPack files
# in-place.  Also pin a stable UpgradeCode for repeatable installs/upgrades.
prepare_wix_license() {
  : "${MSI_VERSION:?internal error: MSI_VERSION is not set}"
  : "${MSI_NAME:?internal error: MSI_NAME is not set}"
  local src="$1"
  local bld="$2"
  local lic="$src/COPYING.txt"
  local lic_win
  local projcfg
  [ -f "$src/COPYING" ] || { echo '[FAIL] JTDX COPYING license source missing'; return 61; }
  cp -f "$src/COPYING" "$lic"
  lic_win="$(cygpath -m "$lic")"
  projcfg="$(find "$bld" -maxdepth 2 -type f -name 'CMakeCPackOptions.cmake' -print -quit)"
  [ -n "$projcfg" ] || { echo '[FAIL] generated CMakeCPackOptions.cmake not found'; return 62; }
  [ -f "$bld/CPackConfig.cmake" ] || { echo '[FAIL] CPackConfig.cmake not found'; return 63; }
  env -u PYTHONHOME -u PYTHONPATH /usr/bin/python3 - "$projcfg" "$bld/CPackConfig.cmake" "$lic_win" <<'PYWIX'
from pathlib import Path
import os,re,sys
proj=Path(sys.argv[1])
cfg=Path(sys.argv[2])
lic=sys.argv[3].replace('\\','/')
guid='06176685-11E3-571C-9A05-5DC2E4640B2B'
msi_version=os.environ['MSI_VERSION']
msi_name=os.environ['MSI_NAME']
msi_patch=msi_version.rsplit('.',1)[1]

def patch(p):
    s=p.read_text(encoding='utf-8')
    # Handle both `set (...)` and `set(...)` generated CMake syntax.
    s2,n=re.subn(r'set\s*\(CPACK_RESOURCE_FILE_LICENSE\s+"[^"]*"\)',
                 f'set (CPACK_RESOURCE_FILE_LICENSE "{lic}")',s)
    if n < 1:
        s2 += f'\nset (CPACK_RESOURCE_FILE_LICENSE "{lic}")\n'
    # Ensure a stable WiX UpgradeCode; replace if already present, append otherwise.
    pat=r'set\s*\(CPACK_WIX_UPGRADE_GUID\s+"[^"]*"\)'
    if re.search(pat,s2):
        s2=re.sub(pat,f'set (CPACK_WIX_UPGRADE_GUID "{guid}")',s2)
    else:
        s2 += f'\nset (CPACK_WIX_UPGRADE_GUID "{guid}")\n'
    # Use a package version higher than the already-installed V15 MSI so
    # Windows Installer performs an in-place upgrade instead of keeping V15.
    for var,val in [('CPACK_PACKAGE_VERSION',msi_version),
                    ('CPACK_PACKAGE_VERSION_MAJOR','2'),
                    ('CPACK_PACKAGE_VERSION_MINOR','2'),
                    ('CPACK_PACKAGE_VERSION_PATCH',msi_patch),
                    ('CPACK_PACKAGE_FILE_NAME',msi_name)]:
        pat=rf'set\s*\({var}\s+"?[^\)\"]+"?\)'
        if re.search(pat,s2):
            s2=re.sub(pat,f'set ({var} "{val}")',s2)
        else:
            s2 += f'\nset ({var} "{val}")\n'
    p.write_text(s2,encoding='utf-8',newline='\n')

patch(proj)
patch(cfg)
print(f'[PASS] WiX license source fixed: {lic}')
print(f'[PASS] WiX UpgradeCode pinned: {guid}')
print(f'[PASS] MSI upgrade version: {msi_version} / {msi_name}')
PYWIX
  grep -Fq 'COPYING.txt' "$projcfg"
  grep -Fq 'COPYING.txt' "$bld/CPackConfig.cmake"
  grep -Fq "$MSI_VERSION" "$projcfg"
  grep -Fq "$MSI_VERSION" "$bld/CPackConfig.cmake"
  grep -Fq "$MSI_NAME" "$projcfg"
  grep -Fq "$MSI_NAME" "$bld/CPackConfig.cmake"
  echo "[PASS] WiX CPack license/version gates: $MSI_VERSION / $MSI_NAME"
}

# R12 CLEAN: never compile the cumulative dirty R2-R9 source/build tree.
PARENT="$(dirname "$HERE")"
WSJTX_REF="332e48c9f7910058b56c35e237027f11a21d56e6"
echo '[CLEAN] R12: using pinned clean source; V11 is source/dependency cache only'
echo '[CLEAN] full rebuild from reset --hard pinned JTDX source'
env -u PYTHONHOME -u PYTHONPATH /usr/bin/python3 "$HERE/PATCHER_SELFTEST_R12.py"
grep -Fq 'SQ4KOU FT2: per-row saved-table migration' "$HERE/patch_ft2.py"
grep -Fq 'SQ4KOU FT2: per-row saved-table migration' "$HERE/AUDIT_PROJECT_R12.py"
echo '[PASS] R12 semantic audit markers synchronized'

# Build the JTDX Hamlib fork from source only once. V16 uses a persistent
# sibling cache and imports a verified prefix from V15..V1 when available.
# This prevents another long Hamlib rebuild on every ONECLICK revision.
PARENT="$(dirname "$HERE")"
CACHE_ROOT="$PARENT/_JTDX_SUPERHOUND_CACHE"
WSJTX_CACHE="$CACHE_ROOT/wsjtx-superfox"
HAMLIB_PREFIX="$CACHE_ROOT/hamlib-prefix"
mkdir -p "$CACHE_ROOT"
valid_hamlib_prefix() {
  local p="$1"
  [ -f "$p/include/hamlib/rig.h" ] &&   [ -f "$p/lib/libhamlib.dll.a" ] &&   compgen -G "$p/bin/libhamlib*.dll" >/dev/null
}

if ! valid_hamlib_prefix "$HAMLIB_PREFIX"; then
  for v in 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1; do
    candidate="$PARENT/JTDX_SUPERHOUND_MSI_V${v}/WORK/hamlib-prefix"
    [ -d "$candidate" ] || continue
    if valid_hamlib_prefix "$candidate"; then
      echo "[INFO] importing verified Hamlib cache from: $candidate"
      rm -rf "$HAMLIB_PREFIX"
      cp -a "$candidate" "$HAMLIB_PREFIX"
      break
    fi
  done
fi

if valid_hamlib_prefix "$HAMLIB_PREFIX"; then
  echo '[PASS] JTDX Hamlib persistent cache ready'
else
  if [ ! -d hamlib-src/.git ]; then
    echo '[INFO] cloning JTDX Hamlib'
    if ! git clone https://github.com/jtdx-project/jtdxhamlib.git hamlib-src; then
      echo '[WARN] GitHub Hamlib clone failed; using JTDX SourceForge'
      git clone https://git.code.sf.net/p/jtdx/hamlib hamlib-src
    fi
  fi

  echo '[INFO] refreshing/pinning JTDX Hamlib source'
  git -C hamlib-src fetch --all --prune || true
  git -C hamlib-src checkout 1e70dd7b98fd715c829724313eb88884ca1cbfc1
  git -C hamlib-src reset --hard 1e70dd7b98fd715c829724313eb88884ca1cbfc1
  git -C hamlib-src clean -fdx
  echo '[PASS] Hamlib pinned at 1e70dd7b98fd715c829724313eb88884ca1cbfc1'

  rm -rf hamlib-build "$HAMLIB_PREFIX"
  mkdir -p hamlib-build "$HAMLIB_PREFIX"
  (
    cd hamlib-src
    ./bootstrap
  )
  (
    cd hamlib-build
    PKG_CONFIG_PATH=/mingw64/lib/pkgconfig ../hamlib-src/configure \
      --prefix="$HAMLIB_PREFIX" \
      --disable-static --enable-shared \
      --without-readline --without-indi --without-cxx-binding --disable-winradio \
      CC=gcc CXX=g++ \
      CFLAGS="-O2 -fdata-sections -ffunction-sections" \
      LDFLAGS="-Wl,--gc-sections"
    make -j"$(nproc)"
    make install-strip || make install
  )

  if ! valid_hamlib_prefix "$HAMLIB_PREFIX"; then
    echo '[FAIL] JTDX Hamlib prefix postcheck failed'
    find "$HAMLIB_PREFIX" -maxdepth 3 -type f | sort | tail -n 100
    exit 31
  fi
  echo '[PASS] JTDX Hamlib built from source'
fi
export PATH="$HAMLIB_PREFIX/bin:/mingw64/bin:/usr/bin:$PATH"

if [ ! -d jtdx/.git ]; then
  for v in 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1; do
    oldrepo="$PARENT/JTDX_SUPERHOUND_MSI_V${v}/WORK/jtdx"
    [ -d "$oldrepo/.git" ] || continue
    echo "[INFO] reusing JTDX clone from: $oldrepo"
    cp -a "$oldrepo" jtdx
    break
  done
fi
if [ ! -d jtdx/.git ]; then
  echo '[INFO] cloning JTDX'
  if ! git clone https://github.com/jtdx-project/jtdx.git jtdx; then
    echo '[WARN] GitHub JTDX clone failed; using JTDX SourceForge'
    git clone https://git.code.sf.net/p/jtdx/code jtdx
  fi
fi

echo '[INFO] resetting/pinning JTDX to 2.2.159 source'
git -C jtdx fetch --all --prune || true
git -C jtdx checkout 2a0e2bea8c66c9ca94d2ea8034cf83a68cfa40eb
git -C jtdx reset --hard 2a0e2bea8c66c9ca94d2ea8034cf83a68cfa40eb
git -C jtdx clean -fdx
if [ -n "$(git -C jtdx status --porcelain --untracked-files=no)" ]; then
  echo '[FAIL] clean-source baseline is not clean after reset --hard/clean'
  git -C jtdx status --short
  exit 75
fi
echo '[PASS] clean-source baseline has zero tracked modifications'
echo '[PASS] JTDX pinned at 2a0e2bea8c66c9ca94d2ea8034cf83a68cfa40eb'

echo "[CLEAN] importing pinned SuperFox source overlay from WSJT-X $WSJTX_REF"
if [ ! -d "$WSJTX_CACHE/.git" ]; then
  rm -rf "$WSJTX_CACHE"
  git clone https://github.com/kholia/wsjtx.git "$WSJTX_CACHE"
fi
git -C "$WSJTX_CACHE" fetch --all --prune || true
git -C "$WSJTX_CACHE" checkout "$WSJTX_REF"
git -C "$WSJTX_CACHE" reset --hard "$WSJTX_REF"
git -C "$WSJTX_CACHE" clean -fdx
rm -rf jtdx/lib/superfox
cp -a "$WSJTX_CACHE/lib/superfox" jtdx/lib/superfox
test -s jtdx/lib/superfox/smo121.f90
echo "[PASS] SuperFox source pinned at $WSJTX_REF"
echo '[INFO] applying SuperHound source patch with /usr/bin/python3'
env -u PYTHONHOME -u PYTHONPATH /usr/bin/python3 "$HERE/patch_superhound.py" "$WORK/jtdx"
echo '[INFO] applying FT2 integration patch'
env -u PYTHONHOME -u PYTHONPATH /usr/bin/python3 "$HERE/patch_ft2.py" "$WORK/jtdx"
env -u PYTHONHOME -u PYTHONPATH /usr/bin/python3 "$HERE/AUDIT_PROJECT_R12.py" "$WORK/jtdx"

# R12 project-wide patch surface audit.
git -C jtdx diff --check
allowed_re='^(CMake/Modules/FindFFTW3\.cmake|CMakeLists\.txt|Configuration\.cpp|FrequencyList\.cpp|Modes\.cpp|Modes\.hpp|Modulator\.cpp|TCITransceiver\.cpp|TCITransceiver\.hpp|TransceiverFactory\.cpp|commons\.h|eqsl\.cpp|lib/decoder\.f90|lib/ft4_mod1\.f90|lib/jplsubs\.f|lib/jt9a\.f90|lib/jt9com\.f90|logbook/adif\.cpp|logqso\.cpp|mainwindow\.cpp|mainwindow\.h|mainwindow\.ui|plotter\.cpp)$'
unexpected="$(git -C jtdx diff --name-only | grep -Ev "$allowed_re" || true)"
if [ -n "$unexpected" ]; then
  echo '[FAIL] R12 unexpected tracked source modifications:'
  printf '%s\n' "$unexpected"
  exit 76
fi
echo '[PASS] R12 project-wide patch surface audit'

# Explicit source postchecks before wasting time on compilation.
grep -q 'bool lsuperhound;' jtdx/commons.h
grep -q 'logical(c_bool) :: lsuperhound' jtdx/lib/jt9com.f90
grep -q 'call sfrx_sub_jtdx' jtdx/lib/jt9a.f90
grep -q 'lib/superfox/smo121.f90' jtdx/CMakeLists.txt
test -s jtdx/lib/superfox/smo121.f90
grep -q 'CPACK_GENERATOR "WIX"' jtdx/CMakeLists.txt
grep -q 'JTDX_ENABLE_OMNIRIG' jtdx/CMakeLists.txt
grep -q 'defined (JTDX_ENABLE_OMNIRIG)' jtdx/TransceiverFactory.cpp
grep -Fq 'SUBROUTINE JPL_SPLIT(TT,FR)' jtdx/lib/jplsubs.f
grep -Fq 'CALL JPL_SPLIT(S,PJD(1))' jtdx/lib/jplsubs.f
grep -Fq 'use packjt, only : unpackgrid' jtdx/lib/superfox/sfox_unpack.f90
grep -Fq 'Modern MSYS2/MinGW also ships separate FFTW thread import libraries.' jtdx/CMake/Modules/FindFFTW3.cmake
grep -Fq 'm_superHoundArmed' jtdx/mainwindow.h
grep -Fq 'validSuperFoxTarget' jtdx/mainwindow.cpp
grep -Fq 'SuperHound armed for %1' jtdx/mainwindow.cpp
grep -Fq 'integrated monitor at the bottom' jtdx/mainwindow.cpp
grep -Fq 'QSplitter *integratedMonitorSplitter' jtdx/mainwindow.cpp
grep -Fq 'embedded monitor has no separate closeEvent' jtdx/mainwindow.cpp
grep -Fq 'void onReconnectTimer();' jtdx/TCITransceiver.hpp
grep -Fq 'QElapsedTimer reconnect_clock_' jtdx/TCITransceiver.hpp
grep -Fq 'TCI automatic reconnect complete' jtdx/TCITransceiver.cpp
grep -Fq 'commander_->ping(QByteArray("JTDX-TCI"))' jtdx/TCITransceiver.cpp
grep -Fq 'requested_rx_frequency_ != rx_frequency_' jtdx/TCITransceiver.cpp
grep -Fq 'requested_split_ != split_' jtdx/TCITransceiver.cpp
grep -Fq 'Fail safe: a reconnect can never arm TX.' jtdx/TCITransceiver.cpp
grep -Fq 'void on_actionFT2_triggered();' jtdx/mainwindow.h
grep -Fq 'm_TRperiod=3.75' jtdx/mainwindow.cpp
grep -Fq 'dec_data.params.nmode=52' jtdx/mainwindow.cpp
grep -Fq 'call my_ft4%decode(ft2_decoded' jtdx/lib/decoder.f90
grep -Fq 'npts1=39744' jtdx/lib/jt9a.f90
grep -Fq 'dd2raw(1:npts1)=dd(1:npts1)' jtdx/lib/jt9a.f90
grep -Fq 'dd2raw(39744)' jtdx/lib/ft4_mod1.f90
grep -Fq 'ft2_start=2881' jtdx/lib/decoder.f90
grep -Fq 'ft2_offset_sec=0.24' jtdx/lib/decoder.f90
grep -Fq 'dt_ft2=0.5*dt - 0.25 + ft2_offset_sec' jtdx/lib/decoder.f90
grep -Fq 'm_nsps==288' jtdx/Modulator.cpp
grep -Fq 'delay_ms=150' jtdx/Modulator.cpp
grep -Fq 'm_nsps==288' jtdx/TCITransceiver.cpp
grep -Fq 'delay_ms=150' jtdx/TCITransceiver.cpp
grep -Fq 'return m_->frequency_list (frequency_list);' jtdx/FrequencyList.cpp
if grep -Fq 'bool have_ft2=false;' jtdx/FrequencyList.cpp; then
  echo '[FAIL] R7: obsolete R3-R5 FrequencyList setter mutation is still present'
  exit 73
fi
grep -Fq 'SQ4KOU FT2: per-row saved-table migration' jtdx/Configuration.cpp
grep -Fq 'frequency_list_merge (missing_ft2_frequency_rows)' jtdx/Configuration.cpp
grep -Fq 'best_working_frequency (current_band)' jtdx/mainwindow.cpp
grep -Fq 'old_fast_mode != new_fast_mode' jtdx/mainwindow.cpp
grep -Fq 'else if(m_mode=="FT2") TRperiod=3.75' jtdx/mainwindow.cpp

echo '[PASS] PATCH/ABI/CPACK/GFORTRAN/SUPERFOX/FFTW/FUNCTIONAL/MONITOR/TCI/FT2 source gates'

# JTDX 2.2.159 uses its own LibFindMacros-based FindHamlib module. With modern
# CMake/MSYS2, CMAKE_PREFIX_PATH alone is insufficient for this old module.
# Feed the exact verified header/import-library paths and pkg-config prefix.
HAMLIB_PREFIX_WIN="$(cygpath -m "$HAMLIB_PREFIX")"
export PKG_CONFIG_PATH="$HAMLIB_PREFIX/lib/pkgconfig:/mingw64/lib/pkgconfig"
test -f "$HAMLIB_PREFIX/include/hamlib/rig.h"
test -f "$HAMLIB_PREFIX/lib/libhamlib.dll.a"
echo "[PASS] Hamlib include: $HAMLIB_PREFIX/include/hamlib/rig.h"
echo "[PASS] Hamlib import lib: $HAMLIB_PREFIX/lib/libhamlib.dll.a"

FFTW_THREADS_LIB="$(find /mingw64/lib -maxdepth 1 -type f \
  \( -name 'libfftw3f_threads.dll.a' -o -name 'libfftw3f_threads.a' \) | head -n 1)"
if [ -z "$FFTW_THREADS_LIB" ]; then
  echo '[FAIL] MSYS2 FFTW single-precision threads library not found'
  ls -1 /mingw64/lib/libfftw3f* 2>/dev/null || true
  exit 36
fi
FFTW_THREADS_LIB_WIN="$(cygpath -m "$FFTW_THREADS_LIB")"
echo "[PASS] FFTW threads import lib: $FFTW_THREADS_LIB"

rm -rf jtdx/build-superhound
cmake -S jtdx -B jtdx/build-superhound -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DWSJT_GENERATE_DOCS=OFF \
  -DWSJT_BUILD_UTILS=OFF \
  -DJTDX_ENABLE_OMNIRIG=OFF \
  -DPYTHON_EXECUTABLE=/usr/bin/python3 \
  -DPython_EXECUTABLE=/usr/bin/python3 \
  -DPython3_EXECUTABLE=/usr/bin/python3 \
  -DCMAKE_Fortran_FLAGS="-fallow-argument-mismatch" \
  -DCMAKE_PREFIX_PATH="$HAMLIB_PREFIX_WIN;C:/msys64/mingw64" \
  -DHamlib_INCLUDE_DIR="$HAMLIB_PREFIX_WIN/include" \
  -DHamlib_LIBRARY="$HAMLIB_PREFIX_WIN/lib/libhamlib.dll.a" \
  -DFFTW3F_THREADS_LIBRARY="$FFTW_THREADS_LIB_WIN"

# Hard configure gate for the exact private Hamlib selected above.
grep -Fq "Hamlib_INCLUDE_DIR:PATH=$HAMLIB_PREFIX_WIN/include" jtdx/build-superhound/CMakeCache.txt || {
  echo '[FAIL] CMake did not retain the explicit Hamlib include path'
  grep -E '^Hamlib_(INCLUDE_DIR|LIBRARY)' jtdx/build-superhound/CMakeCache.txt || true
  exit 34
}
grep -Fq "Hamlib_LIBRARY:FILEPATH=$HAMLIB_PREFIX_WIN/lib/libhamlib.dll.a" jtdx/build-superhound/CMakeCache.txt || {
  echo '[FAIL] CMake did not retain the explicit Hamlib import library'
  grep -E '^Hamlib_(INCLUDE_DIR|LIBRARY)' jtdx/build-superhound/CMakeCache.txt || true
  exit 35
}
echo '[PASS] CMake Hamlib discovery gate'
grep -Fq 'fftw3f_threads' jtdx/build-superhound/build.ninja || {
  echo '[FAIL] CMake/Ninja did not retain FFTW threads link library'
  grep -E '^FFTW3F(_THREADS)?_LIBRARY' jtdx/build-superhound/CMakeCache.txt || true
  exit 37
}
echo '[PASS] CMake FFTW threads link gate'

cmake --build jtdx/build-superhound --parallel
env -u PYTHONHOME -u PYTHONPATH /usr/bin/python3 "$HERE/AUDIT_PROJECT_R12.py" "$WORK/jtdx"

prepare_wix_license "$WORK/jtdx" "$WORK/jtdx/build-superhound"
echo '[INFO] WiX package configuration verified; starting CPack'
cd jtdx/build-superhound
cpack -G WIX --config CPackConfig.cmake

MSI="$(find . -maxdepth 2 -type f -iname 'JTDX-SuperHound*.msi' | head -n 1)"
if [ -z "$MSI" ]; then
  echo '[FAIL] MSI not produced'
  find . -maxdepth 2 -type f | sort | tail -n 100
  exit 40
fi
cp -f "$MSI" "$OUT/"
echo "[PASS] MSI=$MSI"
ls -lh "$OUT"/*.msi
'@

    $BashFile = Join-Path $Work 'build_superhound.sh'
    $bash = $bash -replace "`r`n","`n"
    [IO.File]::WriteAllText($BashFile, $bash, (New-Object Text.UTF8Encoding($false)))
    $env:SH_BASH_WIN = $BashFile
    $BashFileMsys = To-MsysPath $BashFile
    Run { & $BashExe --login $BashFileMsys } 'Patch + compile + MSI package'

    $msi = Get-ChildItem $Out -Filter 'JTDX-SuperHound*.msi' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (!$msi) { throw 'Final MSI postcheck failed: no MSI in OUTPUT' }
    if ($msi.Length -lt 1MB) { throw "Final MSI suspiciously small: $($msi.Length) bytes" }
    $hash = (Get-FileHash $msi.FullName -Algorithm SHA256).Hash
    Log "PASS MSI: $($msi.FullName)"
    Log "SIZE: $($msi.Length) bytes"
    Log "SHA256: $hash"
    Log 'JTDX SuperHound FT2 FINAL - SUCCESS'
    Write-Host "`nSUCCESS: $($msi.FullName)" -ForegroundColor Green
    Write-Host "SHA256 : $hash" -ForegroundColor Green
}
catch {
    Log "FAIL: $($_.Exception.Message)"
    Write-Host "`nBUILD FAILED - see log: $Log" -ForegroundColor Red
    throw
}
