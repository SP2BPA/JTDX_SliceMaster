# JTDX Slice Master — SP2BPA

Warstwa projektu rozwijana dla stacji SP2BPA na bazie `SQ4KOU/JTDX_SuperHound`.

## Stabilne wydanie

**v0.3h — zweryfikowane na stacji 2026-09-20**

Baza:
- JTDX 2.2.159
- FT8
- FT2
- SuperHound
- standardowy dekoder/DSP JTDX

Potwierdzone w pracy:
- zaakceptowany układ GUI z kompletnym WideGraph/wodospadem w prawej górnej części głównego okna,
- FT8 / FT2 / SuperHound pozostają funkcjonalnie bez zmian,
- CAT przez Slice Master 6000: Hamlib `FlexRadio 6xxx`,
- Slice A: `127.0.0.1:7821`,
- Slice B: `127.0.0.1:7822`,
- PTT: CAT,
- opcjonalny bezpośredni odczyt bazy Log4OM 2 SQLite dla statusu Worked/New,
- baza Log4OM otwierana wyłącznie do odczytu,
- automatyczny fallback do `wsjtx_log.adi`,
- lokalny `wsjtx_log.adi` nadal obsługuje lokalny licznik QSO JTDX.

## Log4OM 2

W `Ustawienia -> Zaawansowane -> Log4OM 2` można wskazać bazę SQLite Log4OM i włączyć ją jako źródło informacji dla:
- New DXCC,
- New Call,
- New Grid,
- New Prefix,
- statusów wg pasma/emisji.

Funkcja jest opt-in. Gdy jest wyłączona lub baza jest niedostępna, JTDX zachowuje standardowe działanie.

## Slice Master

Stabilna ścieżka CAT dla JTDX korzysta z portów 782x. Emulacja HRD 781x była testowana, ale nie jest używana jako konfiguracja robocza.

## Zakres repozytorium

Thetis pozostaje częścią upstreamowego forka, ale **nie jest rozwijany w warstwie SP2BPA**.

Katalog:
- `docs/` — konfiguracja i dokumentacja,
- `builder/` — audyty i informacje buildowe,
- `release/` — metadane stabilnego wydania,
- `CHANGELOG.md` — historia zmian.

Kod upstream pozostaje poza katalogiem `SP2BPA/`, dzięki czemu baza SQ4KOU i nasze zmiany są łatwe do rozróżnienia.
