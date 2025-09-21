"""
Email SMTP Adapter
基于SMTP协议的邮件发送适配器
支持主流邮件服务商和自定义SMTP服务器
"""

import asyncio
import logging
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from .base import (
    APIAdapter,
    AuthenticationError,
    OAuth2Config,
    PermanentError,
    TemporaryError,
    ValidationError,
    register_adapter,
)

logger = logging.getLogger(__name__)


@register_adapter("email")
class EmailAdapter(APIAdapter):
    """Email SMTP适配器 - 基于SMTP协议发送邮件"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def call(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        执行邮件操作

        Args:
            operation: 邮件操作类型 (send_email)
            parameters: 操作参数
            credentials: SMTP认证凭据

        Returns:
            邮件发送结果
        """
        try:
            self.logger.info(f"Email operation: {operation} with params: {list(parameters.keys())}")

            # 验证凭据和参数
            self._validate_parameters(operation, parameters)
            self._validate_smtp_credentials(parameters)

            # 目前主要支持发送邮件
            if operation == "send_email" or operation == "send":
                return await self._send_email(parameters)
            else:
                # 默认为发送邮件
                return await self._send_email(parameters)

        except Exception as e:
            self.logger.error(f"Email operation failed: {e}")
            raise

    def get_oauth2_config(self) -> OAuth2Config:
        """邮件服务通常不使用OAuth2，返回空配置"""
        return OAuth2Config(client_id="", client_secret="", auth_url="", token_url="", scopes=[])

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证SMTP凭据（不使用，改用_validate_smtp_credentials）"""
        return True

    def _validate_parameters(self, operation: str, parameters: Dict[str, Any]):
        """验证操作参数"""
        required_params = ["to", "subject", "body", "smtp_server", "port", "username", "password"]

        for param in required_params:
            if param not in parameters:
                raise ValidationError(f"Missing required parameter: {param}")

        # 验证收件人格式
        to_recipients = parameters["to"]
        if isinstance(to_recipients, str):
            to_recipients = [to_recipients]
        elif not isinstance(to_recipients, list):
            raise ValidationError("'to' parameter must be string or list of strings")

        # 验证邮箱格式
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for email in to_recipients:
            if not re.match(email_pattern, email):
                raise ValidationError(f"Invalid email address: {email}")

    def _validate_smtp_credentials(self, parameters: Dict[str, Any]):
        """验证SMTP配置"""
        smtp_server = parameters.get("smtp_server", "").strip()
        port = parameters.get("port")
        username = parameters.get("username", "").strip()
        password = parameters.get("password", "").strip()

        if not smtp_server:
            raise ValidationError("SMTP server is required")

        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValidationError("Port must be a valid integer between 1-65535")

        if not username:
            raise ValidationError("SMTP username is required")

        if not password:
            raise ValidationError("SMTP password is required")

    async def _send_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """发送邮件"""
        # 使用线程池执行同步的SMTP操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._send_email_sync, parameters)

    def _send_email_sync(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """同步发送邮件"""
        smtp_server = parameters["smtp_server"]
        port = int(parameters["port"])
        username = parameters["username"]
        password = parameters["password"]
        use_tls = parameters.get("use_tls", True)

        # 收件人处理
        to_recipients = parameters["to"]
        if isinstance(to_recipients, str):
            to_recipients = [to_recipients]

        cc_recipients = parameters.get("cc", [])
        if isinstance(cc_recipients, str):
            cc_recipients = [cc_recipients]

        bcc_recipients = parameters.get("bcc", [])
        if isinstance(bcc_recipients, str):
            bcc_recipients = [bcc_recipients]

        # 创建邮件
        msg = MIMEMultipart()
        msg["From"] = username
        msg["To"] = ", ".join(to_recipients)
        if cc_recipients:
            msg["Cc"] = ", ".join(cc_recipients)
        msg["Subject"] = parameters["subject"]

        # 邮件正文
        content_type = parameters.get("content_type", "text/html")
        if content_type == "text/html":
            msg.attach(MIMEText(parameters["body"], "html"))
        else:
            msg.attach(MIMEText(parameters["body"], "plain"))

        # 处理附件
        attachments = parameters.get("attachments", [])
        if attachments:
            for attachment in attachments:
                self._add_attachment(msg, attachment)

        # 发送邮件
        try:
            # 创建SMTP连接
            if port == 465:
                # SSL连接
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(smtp_server, port, context=context)
            else:
                # 标准连接或STARTTLS
                server = smtplib.SMTP(smtp_server, port)
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            # 登录
            server.login(username, password)

            # 发送邮件
            all_recipients = to_recipients + cc_recipients + bcc_recipients
            text = msg.as_string()
            server.sendmail(username, all_recipients, text)
            server.quit()

            self.logger.info(f"Email sent successfully to {len(all_recipients)} recipients")

            return {
                "success": True,
                "message_id": msg.get("Message-ID", ""),
                "recipients": {
                    "to": to_recipients,
                    "cc": cc_recipients,
                    "bcc": bcc_recipients,
                    "total": len(all_recipients),
                },
                "subject": parameters["subject"],
                "smtp_server": smtp_server,
                "sent_at": self._get_current_timestamp(),
            }

        except smtplib.SMTPAuthenticationError as e:
            raise AuthenticationError(f"SMTP authentication failed: {str(e)}")
        except smtplib.SMTPRecipientsRefused as e:
            raise PermanentError(f"Recipients refused: {str(e)}")
        except smtplib.SMTPServerDisconnected as e:
            raise TemporaryError(f"SMTP server disconnected: {str(e)}")
        except smtplib.SMTPException as e:
            raise TemporaryError(f"SMTP error: {str(e)}")
        except Exception as e:
            raise PermanentError(f"Email sending failed: {str(e)}")

    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """添加附件到邮件"""
        try:
            filename = attachment.get("filename", "attachment")
            content = attachment.get("content", "")
            content_type = attachment.get("content_type", "application/octet-stream")

            # 创建附件
            part = MIMEBase("application", "octet-stream")

            if isinstance(content, str):
                part.set_payload(content.encode())
            else:
                part.set_payload(content)

            # 编码附件
            encoders.encode_base64(part)

            # 设置附件头
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )

            msg.attach(part)

        except Exception as e:
            self.logger.warning(
                f"Failed to add attachment {attachment.get('filename', 'unknown')}: {e}"
            )

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    async def connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """测试SMTP连接"""
        try:
            # 提取SMTP配置
            smtp_server = credentials.get("smtp_server", "")
            port = int(credentials.get("port", 587))
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            use_tls = credentials.get("use_tls", True)

            # 验证参数
            if not all([smtp_server, username, password]):
                return {"credentials_valid": False, "error": "Missing SMTP configuration"}

            # 测试连接
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._test_smtp_connection,
                smtp_server,
                port,
                username,
                password,
                use_tls,
            )

            return result

        except Exception as e:
            return {"credentials_valid": False, "error": str(e)}

    def _test_smtp_connection(
        self, smtp_server: str, port: int, username: str, password: str, use_tls: bool
    ) -> Dict[str, Any]:
        """同步测试SMTP连接"""
        try:
            if port == 465:
                # SSL连接
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(smtp_server, port, context=context)
            else:
                # 标准连接或STARTTLS
                server = smtplib.SMTP(smtp_server, port)
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            # 测试登录
            server.login(username, password)
            server.quit()

            return {
                "credentials_valid": True,
                "smtp_server": smtp_server,
                "port": port,
                "username": username,
                "tls_enabled": use_tls,
            }

        except smtplib.SMTPAuthenticationError:
            return {
                "credentials_valid": False,
                "error": "SMTP authentication failed - check username and password",
            }
        except smtplib.SMTPConnectError:
            return {
                "credentials_valid": False,
                "error": f"Cannot connect to SMTP server {smtp_server}:{port}",
            }
        except Exception as e:
            return {"credentials_valid": False, "error": str(e)}

    async def close(self):
        """关闭资源"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)
        await super().close()
