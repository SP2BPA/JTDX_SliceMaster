# Slice Master 6000 — konfiguracja JTDX

## Konfiguracja zalecana i przetestowana

### Slice A

- JTDX Rig: `FlexRadio 6xxx`
- Network Server: `127.0.0.1:7821`
- PTT Method: `CAT`

### Slice B

- JTDX Rig: `FlexRadio 6xxx`
- Network Server: `127.0.0.1:7822`
- PTT Method: `CAT`

## Porty Slice Mastera

| Funkcja | TX | Slice A | Slice B |
|---|---:|---:|---:|
| HRD TCP | 7810 | 7811 | 7812 |
| CAT TCP | 7820 | 7821 | 7822 |

Dla JTDX używamy obecnie **CAT TCP 782x**, nie HRD 781x.

## Co zostało sprawdzone

- listener 7821 nasłuchuje dla Slice A
- `Test CAT` w JTDX działa przy `FlexRadio 6xxx / 127.0.0.1:7821`
- zmiana częstotliwości i sterowanie radiem działają przez Slice Master
- sterowanie wzmacniaczem przez Slice Master pozostaje poprawne
- JTDX może być uruchamiany ręcznie; automatyczny przycisk JTDX w Slice Masterze nie jest wymagany do bieżącej pracy

## HRD

Port 7811 był dostępny i przyjmował połączenie TCP, ale JTDX nie kończył poprawnie testu CAT przez emulację HRD. Z tego powodu ta droga nie jest obecnie konfiguracją roboczą.
