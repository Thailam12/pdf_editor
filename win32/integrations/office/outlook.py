"""Outlook integration: open PDF attachments, save back to email, and reply with annotated PDFs."""

import os
import logging
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False


@dataclass
class EmailMessage:
    entry_id: str = ""
    subject: str = ""
    sender: str = ""
    sender_email: str = ""
    to: str = ""
    cc: str = ""
    body: str = ""
    body_html: str = ""
    received_time: str = ""
    has_attachments: bool = False
    attachment_count: int = 0
    is_read: bool = False
    importance: str = "normal"


@dataclass
class Attachment:
    name: str = ""
    content_type: str = ""
    size_bytes: int = 0
    content: bytes = b""
    is_inline: bool = False
    content_id: str = ""
    is_pdf: bool = False


@dataclass
class OutlookFolder:
    name: str = ""
    entry_id: str = ""
    folder_type: str = ""
    child_count: int = 0
    unread_count: int = 0


class OutlookIntegration:
    """Microsoft Outlook integration for opening, saving, and replying with PDF attachments."""

    OL_FOLDER_INBOX = 6
    OL_FOLDER_SENT = 5
    OL_FOLDER_DRAFTS = 16
    OL_FOLDER_OUTBOX = 4
    OL_FORMAT_HTML = 2
    OL_FORMAT_PLAIN = 1
    OL_FORMAT_RTF = 3
    OL_SAVE_AS_PDF = 10245

    def __init__(self, profile_name: str = ""):
        self._outlook = None
        self._namespace = None
        self._profile_name = profile_name
        self._connected = False

    def connect(self) -> bool:
        if not HAS_WIN32COM:
            logger.warning("win32com not available; Outlook integration disabled on non-Windows")
            return False
        try:
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            self._namespace = self._outlook.GetNamespace("MAPI")
            if self._profile_name:
                self._namespace.Logon(self._profile_name)
            else:
                self._namespace.Logon()
            self._connected = True
            logger.info("Connected to Outlook")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Outlook: {e}")
            return False

    def disconnect(self):
        if self._namespace:
            try:
                self._namespace.Logoff()
            except Exception:
                pass
        self._connected = False
        self._outlook = None
        self._namespace = None

    def _ensure_connected(self):
        if not self._connected:
            if not self.connect():
                raise RuntimeError("Cannot connect to Outlook")

    def get_default_folder(self, folder_type: int):
        self._ensure_connected()
        return self._namespace.GetDefaultFolder(folder_type)

    def get_inbox(self):
        return self.get_default_folder(self.OL_FOLDER_INBOX)

    def list_folders(self, parent=None) -> list[OutlookFolder]:
        self._ensure_connected()
        parent = parent or self._namespace.Folders.Item(1)
        folders = []
        for i in range(1, parent.Folders.Count + 1):
            f = parent.Folders.Item(i)
            folders.append(OutlookFolder(
                name=f.Name, entry_id=f.EntryID,
                child_count=f.Items.Count,
            ))
        return folders

    def list_messages(self, folder=None, limit: int = 50,
                      unread_only: bool = False) -> list[EmailMessage]:
        self._ensure_connected()
        if folder is None:
            folder = self.get_inbox()
        messages = []
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        if unread_only:
            items = items.Restrict("[UnRead] = True")
        for i, item in enumerate(items):
            if i >= limit:
                break
            try:
                msg = EmailMessage(
                    entry_id=item.EntryID,
                    subject=item.Subject or "",
                    sender=item.SenderName or "",
                    sender_email=getattr(item, "SenderEmailAddress", ""),
                    to=getattr(item, "To", ""),
                    cc=getattr(item, "CC", ""),
                    body=item.Body or "",
                    body_html=getattr(item, "HTMLBody", "") or "",
                    received_time=str(item.ReceivedTime),
                    has_attachments=item.Attachments.Count > 0,
                    attachment_count=item.Attachments.Count,
                    is_read=item.UnRead is False if hasattr(item, "UnRead") else True,
                    importance={0: "low", 1: "normal", 2: "high"}.get(
                        getattr(item, "Importance", 1), "normal"
                    ),
                )
                messages.append(msg)
            except Exception as e:
                logger.warning(f"Error reading message: {e}")
                continue
        return messages

    def search_messages(self, query: str, folder=None, limit: int = 50) -> list[EmailMessage]:
        self._ensure_connected()
        if folder is None:
            folder = self.get_inbox()
        messages = []
        filter_str = f"@SQL=`urn:schemas:httpmail:subject` LIKE '%{query}%'"
        try:
            items = folder.Items.Restrict(filter_str)
            for i, item in enumerate(items):
                if i >= limit:
                    break
                try:
                    msg = EmailMessage(
                        entry_id=item.EntryID,
                        subject=item.Subject or "",
                        sender=item.SenderName or "",
                        sender_email=getattr(item, "SenderEmailAddress", ""),
                        to=getattr(item, "To", ""),
                        body=item.Body or "",
                        received_time=str(item.ReceivedTime),
                        has_attachments=item.Attachments.Count > 0,
                    )
                    messages.append(msg)
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        return messages

    def get_attachments(self, entry_id: str) -> list[Attachment]:
        self._ensure_connected()
        item = self._namespace.GetItemFromID(entry_id)
        attachments = []
        for i in range(1, item.Attachments.Count + 1):
            att = item.Attachments.Item(i)
            is_pdf = att.FileName.lower().endswith(".pdf")
            attachments.append(Attachment(
                name=att.FileName,
                content_type=getattr(att, "ContentType", ""),
                size_bytes=att.Size,
                content=att.PropertyAccessor.GetProperty(
                    "http://schemas.microsoft.com/mapi/proptag/0x37080102"
                ) if is_pdf else b"",
                is_inline=getattr(att, "IsInline", False),
                content_id=getattr(att, "ContentId", ""),
                is_pdf=is_pdf,
            ))
        return attachments

    def open_pdf_attachment(self, entry_id: str, attachment_index: int = 0) -> Optional[bytes]:
        self._ensure_connected()
        item = self._namespace.GetItemFromID(entry_id)
        if item.Attachments.Count <= attachment_index:
            return None
        att = item.Attachments.Item(attachment_index + 1)
        content = att.PropertyAccessor.GetProperty(
            "http://schemas.microsoft.com/mapi/proptag/0x37080102"
        )
        logger.info(f"Opened attachment: {att.FileName} ({len(content)} bytes)")
        return content

    def save_pdf_to_email(self, entry_id: str, pdf_path: str, attachment_name: str = None) -> bool:
        self._ensure_connected()
        try:
            item = self._namespace.GetItemFromID(entry_id)
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return False
            name = attachment_name or os.path.basename(pdf_path)
            item.Attachments.Add(
                pdf_path,
                1,  # olByValue
                1,
                name,
            )
            item.Save()
            logger.info(f"Saved PDF {name} to email: {item.Subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to save PDF to email: {e}")
            return False

    def save_as_pdf(self, entry_id: str, output_path: str) -> bool:
        self._ensure_connected()
        try:
            item = self._namespace.GetItemFromID(entry_id)
            item.SaveAs(output_path, self.OL_SAVE_AS_PDF)
            logger.info(f"Saved email as PDF: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save as PDF: {e}")
            return False

    def reply_with_pdf(self, entry_id: str, pdf_path: str,
                       reply_body: str = "",
                       reply_all: bool = False) -> Optional[str]:
        self._ensure_connected()
        try:
            item = self._namespace.GetItemFromID(entry_id)
            if reply_all:
                response = item.ReplyAll
            else:
                response = item.Reply
            if reply_body:
                response.HTMLBody = f"<p>{reply_body}</p><hr>{response.HTMLBody}"
            if os.path.exists(pdf_path):
                name = os.path.basename(pdf_path)
                response.Attachments.Add(pdf_path, 1, 1, name)
            response.Send()
            logger.info(f"Sent reply with PDF to: {item.SenderName}")
            return response.EntryID
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return None

    def forward_with_pdf(self, entry_id: str, pdf_path: str, to: str,
                         forward_body: str = "") -> Optional[str]:
        self._ensure_connected()
        try:
            item = self._namespace.GetItemFromID(entry_id)
            fwd = item.Forward
            fwd.To = to
            if forward_body:
                fwd.HTMLBody = f"<p>{forward_body}</p><hr>{fwd.HTMLBody}"
            if os.path.exists(pdf_path):
                fwd.Attachments.Add(pdf_path, 1, 1, os.path.basename(pdf_path))
            fwd.Send()
            return fwd.EntryID
        except Exception as e:
            logger.error(f"Failed to forward: {e}")
            return None

    def create_email_with_pdf(self, to: str, subject: str, body: str,
                               pdf_path: str, cc: str = None) -> Optional[str]:
        self._ensure_connected()
        try:
            mail = self._outlook.CreateItem(0)
            mail.To = to
            mail.Subject = subject
            mail.HTMLBody = f"<p>{body}</p>"
            if cc:
                mail.CC = cc
            if os.path.exists(pdf_path):
                mail.Attachments.Add(pdf_path, 1, 1, os.path.basename(pdf_path))
            mail.Send()
            return mail.EntryID
        except Exception as e:
            logger.error(f"Failed to create email: {e}")
            return None

    def monitor_inbox(self, callback, poll_interval: int = 30, folder=None):
        self._ensure_connected()
        import time
        if folder is None:
            folder = self.get_inbox()
        seen_ids = set()
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        for item in items:
            seen_ids.add(item.EntryID)
        logger.info(f"Monitoring inbox ({len(seen_ids)} existing messages)")
        while True:
            time.sleep(poll_interval)
            items = folder.Items
            items.Sort("[ReceivedTime]", True)
            for item in items:
                if item.EntryID not in seen_ids:
                    seen_ids.add(item.EntryID)
                    try:
                        msg = EmailMessage(
                            entry_id=item.EntryID,
                            subject=item.Subject or "",
                            sender=item.SenderName or "",
                            sender_email=getattr(item, "SenderEmailAddress", ""),
                            to=getattr(item, "To", ""),
                            body=item.Body or "",
                            received_time=str(item.ReceivedTime),
                            has_attachments=item.Attachments.Count > 0,
                        )
                        callback(msg)
                    except Exception as e:
                        logger.error(f"Monitor callback error: {e}")

    def export_folder_as_pdf(self, folder=None, output_dir: str = None,
                              pdf_only: bool = True) -> list[str]:
        self._ensure_connected()
        if folder is None:
            folder = self.get_inbox()
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="pdfmind_outlook_")
        os.makedirs(output_dir, exist_ok=True)
        exported = []
        for i, item in enumerate(folder.Items):
            try:
                if pdf_only:
                    attachments = self.get_attachments(item.EntryID)
                    for att in attachments:
                        if att.is_pdf and att.content:
                            path = os.path.join(output_dir, att.name)
                            with open(path, "wb") as f:
                                f.write(att.content)
                            exported.append(path)
                else:
                    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in item.Subject)[:100]
                    path = os.path.join(output_dir, f"{safe_name}.pdf")
                    self.save_as_pdf(item.EntryID, path)
                    exported.append(path)
            except Exception as e:
                logger.warning(f"Failed to export item: {e}")
        return exported
