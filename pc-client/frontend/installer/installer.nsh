; installer/installer.nsh
; 鱿郁仔仔 - 自定义 NSIS 安装脚本
; 由 electron-builder 调用

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "FileFunc.nsh"

; 自定义变量
Var /GLOBAL InstallPath
Var /GLOBAL PreviousVersion

; ==================== 安装前检查 ====================
!macro customHeader
  ; 设置安装程序属性
  !define MUI_ABORTWARNING
  !define MUI_ABORTWARNING_CANCEL
  
  ; 自定义页面标题
  !define MUI_WELCOMEPAGE_TITLE "欢迎安装 鱿郁仔仔"
  !define MUI_WELCOMEPAGE_TEXT "鱿郁仔仔是一款 Nintendo Switch 游戏管理工具。$\r$\n$\r$\n本向导将引导您完成安装过程。$\r$\n$\r$\n点击 下一步 继续。"
  
  !define MUI_FINISHPAGE_TITLE "安装完成"
  !define MUI_FINISHPAGE_TEXT "鱿郁仔仔 已成功安装到您的计算机。"
  !define MUI_FINISHPAGE_RUN "$INSTDIR\鱿郁仔仔.exe"
  !define MUI_FINISHPAGE_RUN_TEXT "运行 鱿郁仔仔"
  !define MUI_FINISHPAGE_LINK "访问项目主页"
  !define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/your-repo"
!macroend

; ==================== 初始化 ====================
!macro preInit
  ; 检查 Windows 版本
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "此程序需要 Windows 10 或更高版本。"
    Abort
  ${EndIf}
  
  ; 检查是否已安装
  SetRegView 64
  ReadRegStr $PreviousVersion HKLM "Software\鱿郁仔仔" "InstallDir"
  
  ${If} $PreviousVersion != ""
    ; 读取版本号
    ReadRegStr $0 HKLM "Software\鱿郁仔仔" "Version"
    
    MessageBox MB_YESNO|MB_ICONQUESTION \
      "检测到已安装 鱿郁仔仔 (版本 $0)。$\r$\n$\r$\n是否覆盖安装？$\r$\n（用户数据将保留）" \
      IDYES continue_install
    Abort
    
    continue_install:
    ; 使用之前的安装路径
    StrCpy $INSTDIR $PreviousVersion
  ${EndIf}
!macroend

; ==================== 安装过程 ====================
!macro customInstall
  ; 写入注册表
  WriteRegStr HKLM "Software\鱿郁仔仔" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\鱿郁仔仔" "Version" "${VERSION}"
  
  ; 添加卸载信息
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔" \
    "DisplayName" "鱿郁仔仔"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔" \
    "UninstallString" "$INSTDIR\Uninstall 鱿郁仔仔.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔" \
    "DisplayIcon" "$INSTDIR\鱿郁仔仔.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔" \
    "Publisher" "鱿郁仔仔团队"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔" \
    "DisplayVersion" "${VERSION}"
  
  ; 计算安装大小
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔" \
    "EstimatedSize" "$0"
  
  ; 创建数据目录
  CreateDirectory "$APPDATA\youyuzz\cache"
  CreateDirectory "$APPDATA\youyuzz\data"
  CreateDirectory "$APPDATA\youyuzz\logs"
  
  ; 设置目录权限（允许普通用户写入）
  AccessControl::GrantOnFile \
    "$APPDATA\youyuzz" "(BU)" "GenericRead + GenericWrite"
!macroend

; ==================== 卸载过程 ====================
!macro customUnInstall
  ; 询问是否删除用户数据
  MessageBox MB_YESNO|MB_ICONQUESTION \
    "是否删除用户数据（缓存、配置、日志等）？$\r$\n$\r$\n选择 否 将保留这些数据，以便下次安装时恢复。" \
    IDNO skip_userdata
  
  ; 删除用户数据
  RMDir /r "$APPDATA\youyuzz\cache"
  RMDir /r "$APPDATA\youyuzz\data"
  RMDir /r "$APPDATA\youyuzz\logs"
  RMDir "$APPDATA\youyuzz"
  
  skip_userdata:
  
  ; 清理注册表
  DeleteRegKey HKLM "Software\鱿郁仔仔"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\鱿郁仔仔"
!macroend

; ==================== 自定义函数 ====================
; 检查进程是否运行
Function CheckProcessRunning
  nsExec::ExecToStack 'tasklist /FI "IMAGENAME eq 鱿郁仔仔.exe" /NH'
  Pop $0
  ${If} $0 != ""
    MessageBox MB_OK|MB_ICONEXCLAMATION \
      "鱿郁仔仔 正在运行，请先关闭程序后再继续安装。"
    Abort
  ${EndIf}
FunctionEnd

; 安装前检查进程
!macro customInit
  Call CheckProcessRunning
!macroend

; 卸载前检查进程
!macro customUnInit
  Call CheckProcessRunning
!macroend
