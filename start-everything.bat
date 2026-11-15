@echo off
rem Double-click: update, install and start the match service (with the coach), CS2 in Bot Mode and the website.
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start-everything.ps1" %*
