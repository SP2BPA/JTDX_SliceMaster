# Builder SP2BPA

Ten katalog opisuje zweryfikowany zestaw buildera, który utworzył działający MSI v0.2.

## Zestaw źródłowy

Docelowo komplet zawiera:

- `BUILD_JTDX_SUPERHOUND_MSI.ps1`
- `BUILD_MSI.bat`
- `patch_superhound.py`
- `patch_ft2.py`
- `patch_slice_master.py`
- `PATCHER_SELFTEST_R12.py`
- `PATCHER_SELFTEST_SM_V02.py`
- `AUDIT_PROJECT_R12.py`
- pliki README/changelog/audytu

Plik `SHA256SUMS-v0.2a.txt` zapisuje dokładne sumy kontrolne lokalnego zestawu, z którego powstał działający MSI.

## Status patch_slice_master.py

Patch HRD reconnect z v0.2 jest zachowywany jako część historii eksperymentów. Aktualna konfiguracja robocza JTDX korzysta z `FlexRadio 6xxx` i portów CAT TCP 7821/7822, więc HRD reconnect nie jest wymagany do bieżącej pracy.

## Zasada

Nie dodajemy do Git:
- `_JTDX_SUPERHOUND_CACHE/`
- `WORK/`
- `OUTPUT/`
- `LOGS/`
- `__pycache__/`
- środowiska `C:\msys64`

Do repo trafiają źródła, patche, skrypty, dokumentacja i sumy kontrolne.
