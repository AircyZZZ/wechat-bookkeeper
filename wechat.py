"""微信协议层：签名验证、XML 解析、回复构造。

微信测试号不需要消息加解密（明文模式），所以代码保持简洁。
"""

import hashlib
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Union


@dataclass
class WxMessage:
    """微信消息结构。"""
    to_user: str       # 公众号原始 ID
    from_user: str     # 用户 openid
    create_time: int   # 消息时间戳
    msg_type: str      # 消息类型，本项目只处理 text
    content: str       # 用户发送的文本内容
    msg_id: str        # 消息 ID


def verify_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    """验证微信服务器签名。

    微信 GET 验证流程：
    1. 将 token、timestamp、nonce 按字典序排序
    2. 拼接成一个字符串
    3. SHA1 哈希
    4. 与 signature 比较
    """
    parts = sorted([token, timestamp, nonce])
    raw = "".join(parts)
    computed = hashlib.sha1(raw.encode()).hexdigest()
    return computed == signature


def parse_message(xml_str: str) -> Union[WxMessage, None]:
    """解析微信发来的 XML 消息。

    Args:
        xml_str: 微信 POST 的原始 XML 文本

    Returns:
        WxMessage 或 None（解析失败）
    """
    try:
        root = ET.fromstring(xml_str)

        def get_text(tag: str) -> str:
            elem = root.find(tag)
            return elem.text or "" if elem is not None else ""

        return WxMessage(
            to_user=get_text("ToUserName"),
            from_user=get_text("FromUserName"),
            create_time=int(get_text("CreateTime") or "0"),
            msg_type=get_text("MsgType"),
            content=get_text("Content"),
            msg_id=get_text("MsgId"),
        )
    except Exception:
        return None


def build_reply(to_user: str, from_user: str, content: str) -> str:
    """构造微信 XML 文本回复。

    注意：to/from 和接收时是反的。
    """
    reply_xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
    return reply_xml
