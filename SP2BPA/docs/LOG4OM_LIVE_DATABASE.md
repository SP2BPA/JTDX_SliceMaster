# Log4OM 2 — bezpośrednie źródło historii QSO

Status: **v0.3a — implementacja przygotowana i schemat zweryfikowany na prawdziwej bazie SP2BPA; przed kompilacją/testem MSI na stacji**.

## Cel

JTDX ma móc używać pełnej bazy Log4OM 2 do ustalania, czy DXCC, znak, lokator lub prefiks był już zrobiony. Dzięki temu kolorowanie „Nowy DXCC” nie zależy wyłącznie od lokalnego `wsjtx_log.adi`.

## Interfejs

Nowy panel ma znajdować się wyłącznie w wolnej prawej części:

`Ustawienia -> Zaawansowane -> Log4OM 2`

Elementy:
- checkbox włączający zewnętrzną bazę,
- pole ze ścieżką do pliku SQLite,
- przycisk `...` do wskazania pliku,
- informacja, że dostęp jest tylko do odczytu i że istnieje fallback.

## Zasada „niczego innego nie ruszamy”

Funkcja jest **opt-in**. Przy wyłączonym checkboxie JTDX działa dokładnie jak dotychczas i korzysta z `wsjtx_log.adi`.

Nie zmieniamy:
- dekodowania ani DSP,
- FT8,
- FT2,
- SuperHound,
- CAT/PTT,
- WideGraph i układu zaakceptowanego GUI,
- działania Slice Mastera ani sterowania wzmacniaczem,
- priorytetów i kolorów powiadomień.

## Bezpieczeństwo bazy

Połączenie SQLite jest otwierane w trybie **read-only**. JTDX nie wykonuje INSERT, UPDATE, DELETE ani żadnych zmian schematu Log4OM.

Jeżeli:
- plik nie istnieje,
- SQLite nie daje się otworzyć,
- tabela `Log` nie istnieje / nie ma kolumny Callsign/Call,
- zapytanie kończy się błędem,

JTDX wraca do standardowego `wsjtx_log.adi`.

## Mapowanie danych

Czytana jest tabela `Log`. Kolumny są wykrywane po nazwie, a nie pozycji. W szczególności:
- `Callsign` lub `Call`,
- `Band`,
- `Mode`,
- `SubMode`,
- `QsoDate`,
- `StationCallsign`,
- pola lokatora, jeżeli występują.

Kraj/DXCC nadal jest wyliczany przez istniejący mechanizm JTDX i jego `cty.dat`. Oznacza to, że nie zmieniamy logiki DXCC — podmieniamy jedynie źródło listy wykonanych łączności.

## Odświeżanie

Po wybraniu bazy JTDX obserwuje plik SQLite, a gdy istnieje również plik `-wal`. Zmiana ma powodować ponowne wczytanie historii bez restartu JTDX.

## Build

Wersja robocza: `v0.3 Log4OM`.

Builder wymaga QtSql i sprawdza obecność sterownika `sqldrivers/qsqlite.dll`. Instalator nie powinien zostać zaakceptowany przez gate buildu, jeśli sterownik SQLite nie trafi do paczki.

Schemat został już zweryfikowany na kopii rzeczywistej bazy Log4OM SP2BPA: 1543 QSO, 98 kolumn, 240 różnych wartości DXCC, tabela `Log`, komplet potrzebnych pól. Przed uznaniem wersji za stabilną pozostaje kompilacja MSI i test funkcjonalny w działającym JTDX.
