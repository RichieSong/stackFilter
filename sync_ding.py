import asyncio
import json
import re
import requests
from mitmproxy import ctx, http

# ===================== 你的配置 =====================
DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=5dfbc8f652a85f9ef88532e085bf604bb57777129bd085e493ab7f5e44b5b6f5"
TARGET_GROUP = "测试B"  # 要同步的群名
# ====================================================

sent_msg = set()

def send_alert(content):
    try:
        requests.post(
            DING_WEBHOOK,
            json={
                "msgtype": "text",
                "text": {"content": f"【{TARGET_GROUP}】{content}"}
            },
            timeout=2
        )
    except:
        pass

class DingTalkMsg:
    def websocket_message(self, flow: http.WebSocketFlow):
        try:
            msg = flow.messages[-1]
            if not msg.from_client:
                data = msg.content
                if data:
                    txt = data.decode("utf-8", errors="ignore")
                    if "content" in txt and TARGET_GROUP in txt:
                        js = json.loads(txt)
                        msg_type = js.get("msgType", "")
                        if msg_type == "TEXT":
                            content = js.get("msg", {}).get("content", "").strip()
                            sender = js.get("sender", {}).get("nick", "未知")
                            final = f"{sender}：{content}"

                            if final not in sent_msg:
                                sent_msg.add(final)
                                print("🆕", final)
                                send_alert(final)
        except:
            pass

addons = [DingTalkMsg()]

async def run_proxy():
    from mitmproxy.tools.main import main
    main(["-s", __file__, "--quiet", "-p", "8888"])

if __name__ == "__main__":
    print("="*60)
    print("✅ 钉钉消息抓包工具启动成功")
    print(f"✅ 目标群：{TARGET_GROUP}")
    print("✅ 请把钉钉代理设置为：127.0.0.1:8888")
    print("="*60)
    asyncio.run(run_proxy())