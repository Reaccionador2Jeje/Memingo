#define MyAppName "Memingo"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "AtDev"
#define MyAppExeName "Memingo.exe"
[Setup]
AppId={{A4C5CDE1-78B4-4E0C-8C27-8F01D29F0C25}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Memingo
DefaultGroupName=Memingo
OutputDir=..\..\dist
OutputBaseFilename=Memingo-Setup-{#MyAppVersion}-windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
[Files]
Source: "..\..\dist\Memingo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Memingo"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Memingo"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
[Registry]
Root: HKA; Subkey: "Software\Classes\.mgo"; ValueType: string; ValueName: ""; ValueData: "Memingo.Source"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Memingo.Source"; ValueType: string; ValueName: ""; ValueData: "Memingo source file"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Memingo.Source\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\MemingoFile.ico,0"
Root: HKA; Subkey: "Software\Classes\Memingo.Source\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Memingo.exe"" ""%1"""
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Memingo"; Flags: nowait postinstall skipifsilent
