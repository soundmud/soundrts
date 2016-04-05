#define FileHandle FileOpen("version.txt")
#define MyAppVer FileRead(FileHandle)

#define FileHandle FileOpen("version-name.txt")
#define MyAppVerName FileRead(FileHandle)

#define FileHandle FileOpen("stage.txt")
#define MyAppStage FileRead(FileHandle)

#define FileHandle FileOpen("stage-name.txt")
#define MyAppStageName FileRead(FileHandle)

#if MyAppStage == "stable"
#define MyAppStage
#define MyAppStageName
#endif

[Setup]
AppName=SoundRTS {#MyAppStageName}
AppVerName=SoundRTS {#MyAppVerName}
AppPublisher=SoundMud
AppPublisherURL=http://jlpo.free.fr/soundrts
AppSupportURL=http://jlpo.free.fr/soundrts
AppUpdatesURL=http://jlpo.free.fr/soundrts
DefaultDirName={pf}\SoundRTS {#MyAppStage}
DefaultGroupName=SoundRTS {#MyAppStageName}
Compression=lzma
SolidCompression=true
OutputBaseFilename=soundrts-{#MyAppVer}
OutputDir=..\dist
ShowLanguageDialog=auto
PrivilegesRequired=none

[Files]
Source: soundrts-{#MyAppVer}-windows\*; Excludes: \user; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: {userappdata}\SoundRTS {#MyAppStage}

[Icons]
Name: {group}\SoundRTS {#MyAppStageName}; Filename: {app}\soundrts.exe; WorkingDir: {app}
Name: {group}\SoundRTS with soundpack; Filename: {app}\soundrts.exe; Parameters: --mods=soundpack; WorkingDir: {app}
Name: {group}\CrazyMod\CrazyMod 8.2a; Filename: {app}\soundrts.exe; Parameters: --mods=soundpack,CrazyMod8.2; WorkingDir: {app}
Name: {group}\CrazyMod\Website; Filename: http://pragmapragma.free.fr/soundrts-crazymod/
Name: {group}\Mini mods\Orcs; Filename: {app}\soundrts.exe; Parameters: --mods=orc; WorkingDir: {app}
Name: {group}\Mini mods\Teleportation; Filename: {app}\soundrts.exe; Parameters: --mods=teleportation; WorkingDir: {app}
Name: {group}\Mini mods\Vanilla (no mod); Filename: {app}\soundrts.exe; Parameters: --mods=; WorkingDir: {app}
Name: {group}\Manual; Filename: {app}\doc\help-index.htm
Name: {group}\Website; Filename: http://jlpo.free.fr/soundrts
Name: {group}\{cm:UninstallProgram, SoundRTS}; Filename: {uninstallexe}
Name: {group}\user; Filename: {userappdata}\SoundRTS {#MyAppStage}

[Languages]
Name: English; MessagesFile: compiler:Default.isl
Name: BrazilianPortuguese; MessagesFile: compiler:Languages\BrazilianPortuguese.isl
Name: Chinese; MessagesFile: ChineseSimp-12-5.1.11.isl
Name: Czech; MessagesFile: compiler:Languages\Czech.isl
Name: Dutch; MessagesFile: compiler:Languages\Dutch.isl
Name: French; MessagesFile: compiler:Languages\French.isl
Name: German; MessagesFile: compiler:Languages\German.isl
Name: Italian; MessagesFile: compiler:Languages\Italian.isl
Name: Polish; MessagesFile: compiler:Languages\Polish.isl
Name: Russian; MessagesFile: compiler:Languages\Russian.isl
Name: Slovak; MessagesFile: compiler:Languages\Slovak.isl
Name: Spanish; MessagesFile: compiler:Languages\Spanish.isl

[_ISTool]
UseAbsolutePaths=true
