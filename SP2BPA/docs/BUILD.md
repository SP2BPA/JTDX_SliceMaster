# Budowanie JTDX Slice Master Edition na Windows

## Środowisko użyte podczas udanego buildu

- Windows x64
- MSYS2
- MinGW-w64 GCC / GFortran
- Qt 5
- CMake
- Ninja
- Boost
- FFTW
- Hamlib
- WiX Toolset 3.14
- .NET Framework 3.5 (NetFx3) wymagany przez WiX 3.x

Builder przygotowuje zależności i generuje instalator MSI.

## Punkt bazowy JTDX

Builder przypina źródła JTDX 2.2.159 do konkretnego commita używanego przez projekt SQ4KOU, a następnie nakłada patche SuperHound, FT2 i zmiany SP2BPA.

## Build

Uruchomić:

`BUILD_MSI.bat`

najlepiej jako administrator.

Po pierwszym buildzie warto zachować katalog cache, ponieważ zawiera pobrane źródła i zależności. Nie wpływa on na normalną pracę komputera; zajmuje jedynie miejsce na dysku.

## Wynik zweryfikowany

`JTDX-SuperHound-FT2-SliceMaster-2.2.159-v0.2-win64.msi`

## Uwaga

Pełne środowisko MSYS2/WiX nie jest potrzebne do uruchamiania zainstalowanego JTDX. Jest potrzebne wyłącznie do kolejnych kompilacji.
