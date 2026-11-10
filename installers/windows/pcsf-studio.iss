; Inno Setup script of PCSF Studio: wraps the one-folder PyInstaller
; build (dist/pcsf-studio/) into a Setup.exe with Start Menu entry,
; optional desktop icon, optional .pcsf/.pcsm file association and an
; uninstaller.
;
; The version is never written here; installers/build.py passes it
; from pcsf._version:
;
;   iscc /DMyAppVersion=0.1.0 /DDistDir=..\..\dist\pcsf-studio pcsf-studio.iss
;
; Requires Inno Setup 6 (https://jrsoftware.org/isinfo.php).

#ifndef MyAppVersion
  #error MyAppVersion must be supplied (use installers/build.py)
#endif
#ifndef DistDir
  #define DistDir "..\..\dist\pcsf-studio"
#endif

#define MyAppName "PCSF Studio"
#define MyAppPublisher "earthai-tech"
#define MyAppURL "https://github.com/earthai-tech/pcsf"
#define MyAppExeName "pcsf-studio.exe"
; Fixed across releases so that an upgrade replaces the previous
; installation; do not change.
#define MyAppId "{DEAA707A-7495-4666-95F9-A98B67F46E6E}"

[Setup]
AppId={{#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputBaseFilename=pcsf-studio-{#MyAppVersion}-setup
SetupIconFile=..\assets\pcsf-studio.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Per-user install by default (no administrator rights needed); the
; user can choose an install for all users in the wizard.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associate"; Description: "Open .pcsf and .pcsm files with {#MyAppName}"; GroupDescription: "File types:"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.pcsf"; ValueType: string; ValueName: ""; ValueData: "PCSFStudio.Model"; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.pcsm"; ValueType: string; ValueName: ""; ValueData: "PCSFStudio.Model"; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\PCSFStudio.Model"; ValueType: string; ValueName: ""; ValueData: "PCSF model"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\PCSFStudio.Model\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associate
Root: HKA; Subkey: "Software\Classes\PCSFStudio.Model\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associate

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
