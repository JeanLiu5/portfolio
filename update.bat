@echo off
REM 双击运行：扫描 images\ 目录，生成缩略图与 photos.js，更新网页照片。
chcp 65001 >nul
cd /d "%~dp0"
echo 正在扫描照片并生成数据...
python scan.py
echo.
echo 完成！刷新浏览器中的 index.html 即可看到更新。
pause
