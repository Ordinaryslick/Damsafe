@echo off
setlocal

set QGIS_PY="C:\Program Files\QGIS 3.40.14\bin\python-qgis-ltr.bat"
set SCRIPT="%~dp0terrain_bvii_sdi.py"

%QGIS_PY% %SCRIPT%

endlocal
pause
