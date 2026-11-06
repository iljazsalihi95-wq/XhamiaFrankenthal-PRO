#define MyAppName "Xhamia Frankenthal PRO"
#define MyAppVersion "0.3.0"
#define MyAppExeName "XhamiaFrankenthalPRO.exe"
[Setup]
AppId={{7E23A16B-94E7-4B67-9FA1-3DB03C23F871}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\XhamiaFrankenthalPRO
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=XhamiaFrankenthalPRO-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
UninstallDisplayIcon={app}\mosque.ico
VersionInfoVersion=0.3.0.0
VersionInfoDescription=Xhamia Frankenthal PRO Setup
SetupIconFile=assets\mosque.ico
WizardImageFile=assets\wizard.bmp
WizardSmallImageFile=assets\wizard_small.bmp
PrivilegesRequired=lowest
[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\mosque.ico"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\mosque.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\mosque.ico"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Hap Xhamia Frankenthal PRO"; Flags: nowait postinstall skipifsilent
