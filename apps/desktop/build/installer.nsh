; 安装目录默认与软件显示名一致（资源管理器）。
; 可执行文件名保持 ASCII（local-resource-manager.exe），仅安装目录用中文名。
!undef APP_FILENAME
!define APP_FILENAME "资源管理器"

; 安装目录页之后：桌面快捷方式选择（默认勾选；静默安装不弹页、保持创建）
; 仅安装器构建需要；卸载器构建不声明，避免 unused variable 警告
!ifndef BUILD_UNINSTALLER
!include LogicLib.nsh
!include nsDialogs.nsh

Var desktopShortcutChoice
Var desktopShortcutCheckbox

!macro customPageAfterChangeDir
  Page custom DesktopShortcutPageCreate DesktopShortcutPageLeave

  Function DesktopShortcutPageCreate
    !insertmacro MUI_HEADER_TEXT "快捷方式" "选择是否在桌面创建快捷方式。"
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
      Abort
    ${EndIf}
    ${NSD_CreateCheckBox} 0 0 100% 14u "创建桌面快捷方式"
    Pop $desktopShortcutCheckbox
    ${If} $desktopShortcutChoice != "0"
      ${NSD_Check} $desktopShortcutCheckbox
    ${EndIf}
    nsDialogs::Show
  FunctionEnd

  Function DesktopShortcutPageLeave
    ${NSD_GetState} $desktopShortcutCheckbox $desktopShortcutChoice
  FunctionEnd
!macroend

!macro customInstall
  ${If} $desktopShortcutChoice == "0"
    Delete "$DESKTOP\${SHORTCUT_NAME}.lnk"
  ${EndIf}
  # 标记 NSIS 安装版：绿色版 zip 没有此文件，不启用自动更新
  FileOpen $0 "$INSTDIR\installed.marker" w
  FileWrite $0 "installed"
  FileClose $0
!macroend
!endif
