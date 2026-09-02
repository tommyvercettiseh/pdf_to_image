# PDF to image crop

Sla een vast rechthoekig gedeelte van een PDF-pagina op als PNG of JPG.

## Installatie

```powershell
python -m pip install -r requirements.txt
```

## Gebruik

```powershell
python .\pdf_crop.py .\voorbeeld.pdf .\output\crop.png --page 1 --x1 100 --y1 150 --x2 500 --y2 300 --dpi 200
```

De coordinaten zijn PDF-punten:

* `x1`, `y1` = linksboven
* `x2`, `y2` = rechtsonder
* `page` begint bij 1

Als dezelfde documentopmaak steeds terugkomt, kun je dezelfde coordinaten steeds opnieuw gebruiken.
