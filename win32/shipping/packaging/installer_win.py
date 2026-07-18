"""MSI/MSIX installer builder for Windows distribution via Microsoft Store."""

import os
import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class InstallerConfig:
    app_name: str = "PDFMind"
    version: str = "1.0.0"
    publisher: str = "PDFMind Inc."
    publisher_display: str = "PDFMind, Inc."
    description: str = "Intelligent PDF Editor with AI"
    install_dir: str = r"C:\Program Files\PDFMind"
    start_menu_group: str = "PDFMind"
    desktop_shortcut: bool = True
    start_menu_shortcut: bool = True
    auto_start: bool = False
    associate_pdf: bool = True
    install_size_kb: int = 150 * 1024
    min_windows_version: str = "10.0.17763"
    architecture: str = "x64"
    license_path: str = "LICENSE.txt"
    icon_path: str = "assets/icon.ico"
    logo_path: str = "assets/logo.png"
    background_color: str = "#1e1e2e"
    eula_url: str = ""
    privacy_url: str = ""
    help_url: str = ""
    update_url: str = "https://pdfmind.app/update"
    features: list[str] = field(default_factory=lambda: [
        "PDF editing and annotation", "AI-powered analysis",
        "Cloud storage integration", "Digital signatures",
    ])


@dataclass
class MSIXConfig:
    package_name: str = "PDFMind"
    version: str = "1.0.0.0"
    publisher: str = "CN=PDFMind"
    display_name: str = "PDFMind"
    description: str = "Intelligent PDF Editor with AI"
    logo_square: str = "assets/logo_square.png"
    logo_wide: str = "assets/logo_wide.png"
    logo_large: str = "assets/logo_large.png"
    capabilities: list[str] = field(default_factory=lambda: [
        "internetClient", "enterpriseAuthentication",
        "sharedLibrary", "userCertificateStorage",
    ])
    allowed_extensions: list[str] = field(default_factory=lambda: [".pdf"])
    background_color: str = "#1e1e2e"
    languages: list[str] = field(default_factory=lambda: ["en-US", "de-DE", "fr-FR", "ja-JP", "zh-CN"])
    min_version: str = "10.0.17763"
    max_version_tested: str = "10.0.22621"


class InstallerBuilder:
    """Build MSI and MSIX installers for Windows distribution."""

    def __init__(self, config: InstallerConfig = None):
        self._config = config or InstallerConfig()

    def get_config(self) -> InstallerConfig:
        return self._config

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def generate_wxs_manifest(self) -> str:
        c = self._config
        features_xml = ""
        if c.desktop_shortcut:
            features_xml += '<ComponentRef Id="DesktopShortcut"/>\n'
        if c.start_menu_shortcut:
            features_xml += '<ComponentRef Id="StartMenuShortcut"/>\n'
        if c.associate_pdf:
            features_xml += '<ComponentRef Id="PDFAssociation"/>\n'
        wxs = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="{c.app_name}" Language="1033" Version="{c.version}"
           Manufacturer="{c.publisher}" UpgradeCode="A1B2C3D4-E5F6-7890-ABCD-EF1234567890">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine"
             Description="{c.description}" Comments="PDFMind Installer"/>
    <MajorUpgrade DowngradeErrorMessage="A newer version is already installed."/>
    <Media Id="1" Cabinet="pdfmind.cab" EmbedCab="yes"/>
    <Feature Id="ProductFeature" Title="{c.app_name}" Level="1">
      <ComponentRef Id="MainApplication"/>
      {features_xml}
    </Feature>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="{c.app_name}"/>
      </Directory>
      <Directory Id="DesktopFolder">
        <Component Id="DesktopShortcut" Guid="*" Directory="DesktopFolder">
          <Shortcut Id="DesktopShortcut" Name="{c.app_name}" Target="[INSTALLFOLDER]{c.app_name}.exe"
                    WorkingDirectory="INSTALLFOLDER" Icon="AppIcon.exe"/>
          <RemoveFolder Id="RemoveDesktopShortcut" On="uninstall"/>
          <RegistryValue Root="HKCU" Key="Software\\{c.publisher}\\{c.app_name}"
                         Name="DesktopShortcut" Type="integer" Value="1" KeyPath="yes"/>
        </Component>
      </Directory>
    </Directory>
    <Fragment>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ApplicationProgramsFolder" Name="{c.start_menu_group}"/>
      </Directory>
    </Fragment>
    <Icon Id="AppIcon.exe" SourceFile="{c.icon_path}"/>
    <Property Id="ARPPRODUCTICON" Value="AppIcon.exe"/>
    <Property Id="ARPHELPLINK" Value="{c.help_url}"/>
    <Property Id="ARPURLINFOABOUT" Value="{c.privacy_url}"/>
  </Product>
