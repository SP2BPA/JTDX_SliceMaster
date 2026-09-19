# JTDX Slice Master — SP2BPA

Ta część repozytorium dokumentuje rozwój wersji JTDX przygotowanej pod stację SP2BPA i Slice Master 6000.

## Baza projektu

- upstream/fork base: `SQ4KOU/JTDX_SuperHound`
- JTDX base: 2.2.159
- zachowane funkcje: FT8, FT2, SuperHound oraz standardowy dekoder/DSP JTDX
- Thetis nie jest rozwijany w tej gałęzi i nie jest częścią zakresu prac SP2BPA

## Aktualny stan — 2026-09-19

Status: **wersja robocza działająca i używana na stacji**.

Potwierdzone:
- FT8 działa i dekoduje poprawnie
- FT2 pozostaje zaimplementowany
- SuperHound pozostaje zaimplementowany
- WideGraph/wodospad został osadzony w prawej górnej części głównego okna JTDX
- cały WideGraph pozostaje razem z kontrolkami, suwakami i skalą
- pozostały układ GUI został zachowany
- działające sterowanie CAT przez Slice Master 6000 używa Hamlib `FlexRadio 6xxx`
- Slice A: `127.0.0.1:7821`
- Slice B: `127.0.0.1:7822`
- PTT: CAT

## Ważne

Listener HRD Slice Mastera (7811/7812) został przetestowany, ale nie jest obecnie używaną ścieżką dla tej wersji JTDX. Połączenie TCP było zestawiane, lecz handshake HRD nie kończył się poprawnie. Stabilna konfiguracja korzysta z CAT TCP 782x i sterownika Hamlib FlexRadio 6xxx.

Automatyczne uruchamianie JTDX z GUI Slice Mastera nie jest obecnie wymagane. JTDX jest uruchamiany ręcznie z ikony i pracuje poprawnie.

## Struktura katalogu SP2BPA

- `docs/` — bieżąca konfiguracja i opis budowania
- `builder/` — informacje o zweryfikowanym builderze i sumy kontrolne
- `CHANGELOG.md` — historia zmian wykonanych przez SP2BPA/OpenAI

Kod upstream pozostaje poza tym katalogiem, dzięki czemu łatwo rozróżnić bazę SQ4KOU od naszych zmian.
