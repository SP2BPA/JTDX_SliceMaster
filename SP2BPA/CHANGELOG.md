# Changelog — SP2BPA JTDX Slice Master

## v0.3b Log4OM — W TRAKCIE TESTÓW — 2026-09-20

**Hotfix v0.3b:** pierwszy build v0.3a zatrzymał się na gate `git diff --check` z powodu istniejących wcześniej spacji końcowych w kilku liniach `logbook.cpp`, które stały się liniami zmodyfikowanymi po przełączeniu źródła Worked/New. Patcher v0.3b usuwa whitespace wyłącznie z tych linii; nie zmienia logiki programu.

- dodawane jest opcjonalne, bezpośrednie źródło historii QSO z bazy Log4OM 2 SQLite
- wybór pliku bazy ma być dostępny w `Ustawienia -> Zaawansowane -> Log4OM 2`
- funkcja jest domyślnie wyłączona, więc dotychczasowe zachowanie JTDX pozostaje bez zmian
- baza Log4OM jest otwierana wyłącznie do odczytu; JTDX nie zapisuje do niej żadnych danych
- przy braku bazy, błędzie otwarcia lub niezgodnej strukturze następuje automatyczny fallback do `wsjtx_log.adi`
- zachowana zostaje oryginalna logika JTDX dla New DXCC / New Call / Grid / Prefix / pasmo / emisja; zmienia się tylko źródło informacji o wykonanych QSO
- planowane jest automatyczne przeładowanie po zmianie pliku SQLite / pliku WAL
- do buildu dodawany jest QtSql oraz sterownik SQLite `qsqlite.dll`
- lokalny `wsjtx_log.adi` nadal obsługuje licznik QSO i lokalne dane JTDX; Log4OM jest osobnym źródłem Worked/New
- schemat potwierdzony na rzeczywistej bazie SP2BPA: 1543 QSO / 98 kolumn / 240 wartości DXCC
- bez zmian w FT8, FT2, SuperHound, dekoderze, CAT/PTT, WideGraph i integracji Slice Master

## v0.2 / v0.2a — 2026-09-19

- zachowano zaakceptowane GUI z v0.1
- utrzymano FT8, FT2 i SuperHound bez zmian funkcjonalnych
- przygotowano warstwę testową integracji Slice Master
- builder został dostosowany do MSYS2, WiX 3.14 i współczesnego środowiska Windows
- naprawiono problemy pierwszego buildu:
  - automatyczny preflight administrator/NetFx3/WiX
  - naprawa niepełnej instalacji Boost po przerwanym pacman
  - poprawka źródła SuperFox `lib/smo121.f90`
  - poprawki CPack/WiX
- poprawnie wygenerowano MSI:
  `JTDX-SuperHound-FT2-SliceMaster-2.2.159-v0.2-win64.msi`

### CAT — stan końcowy testów

Konfiguracja działająca:
- Rig: `FlexRadio 6xxx`
- Slice A: `127.0.0.1:7821`
- Slice B: `127.0.0.1:7822`
- PTT Method: `CAT`

HRD 7811/7812 pozostaje ścieżką eksperymentalną i nie jest używany w konfiguracji roboczej.

## v0.1 — 2026-09-18

- zbudowano JTDX 2.2.159 na bazie zmian SQ4KOU
- zachowano SuperHound i FT2
- WideGraph przeniesiono do prawego górnego pola głównego okna
- WideGraph pozostawiono jako jeden kompletny widget razem z kontrolkami i suwakami
- panel częstotliwości/sterowania przesunięto pod wodospad
- pozostałe elementy GUI oraz DSP pozostawiono bez zmian
- powstał pierwszy poprawnie działający instalator MSI
