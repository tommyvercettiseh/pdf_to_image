# PDF to image crop

Sla een geselecteerd gedeelte van een PDF-pagina op als PNG of JPG.

## Snelste manier

Dubbelklik op:

```text
run.bat
```

De launcher maakt automatisch deze mappen aan:

```text
output\
test_files\
```

Als PyMuPDF nog niet is geïnstalleerd, probeert `run.bat` dit automatisch te installeren.

## GUI gebruiken

1. Klik op `Kies PDF` of op `Maak test PDF`.
2. Kies eventueel een andere outputmap.
3. Selecteer de juiste pagina.
4. Sleep met de muis een rood vak over het gedeelte dat je wilt opslaan.
5. Kies een bestandsnaam.
6. Klik op `OPSLAAN ALS AFBEELDING`.

De GUI rekent de PDF-coördinaten automatisch uit. Daardoor hoef je `x1`, `y1`, `x2` en `y2` niet handmatig te bepalen.

## Testbestand

Klik in de GUI op `Maak test PDF`.

Dan wordt automatisch gemaakt:

```text
test_files\test_document.pdf
```

Je kunt vervolgens bijvoorbeeld alleen `BLOK 1`, `BLOK 2` of `BLOK 3` selecteren en als losse afbeelding opslaan.

## Output

Standaard worden afbeeldingen opgeslagen in:

```text
output\
```

Bijvoorbeeld:

```text
output\crop.png
```

## Command line blijft ook beschikbaar

```powershell
python .\pdf_crop.py .\voorbeeld.pdf .\output\crop.png --page 1 --x1 100 --y1 150 --x2 500 --y2 300 --dpi 200
```

Als dezelfde documentopmaak steeds terugkomt, kun je dezelfde coördinaten ook automatisch opnieuw gebruiken.
