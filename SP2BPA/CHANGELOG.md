# Changelog — SP2BPA JTDX Slice Master

## v0.3g Log4OM — W TRAKCIE TESTÓW — 2026-09-20

**Hotfix v0.3g:** pełny build v0.3f doszedł do **1213/1219**. Jedyny twardy błąd był w `Configuration.cpp`: wygenerowana klasa UI nie zawierała `label_11`, którego upstream JTDX używa do obrazu `decpasses.png`. Patcher Log4OM zastąpił cały prawy layout zakładki Advanced i nie zachował tego QLabel. v0.3g przywraca `label_11` w tym samym layoucie obok nowego panelu Log4OM i dodaje gate pilnujący, aby widget nie został ponownie usunięty. Bez zmian logiki programu.

**Hotfix v0.3f:** v0.3e zatrzymał się podczas konfiguracji CMake, zanim ruszył pełny build. Przyczyna: upstream JTDX używa dla `wsjt_fort` i `wsjt_fort_omp` starej/plain składni `target_link_libraries`, a v0.3e dołożył dla tych samych targetów składnię keyword `PUBLIC`. CMake nie pozwala mieszać tych dwóch form. v0.3f dodaje `gfortran` tą samą, plain składnią. W tym projekcie plain link interface pozostaje tranzytywny, więc `-lgfortran` nadal przechodzi do konsumentów C++. Funkcjonalność programu bez zmian.

**Hotfix v0.3e:** po poprawieniu `wsprd_jtdx` build doszedł jeszcze dalej (ok. 1167/1219) i ujawnił ten sam problem w targetach C++ konsumujących statyczne biblioteki Fortrana `wsjt_fort` / `wsjt_fort_omp`: brak propagacji `libgfortran` przy linkowaniu. v0.3e dodaje `gfortran` jako PUBLIC zależność tych bibliotek tylko dla GNU/MinGW oraz pre-build gate dla `jtdx` i `jtdxjt9`. Funkcjonalność aplikacji bez zmian.

**Hotfix v0.3d:** pełny log v0.3c potwierdził poprawną konfigurację i dojście do kroku 1037/1219. Rzeczywista awaria była w linkowaniu `wsprd_jtdx.exe`: target zawiera obiekty Fortrana, ale link wykonywany przez `c++.exe` nie zawierał `-lgfortran`, co dało `_gfortran_runtime_error_at`, `_gfortran_stop_string` i `_gfortran_cshift0_4`. v0.3d dodaje runtime gfortran wyłącznie do `wsprd_jtdx` na GNU/MinGW i gate sprawdzający komendę Ninja przed pełnym buildem. Bez zmian funkcjonalnych programu.

**Hotfix v0.3c:** build v0.3b doszedł dalej, ale zatrzymał się w pomocniczym teście CMake `FortranCInterface_VERIFY(CXX)`. W wygenerowanej komendzie linkera brakowało `libgfortran`, dlatego symbole `_gfortran_st_write*` pozostawały nierozwiązane. v0.3c sprawdza obecność runtime GNU Fortran i tylko na GNU/MinGW omija ten znany fałszywie negatywny preflight; właściwa kompilacja/link całego JTDX pozostaje twardym gate.

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
