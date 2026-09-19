# Changelog — SP2BPA JTDX Slice Master

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
