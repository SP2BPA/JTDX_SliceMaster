# Zweryfikowany schemat bazy Log4OM 2 — SP2BPA

Data weryfikacji: 2026-09-20.

Baza została sprawdzona **wyłącznie do odczytu**. Nie wykonano żadnych zmian w pliku SQLite.

## Wynik

- tabele: `Informations`, `Log`
- liczba QSO w `Log`: **1543**
- liczba różnych wartości `DXCC`: **240**
- zakres dat QSO: **2023-03-17 19:15:45Z — 2026-09-20 06:36:14Z**
- wszystkie rekordy mają `stationcallsign = SP2BPA`

## Kolumny potrzebne JTDX

Tabela `Log` zawiera bezpośrednio pola potrzebne do mechanizmu Worked/New:

- `callsign`
- `band`
- `mode`
- `qsodate`
- `gridsquare`
- `dxcc`
- `country`
- `cqzone`
- `ituzone`
- `pfx`
- `stationcallsign`
- `mygridsquare`

Łącznie tabela `Log` ma 98 kolumn.

## Emisje w bazie

- USB: 1023
- FT8: 368
- LSB: 100
- CW: 20
- FT4: 14
- SSB: 9
- FT2: 5
- RTTY: 3
- FM: 1

## Wniosek dla integracji

Nie trzeba wykonywać eksportu ADIF, aby ustalić „zrobione / nowe”. JTDX może czytać tabelę `Log` bezpośrednio z pliku SQLite i zasilać istniejące mapy Worked/New.

Implementacja powinna nadal używać istniejącego mechanizmu JTDX dla:
- New DXCC,
- New Call,
- New Grid,
- New Prefix,
- CQ/ITU Zone,
- Band / Mode.

Zmienia się wyłącznie źródło historii QSO.

## Bezpieczeństwo

Połączenie w JTDX ma być otwierane jako `QSQLITE_OPEN_READONLY` oraz z `PRAGMA query_only = ON`.

W przypadku błędu otwarcia, braku tabeli `Log` lub braku wymaganej kolumny `callsign`, JTDX ma automatycznie wrócić do `wsjtx_log.adi`.

## Uwaga o lokatorze

W bazie występują różne wartości `mygridsquare` z historycznych QSO. Dlatego filtr po własnym lokatorze powinien zachowywać dotychczasową logikę JTDX tylko wtedy, gdy użytkownik ma włączone filtrowanie po lokatorze; nie należy globalnie odrzucać dawnych QSO z innym QTH.
