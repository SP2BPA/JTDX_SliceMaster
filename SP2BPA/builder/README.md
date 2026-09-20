# Builder SP2BPA

## Aktualny stan

Zweryfikowany build: **v0.3h Log4OM**.

Builder wygenerował na stacji SP2BPA poprawny instalator:

`JTDX-SuperHound-FT2-SliceMaster-2.2.159-v0.3h-Log4OM-win64.msi`

Weryfikacja obejmowała:
- pełną kompilację JTDX,
- FT8 / FT2 / SuperHound,
- QtSql,
- wyłącznie wymagany plugin `qsqlite.dll`,
- odrzucenie nieużywanego Firebird `qsqlibase/fbclient`,
- WiX/CPack,
- instalację i uruchomienie na stacji,
- CAT/audio,
- odczyt Log4OM SQLite dla Worked/New,
- fallback do `wsjtx_log.adi`.

## Środowisko

- Windows x64
- MSYS2 / MinGW-w64
- GCC/GFortran
- Qt 5
- Boost / FFTW
- Hamlib
- CMake / Ninja
- WiX Toolset 3.14

## Zasada repozytorium

Do Git nie trafiają:
- `_JTDX_SUPERHOUND_CACHE/`
- `WORK/`
- `OUTPUT/`
- `LOGS/`
- `__pycache__/`
- `C:\msys64`

Cache i środowisko kompilacji pozostają lokalne. Dokumentacja buildu i manifest końcowego wydania pozostają w repo.