</Wix>"""
        return wxs

    def generate_msix_config(self) -> dict:
        c = self._config
        return {
            "schema": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
            "identity": {
                "name": "PDFMind",
                "publisher": "CN=PDFMindInc",
                "version": f"{c.version}.0",
            },
            "properties": {
                "displayName": c.app_name,
                "publisherDisplayName": c.publisher_display,
                "description": c.description,
                "logo": c.logo_path,
                "backgroundColor": c.background_color,
            },
            "requirements": {
                "deviceCapability": {"internetClient": True},
                "minVersion": c.min_windows_version,
            },
            "capabilities": ["internetClient"],
            "extensions": [{
                "type": "windows.protocol",
                "protocol": {"name": "pdfmind", "displayName": "PDFMind"},
            }, {
                "type": "windows.fileTypeAssociation",
                "fileTypeAssociation": {
                    "name": "pdf",
                    "supportedFileTypes": [{"fileType": ".pdf"}],
                },
            }],
        }

    def generate_build_script(self) -> str:
        c = self._config
        return f"""@echo off
REM PDFMind Installer Build Script
echo Building PDFMind {c.version} installer...

REM Clean previous build
if exist dist\\installer rmdir /s /q dist\\installer
mkdir dist\\installer

REM Build MSIX package
echo Building MSIX package...
makeappx pack /d .\\msix_package /p dist\\installer\\PDFMind-{c.version}-x64.msix /o

REM Sign MSIX package
echo Signing MSIX package...
signtool sign /a /fd SHA256 /f cert.pfx /p {{CERT_PASSWORD}} dist\\installer\\PDFMind-{c.version}-x64.msix

REM Build MSI with WiX
echo Building MSI installer...
candle.exe -dVersion={c.version} -dInstallDir="{c.install_dir}" pdfmind.wxs
light.exe -ext WixUIExtension pdfmind.wixobj -o dist\\installer\\PDFMind-{c.version}-x64.msi

echo Build complete! Output in dist\\installer\\
dir dist\\installer\\
"""

    def get_build_checklist(self) -> list[dict]:
        c = self._config
        return [
            {"item": "Version number updated", "required": True, "checked": bool(c.version)},
            {"item": "License file included", "required": True, "checked": os.path.exists(c.license_path)},
            {"item": "Application icon present", "required": True, "checked": os.path.exists(c.icon_path)},
            {"item": "Code signing certificate", "required": True, "checked": False},
            {"item": "MSIX package manifest", "required": True, "checked": True},
            {"item": "WiX manifest generated", "required": True, "checked": True},
            {"item": "PDF file association", "required": False, "checked": c.associate_pdf},
            {"item": "Desktop shortcut", "required": False, "checked": c.desktop_shortcut},
            {"item": "Start menu group", "required": False, "checked": c.start_menu_shortcut},
            {"item": "Auto-update URL configured", "required": False, "checked": bool(c.update_url)},
            {"item": "Privacy policy URL", "required": True, "checked": bool(c.privacy_url)},
            {"item": "Help/support URL", "required": False, "checked": bool(c.help_url)},
        ]

    def generate_package_content_map(self) -> dict:
        return {
            "exe": f"{self._config.app_name}.exe",
            "dlls": ["PySide6/*.dll", "pdfmind/*.pyd"],
            "resources": ["resources/", "assets/"],
            "config": ["config.json", "settings.json"],
            "plugins": ["plugins/"],
            "total_size_estimate_kb": self._config.install_size_kb,
        }
