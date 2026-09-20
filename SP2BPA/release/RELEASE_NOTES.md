# JTDX SuperHound FT2 SliceMaster v0.3h — Log4OM 2

**Status: stabilne / zweryfikowane na stacji SP2BPA — 2026-09-20**

## Najważniejsze

- JTDX 2.2.159
- zachowane FT8, FT2 i SuperHound
- zaakceptowany układ GUI z kompletnym WideGraph w prawym górnym obszarze
- CAT przez Slice Master 6000 i Hamlib `FlexRadio 6xxx`
- Slice A `127.0.0.1:7821`, Slice B `127.0.0.1:7822`
- PTT przez CAT
- nowa opcjonalna integracja z bazą Log4OM 2 SQLite

## Log4OM 2

JTDX może używać wskazanej bazy Log4OM jako źródła statusu Worked/New dla DXCC, znaków, lokatorów i prefiksów.

Bezpieczeństwo:
- baza jest otwierana wyłącznie do odczytu,
- JTDX nie wykonuje zmian w bazie Log4OM,
- funkcja jest domyślnie wyłączona,
- gdy baza jest niedostępna, następuje fallback do `wsjtx_log.adi`,
- lokalny `wsjtx_log.adi` nadal zachowuje lokalny licznik QSO JTDX.

## Test na stacji

Potwierdzono:
- instalację MSI,
- uruchomienie JTDX,
- audio i dekodowanie,
- CAT,
- WideGraph/GUI,
- poprawne rozpoznawanie wcześniej zrobionych DXCC z pełnej bazy Log4OM,
- zachowanie lokalnego licznika JTDX po przywróceniu lokalnego `wsjtx_log.adi`.

## Zweryfikowany MSI

Plik:
`JTDX-SuperHound-FT2-SliceMaster-2.2.159-v0.3h-Log4OM-win64.msi`

Rozmiar:
`46,061,921 bytes`

SHA256:
`1334102334F2732D1BAEEA92BD977C132DB8E5260243D8718E70756C452CA98A`

Uwaga: build jest własną, niepodpisaną cyfrowo kompilacją. Windows Smart App Control może wymagać odpowiedniego ustawienia lub podpisanego wydania.

## Pochodzenie

Projekt jest forkiem `SQ4KOU/JTDX_SuperHound` i bazuje na JTDX / WSJT-X zgodnie z ich licencjami. Thetis nie jest częścią zakresu prac SP2BPA.
