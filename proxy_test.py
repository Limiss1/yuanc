# -*- coding: utf-8 -*-
import requests

# 你本机 V2Ray 代理（完全匹配你的设置）
PROXY = {
    "http": "http://127.0.0.1:10809",
    "https": "http://127.0.0.1:10809"
}

def test_proxy():
    print("=" * 50)
    print("开始测试本机代理 + 币安API")
    print("=" * 50)

    try:
        # 1. 测试当前出口IP（看是不是走了代理）
        print("\n[1/3] 测试代理IP...")
        ip_resp = requests.get("https://api.ipify.org", proxies=PROXY, timeout=10)
        current_ip = ip_resp.text.strip()
        print(f"✅ 当前出口IP: {current_ip}")

        # 2. 测试币安测试接口
        print("\n[2/3] 测试币安公共API...")
        binance_resp = requests.get("https://api.binance.com/api/v3/ping", proxies=PROXY, timeout=10)
        print(f"币安API状态码: {binance_resp.status_code}")
        
        if binance_resp.status_code == 200:
            print("✅ 币安API访问成功！代理完全正常")
        else:
            print(f"❌ 币安API失败，状态码：{binance_resp.status_code}")

        # 3. 测试币安 Demo 接口（你项目里用的）
        print("\n[3/3] 测试你项目的币安Demo接口...")
        demo_resp = requests.get("https://demo-api.binance.com/api/v3/ping", proxies=PROXY, timeout=10)
        print(f"币安DemoAPI状态码: {demo_resp.status_code}")
        
        if demo_resp.status_code == 200:
            print("✅ 你的项目接口可正常访问！")

    except Exception as e:
        print(f"\n❌ 代理连接失败: {str(e)}")

    print("\n" + "=" * 50)

if __name__ == '__main__':
    test_proxy()