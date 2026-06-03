import base64
import json
import os
import random
import re
import secrets
import time
from pathlib import Path
from urllib.parse import quote

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from flask import Flask, jsonify, render_template_string, request, session


DEFAULT_APPID = (
    "2f8af12ad9912d306b5053abf90c7ebbb695887bc"
    "870ae0706d573c348539c26c5c0a878641fcc0d3e90acb9be1e6ef858a"
    "59af546f3c826988332376b7d18c8ea2398ee3a9c3db947e2471d32a49612"
)

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDc+CZK9bBA9IU+gZUOc6FUGu7y
O9WpTNB0PzmgFBh96Mg1WrovD1oqZ+eIF4LjvxKXGOdI79JRdve9NPhQo07+uqGQ
gE4imwNnRx7PFtCRryiIEcUoavuNtuRVoBAm6qdB0SrctgaqGfLgKvZHOnwTjyNq
jBUxzMeQlEC2czEMSwIDAQAB
-----END PUBLIC KEY-----"""

CAPTCHA_APPID = "195809716"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "token_history.json"
MAX_HISTORY = 20

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


def json_error(message, status_code=400, **extra):
    payload = {"status": "fail", "msg": message}
    payload.update(extra)
    return jsonify(payload), status_code


def read_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def write_history(items):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(items[:MAX_HISTORY], f, ensure_ascii=False, indent=2)


def append_history(item):
    items = read_history()
    items = [entry for entry in items if entry.get("phone") != item.get("phone")]
    items.insert(0, item)
    write_history(items)


def clear_history():
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
    except OSError:
        return False
    return True


def normalize_phone(value):
    phone = re.sub(r"\D", "", str(value or ""))
    return phone if len(phone) == 11 else ""


def random_hex(length=32):
    return "".join(random.choices("0123456789abcdef", k=length))


def generate_appid():
    def rnd():
        return str(random.randint(0, 9))

    return (
        f"{rnd()}f{rnd()}af"
        f"{rnd()}{rnd()}ad"
        f"{rnd()}912d306b5053abf90c7ebbb695887bc"
        "870ae0706d573c348539c26c5c0a878641fcc0d3e90acb9be1e6ef858a"
        "59af546f3c826988332376b7d18c8ea2398ee3a9c3db947e2471d32a49612"
    )


def session_state():
    if "device_id" not in session:
        session["device_id"] = random_hex(32)
    if "appid" not in session:
        session["appid"] = generate_appid()
    return session["device_id"], session["appid"]


class UnicomAndroid:
    def __init__(self, phone, appid=None, device_id=None):
        self.phone = phone
        self.device_id = device_id or random_hex(32)
        self.appid = appid if appid and len(appid) > 20 else DEFAULT_APPID
        self.ua = (
            "Mozilla/5.0 (Linux; Android 13; M2007J3SC Build/TKQ1.220829.002; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.5304.141 "
            f"Mobile Safari/537.36; unicom{{version:android@11.0800,desmobile:{phone}}};"
            "devicetype{deviceBrand:Xiaomi,deviceModel:M2007J3SC};{yw_code:}"
        )

    def rsa(self, value):
        key = RSA.import_key(PUBLIC_KEY.encode("utf-8"))
        cipher = PKCS1_v1_5.new(key)
        encrypted = cipher.encrypt(str(value).encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")

    def post_form(self, url, data):
        headers = {
            "Host": "m.client.10010.com",
            "User-Agent": self.ua,
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "com.sinovatech.unicom.ui",
        }
        try:
            response = requests.post(url, data=data, headers=headers, timeout=18)
            try:
                return response.json()
            except ValueError:
                return {
                    "code": "Err",
                    "msg": f"上游接口返回非 JSON，HTTP {response.status_code}，可能被风控或网络拦截",
                }
        except requests.RequestException as exc:
            return {"code": "Err", "msg": f"请求上游接口失败：{exc}"}

    def post_json(self, url, data, headers=None):
        final_headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "com.sinovatech.unicom.ui",
        }
        if headers:
            final_headers.update(headers)
        try:
            response = requests.post(url, json=data, headers=final_headers, timeout=18)
            try:
                return response.json()
            except ValueError:
                return {
                    "code": "Err",
                    "msg": f"上游接口返回非 JSON，HTTP {response.status_code}，可能被风控或网络拦截",
                }
        except requests.RequestException as exc:
            return {"code": "Err", "msg": f"请求上游接口失败：{exc}"}

    def send_code(self, result_token=""):
        url = "https://m.client.10010.com/mobileService/sendRadomNum.htm"
        timestamp = time.strftime("%Y%m%d%H%M%S")
        post_data = (
            "isFirstInstall=1"
            "&simCount=1"
            "&yw_code="
            "&deviceOS=android13"
            f"&mobile={quote(self.rsa(self.phone))}"
            "&netWay=Wifi"
            "&loginCodeLen=6"
            f"&deviceId={self.device_id}"
            f"&deviceCode={self.device_id}"
            "&version=android@11.0800"
            "&send_flag="
            f"&resultToken={quote(result_token) if result_token else ''}"
            "&keyVersion="
            "&provinceChanel=general"
            f"&appId={self.appid}"
            "&deviceModel=M2007J3SC"
            f"&androidId={self.device_id[:16]}"
            "&deviceBrand=Xiaomi"
            f"&timestamp={timestamp}"
        )
        return self.post_form(url, post_data)

    def validate_captcha(self, mobile_hex, ticket, rand_str):
        url = "https://loginxhm.10010.com/login-web/v1/chartCaptcha/validateTencentCaptcha"
        payload = {
            "seq": random_hex(32),
            "captchaType": "10",
            "mobile": mobile_hex,
            "ticket": ticket,
            "randStr": rand_str,
            "imei": self.device_id,
        }
        headers = {
            "Origin": "https://img.client.10010.com",
            "Referer": "https://img.client.10010.com/loginRisk/index.html",
        }
        return self.post_json(url, payload, headers)

    def login(self, code):
        url = "https://m.client.10010.com/mobileService/radomLogin.htm"
        timestamp = time.strftime("%Y%m%d%H%M%S")
        post_data = (
            "isFirstInstall=1"
            "&simCount=1"
            "&yw_code="
            "&loginStyle=0"
            "&isRemberPwd=true"
            "&deviceOS=android13"
            f"&mobile={quote(self.rsa(self.phone))}"
            "&netWay=Wifi"
            "&version=android@11.0800"
            f"&deviceId={self.device_id}"
            f"&password={quote(self.rsa(code))}"
            "&keyVersion="
            "&provinceChanel=general"
            f"&appId={self.appid}"
            "&deviceModel=M2007J3SC"
            f"&androidId={self.device_id[:16]}"
            "&deviceBrand=Xiaomi"
            f"&timestamp={timestamp}"
        )
        return self.post_form(url, post_data)


PAGE = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>运营商登录态获取</title>
  <script src="https://turing.captcha.qcloud.com/TJCaptcha.js"></script>
  <style>
    :root {
      color-scheme: light;
      --ink: #19202a;
      --muted: #6b7280;
      --line: #d8dee8;
      --paper: #ffffff;
      --wash: #f5f7fb;
      --accent: #0a7c66;
      --accent-dark: #07614f;
      --warn: #a15c00;
      --danger: #b42318;
      --ok: #087443;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #f7f9fc 0%, #edf2f7 100%);
      color: var(--ink);
      display: grid;
      place-items: start center;
      padding: 28px 14px;
    }
    .shell {
      width: min(480px, 100%);
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 14px 40px rgba(25, 32, 42, .08);
      overflow: hidden;
    }
    .head {
      padding: 20px 22px 14px;
      border-bottom: 1px solid var(--line);
    }
    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .sub {
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    .body { padding: 18px 22px 22px; }
    label {
      display: block;
      font-size: 13px;
      color: #374151;
      margin: 0 0 7px;
      font-weight: 650;
    }
    input {
      width: 100%;
      height: 44px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 12px;
      font-size: 16px;
      color: var(--ink);
      background: #fff;
      outline: none;
    }
    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(10, 124, 102, .12);
    }
    .field { margin-bottom: 14px; }
    .row {
      display: grid;
      grid-template-columns: 1fr 128px;
      gap: 10px;
      align-items: end;
    }
    button {
      height: 44px;
      border: 0;
      border-radius: 6px;
      padding: 0 14px;
      color: white;
      background: var(--accent);
      font-weight: 750;
      font-size: 14px;
      cursor: pointer;
      white-space: nowrap;
    }
    button:hover { background: var(--accent-dark); }
    button:disabled {
      cursor: wait;
      opacity: .68;
    }
    .secondary { background: #334155; }
    .secondary:hover { background: #1f2937; }
    .copy-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
      margin-top: 12px;
    }
    .message {
      display: none;
      margin: 14px 0 0;
      padding: 11px 12px;
      border-radius: 6px;
      font-size: 13px;
      line-height: 1.45;
      border: 1px solid transparent;
    }
    .message.show { display: block; }
    .message.ok { color: var(--ok); background: #ecfdf3; border-color: #abefc6; }
    .message.err { color: var(--danger); background: #fef3f2; border-color: #fecdca; }
    .result {
      display: none;
      margin-top: 16px;
      border-top: 1px solid var(--line);
      padding-top: 16px;
    }
    .result.show { display: block; }
    .token {
      padding: 12px;
      background: #101828;
      color: #e5edf7;
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      line-height: 1.55;
      word-break: break-all;
      min-height: 54px;
    }
    .kv {
      margin-top: 10px;
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 12px;
    }
    .footer {
      padding: 12px 22px;
      background: var(--wash);
      border-top: 1px solid var(--line);
      color: var(--warn);
      font-size: 12px;
      line-height: 1.5;
    }
    @media (max-width: 420px) {
      .row, .copy-row { grid-template-columns: 1fr; }
      body { padding: 12px; }
      .head, .body, .footer { padding-left: 16px; padding-right: 16px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="head">
      <h1>运营商登录态获取</h1>
      <div class="sub">短信验证码登录，成功后复制 token_online#appid 到 chinaUnicomCookie。</div>
    </section>
    <section class="body">
      <div class="field">
        <label for="phone">手机号</label>
        <input id="phone" inputmode="numeric" maxlength="11" autocomplete="tel" placeholder="请输入 11 位手机号">
      </div>
      <div class="row field">
        <div>
          <label for="code">短信验证码</label>
          <input id="code" inputmode="numeric" maxlength="6" autocomplete="one-time-code" placeholder="6 位验证码">
        </div>
        <button id="sendBtn" type="button">发送验证码</button>
      </div>
      <button id="loginBtn" type="button" style="width:100%">登录并生成 Token</button>
      <div id="msg" class="message"></div>
      <section id="result" class="result">
        <label>chinaUnicomCookie</label>
        <div id="simpleToken" class="token"></div>
        <div class="copy-row">
          <button id="copySimple" type="button">复制 token_online#appid</button>
          <button id="copyFull" class="secondary" type="button">复制完整 JSON</button>
          <button id="clearHistory" class="secondary" type="button">清除记录</button>
        </div>
        <div id="details" class="kv"></div>
      </section>
    </section>
    <section class="footer">只建议本地或内网使用。不要把服务暴露到公网，token 相当于登录态。</section>
  </main>

  <script>
    const CAPTCHA_APPID = "195809716";
    const $ = (id) => document.getElementById(id);
    let lastResult = null;

    function setBusy(id, busy, text) {
      const btn = $(id);
      btn.disabled = busy;
      if (text) btn.textContent = text;
    }

    function message(text, type = "err") {
      const box = $("msg");
      box.textContent = text || "";
      box.className = "message show " + (type === "ok" ? "ok" : "err");
    }

    function cleanPhone() {
      const phone = $("phone").value.replace(/\D/g, "").slice(0, 11);
      $("phone").value = phone;
      return phone;
    }

    function cleanCode() {
      const code = $("code").value.replace(/\D/g, "").slice(0, 6);
      $("code").value = code;
      return code;
    }

    async function postJSON(url, payload) {
      const response = await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      return response.json();
    }

    async function sendCode(resultToken = "") {
      const phone = cleanPhone();
      if (phone.length !== 11) {
        message("请输入 11 位手机号");
        return;
      }
      setBusy("sendBtn", true, "发送中");
      try {
        const data = await postJSON("/api/send", {phone, resultToken});
        if (data.status === "success") {
          message(data.msg || "验证码已发送", "ok");
        } else if (data.status === "need_captcha") {
          message(data.msg || "需要安全验证");
          await startCaptcha(phone, data.mobile || "");
        } else {
          message(data.msg || "发送失败");
        }
      } catch (err) {
        message("请求失败，请检查服务是否正常运行");
      } finally {
        setBusy("sendBtn", false, "发送验证码");
      }
    }

    async function startCaptcha(phone, mobileHex) {
      if (typeof TencentCaptcha !== "function") {
        message("腾讯验证码组件加载失败，请刷新页面或检查网络");
        return;
      }
      const captcha = new TencentCaptcha(CAPTCHA_APPID, async function(res) {
        if (res.ret !== 0) {
          message("已取消安全验证");
          return;
        }
        try {
          const validated = await postJSON("/api/validate", {
            phone,
            mobile: mobileHex,
            ticket: res.ticket,
            randstr: res.randstr
          });
          if (validated.status === "success" && validated.resultToken) {
            await sendCode(validated.resultToken);
          } else {
            message(validated.msg || "安全验证失败");
          }
        } catch (err) {
          message("安全验证请求失败");
        }
      });
      captcha.show();
    }

    async function login() {
      const phone = cleanPhone();
      const code = cleanCode();
      if (phone.length !== 11 || code.length < 4) {
        message("请填写手机号和短信验证码");
        return;
      }
      setBusy("loginBtn", true, "登录中");
      $("result").classList.remove("show");
      try {
        const data = await postJSON("/api/login", {phone, code});
        if (data.status !== "success") {
          message(data.msg || "登录失败");
          return;
        }
        renderResult(data, "本次获取");
        message("登录成功，已生成 token_online#appid", "ok");
      } catch (err) {
        message("请求失败，请检查服务是否正常运行");
      } finally {
        setBusy("loginBtn", false, "登录并生成 Token");
      }
    }

    async function copyText(text) {
      if (!text) {
        message("没有可复制的数据");
        return;
      }
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          message("已复制到剪贴板", "ok");
          return;
        }
      } catch (err) {
        // Fall back below.
      }
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      area.style.top = "0";
      document.body.appendChild(area);
      area.focus();
      area.select();
      area.setSelectionRange(0, area.value.length);
      const ok = document.execCommand("copy");
      document.body.removeChild(area);
      message(ok ? "已复制到剪贴板" : "复制失败，请手动选中复制", ok ? "ok" : "err");
    }

    function renderResult(data, label) {
      lastResult = data;
      $("simpleToken").textContent = data.simple || data.chinaUnicomCookie || "";
      const created = data.created_at ? new Date(data.created_at * 1000).toLocaleString() : "";
      $("details").innerHTML = `
        <div>来源：${label || "历史记录"}</div>
        <div>手机号：${data.phone || ""}</div>
        <div>保存时间：${created || "刚刚"}</div>
        <div>token_online 长度：${(data.token_online || "").length}</div>
        <div>ecs_token 长度：${(data.ecs_token || "").length}</div>
        <div>appid 长度：${(data.appid || "").length}</div>
      `;
      $("result").classList.add("show");
    }

    async function loadHistory() {
      try {
        const response = await fetch("/api/history");
        const data = await response.json();
        if (data.status === "success" && data.latest) {
          renderResult(data.latest, "上次获取");
          message("已加载上次获取记录", "ok");
        }
      } catch (err) {
        // History is optional.
      }
    }

    async function clearSavedHistory() {
      try {
        const data = await postJSON("/api/clear", {});
        if (data.status === "success") {
          lastResult = null;
          $("simpleToken").textContent = "";
          $("details").innerHTML = "";
          $("result").classList.remove("show");
          message("本机保存记录已清除", "ok");
        } else {
          message(data.msg || "清除失败");
        }
      } catch (err) {
        message("清除失败，请检查服务是否正常运行");
      }
    }

    $("phone").addEventListener("input", cleanPhone);
    $("code").addEventListener("input", cleanCode);
    $("sendBtn").addEventListener("click", () => sendCode(""));
    $("loginBtn").addEventListener("click", login);
    $("copySimple").addEventListener("click", () => copyText(lastResult && (lastResult.simple || lastResult.chinaUnicomCookie)));
    $("copyFull").addEventListener("click", () => copyText(JSON.stringify(lastResult, null, 2)));
    $("clearHistory").addEventListener("click", clearSavedHistory);
    loadHistory();
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/history", methods=["GET"])
def history():
    items = read_history()
    latest = items[0] if items else None
    return jsonify({"status": "success", "latest": latest, "items": items})


@app.route("/api/clear", methods=["POST"])
def clear_saved_history():
    ok = clear_history()
    return jsonify({"status": "success" if ok else "fail", "msg": "已清除" if ok else "清除失败"})


@app.route("/api/send", methods=["POST"])
def send_code():
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(data.get("phone"))
    result_token = str(data.get("resultToken") or "")
    if not phone:
        return json_error("手机号格式不正确")

    device_id, appid = session_state()
    client = UnicomAndroid(phone, appid, device_id)
    upstream = client.send_code(result_token)

    code = str(upstream.get("code", "") or upstream.get("rsp_code", ""))
    desc = upstream.get("dsc") or upstream.get("msg") or upstream.get("desc") or upstream.get("rsp_desc") or ""

    ok = code in {"0", "0000"} or str(upstream.get("status", "")) == "success"
    if ok:
        return jsonify({"status": "success", "msg": "验证码已发送"})

    need_captcha = code in {"ECS99998", "ECS99999"} or "ECS1164" in str(desc)
    if need_captcha:
        mobile_hex = upstream.get("mobile", "")
        if mobile_hex:
            session["mobile_hex"] = mobile_hex
        return jsonify({
            "status": "need_captcha",
            "msg": desc or "需要安全验证",
            "mobile": mobile_hex,
            "url": upstream.get("url", ""),
        })

    return jsonify({
        "status": "fail",
        "msg": desc or "验证码发送失败",
        "code": code,
    })


@app.route("/api/validate", methods=["POST"])
def validate_captcha():
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(data.get("phone"))
    ticket = str(data.get("ticket") or "")
    rand_str = str(data.get("randstr") or "")
    mobile_hex = str(data.get("mobile") or session.get("mobile_hex") or "")

    if not phone:
        return json_error("手机号格式不正确")
    if not ticket or not rand_str:
        return json_error("缺少腾讯验证码参数")
    if not mobile_hex:
        return json_error("缺少上游风控 mobile 参数，请重新发送验证码")

    device_id, appid = session_state()
    client = UnicomAndroid(phone, appid, device_id)
    upstream = client.validate_captcha(mobile_hex, ticket, rand_str)

    if str(upstream.get("code", "")) == "0000":
        result_token = (upstream.get("data") or {}).get("resultToken", "")
        if result_token:
            session["result_token"] = result_token
            return jsonify({"status": "success", "resultToken": result_token})

    msg = upstream.get("msg") or upstream.get("dsc") or upstream.get("desc") or "安全验证失败"
    return jsonify({"status": "fail", "msg": msg})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(data.get("phone"))
    code = re.sub(r"\D", "", str(data.get("code") or ""))
    if not phone:
        return json_error("手机号格式不正确")
    if len(code) < 4:
        return json_error("短信验证码格式不正确")

    device_id, appid = session_state()
    client = UnicomAndroid(phone, appid, device_id)
    upstream = client.login(code)

    result_code = str(upstream.get("code", ""))
    if result_code in {"0", "0000"}:
        token_online = upstream.get("token_online", "")
        ecs_token = upstream.get("ecs_token", "")
        if not token_online:
            return jsonify({"status": "fail", "msg": "登录成功但响应缺少 token_online"})
        simple = f"{token_online}#{appid}"
        result = {
            "status": "success",
            "phone": phone,
            "token_online": token_online,
            "ecs_token": ecs_token,
            "appid": appid,
            "simple": simple,
            "chinaUnicomCookie": simple,
            "created_at": int(time.time()),
        }
        append_history(result)
        return jsonify(result)

    msg = upstream.get("desc") or upstream.get("msg") or upstream.get("dsc") or "登录失败"
    return jsonify({"status": "fail", "msg": f"{msg} [Code:{result_code}]"})


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5123"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host=host, port=port)
