import asyncio
import aiohttp
import json
import random
import time
import logging
import re
import os  # 添加这一行
import sys
from typing import List, Dict, Any

# 设置控制台输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')
# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BiliAPI:
    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://t.bilibili.com/',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site'
        }
        self.name = None
        self.uid = None
        self.session = None
        cookie_string = '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
        self.headers['Cookie'] = cookie_string

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def login(self):
        try:
            print("正在连接B站API...")
            async with self.session.get('https://api.bilibili.com/x/web-interface/nav') as response:
                data = await response.json()
                
                if data['code'] == 0:
                    self.name = data['data']['uname']
                    self.uid = data['data']['mid']
                    print(f"登录成功!")
                    print(f"用户名: {self.name}")
                    print(f"UID: {self.uid}")
                    print(f"等级: {data['data']['level_info']['current_level']}")
                    print(f"硬币: {data['data']['money']}")
                    return True
                else:
                    print(f"登录失败! 错误信息: {data['message']}")
                    return False
                    
        except Exception as e:
            print(f"登录错误: {str(e)}")
            return False

    async def get_followings(self, page: int = 1) -> dict:
        '''获取关注列表'''
        try:
            url = f'https://api.bilibili.com/x/relation/followings?vmid={self.uid}&pn={page}&ps=50'
            async with self.session.get(url) as response:
                return await response.json()
        except Exception as e:
            print(f"获取关注列表失败: {e}")
            return {"code": -1}

    async def get_user_dynamics(self, uid: int, offset: str = '') -> dict:
        '''获取用户动态'''
        try:
            url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?offset={offset}&host_mid={uid}&timezone_offset=-480'
            headers = {
                **self.headers,
                'Origin': 'https://space.bilibili.com',
                'Referer': f'https://space.bilibili.com/{uid}/dynamic'
            }
            async with self.session.get(url, headers=headers) as response:
                return await response.json()
        except Exception as e:
            print(f"获取动态失败: {e}")
            return {"code": -1}

    async def repost_dynamic(self, dynamic_id: str, content: str, retry_times: int = 3) -> dict:
        '''转发动态'''
        for i in range(retry_times):
            try:
                url = 'https://api.bilibili.com/x/dynamic/feed/create/dyn'
                
                json_data = {
                    "dyn_req": {
                        "content": {
                            "contents": [
                                {
                                    "raw_text": content,
                                    "type": 1,
                                    "biz_id": ""
                                }
                            ]
                        },
                        "scene": 4,
                        "attach_card": None,
                        "upload_id": f"{self.uid}_{int(time.time())}_{random.randint(1000, 9999)}",
                        "meta": {
                            "app_meta": {
                                "from": "create.dynamic.web",
                                "mobi_app": "web"
                            }
                        }
                    },
                    "web_repost_src": {
                        "dyn_id_str": str(dynamic_id)
                    }
                }
                
                headers = {
                    **self.headers,
                    'authority': 'api.bilibili.com',
                    'content-type': 'application/json',
                    'origin': 'https://t.bilibili.com',
                    'referer': 'https://t.bilibili.com/',
                    'accept': 'application/json, text/plain, */*',
                }
                
                params = {
                    'platform': 'web',
                    'csrf': self.cookies['bili_jct'],
                    'web_location': '333.999'
                }
                
                async with self.session.post(url, json=json_data, headers=headers, params=params) as response:
                    text = await response.text()
                    try:
                        json_data = json.loads(text)
                        if json_data['code'] == 0:
                            print(f"转发成功! 内容: {content}")
                            return json_data
                        elif i < retry_times - 1:
                            print(f"转发失败，正在重试: {json_data.get('message', '未知错误')}")
                            await asyncio.sleep(3)
                        else:
                            return json_data
                    except json.JSONDecodeError:
                        print(f"服务器响应: {text[:200]}")
                        if i < retry_times - 1:
                            await asyncio.sleep(3)
                        else:
                            return {"code": -1, "message": "服务器返回非JSON数据"}
            except Exception as e:
                if i < retry_times - 1:
                    print(f"转发出错，正在重试: {str(e)}")
                    await asyncio.sleep(3)
                else:
                    return {"code": -1, "message": str(e)}
        return {"code": -1, "message": "重试次数用尽"}

    async def dynamic_reply(self, oid: str, message: str, type: int = 17) -> dict:
        '''评论动态'''
        try:
            url = 'https://api.bilibili.com/x/v2/reply/add'
            data = {
                'oid': oid,
                'type': type,
                'message': message,
                'csrf': self.cookies['bili_jct']
            }
            headers = {
                **self.headers,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://t.bilibili.com'
            }
            async with self.session.post(url, data=data, headers=headers) as response:
                return await response.json()
        except Exception as e:
            print(f"评论失败: {e}")
            return {"code": -1, "message": str(e)}

    async def dynamic_like(self, dynamic_id: str) -> dict:
        '''点赞动态'''
        try:
            url = 'https://api.bilibili.com/x/dynamic/feed/dyn/thumb'
            
            json_data = {
                "dyn_id_str": str(dynamic_id),
                "up": 1
            }
            
            headers = {
                **self.headers,
                'authority': 'api.bilibili.com',
                'content-type': 'application/json',
                'origin': 'https://t.bilibili.com',
                'referer': 'https://t.bilibili.com/',
                'accept': 'application/json, text/plain, */*'
            }
            
            params = {
                'csrf': self.cookies['bili_jct']
            }
            
            async with self.session.post(url, json=json_data, headers=headers, params=params) as response:
                text = await response.text()
                try:
                    json_data = json.loads(text)
                    if json_data['code'] == 0:
                        print("点赞成功!")
                        return json_data
                    else:
                        print(f"点赞失败: {json_data.get('message', '未知错误')}")
                        return json_data
                except json.JSONDecodeError:
                    print(f"服务器响应: {text[:200]}")
                    return {"code": -1, "message": "服务器返回非JSON数据"}
        except Exception as e:
            print(f"点赞失败: {e}")
            return {"code": -1, "message": str(e)}

async def process_account(account: dict):
    """处理单个账号的任务"""
    print(f"\n开始处理账号 {account['DedeUserID']}")
    async with BiliAPI(account) as biliapi:
        if await biliapi.login():
            await lottery_task(biliapi)

async def lottery_task(biliapi: BiliAPI):
    config = {
        "reply": ["今天是个好日子中奖的好日子", "最可爱的就是这个啦,我超级喜欢",
                 "我们都是好朋友，我相信你还记得的，嘤嘤嘤","给我也整一个,我太爱了"],
        "repost": ["今天是个好日子中奖的好日子", "最可爱的就是这个啦,我超级喜欢",
                  "我们都是好朋友，我相信你还记得的，嘤嘤嘤","给我也整一个,我太爱了"],
        "keywords": ["^((?!恭喜).)*#互动抽奖#((?!恭喜).)*$", "^((?!恭喜).)*#抽奖#((?!恭喜).)*$",
                    ".*(转|抽|评).*(转|抽|评).*(转|抽|评).*"],
        "delay": [53, 337]
    }

    keywords = [re.compile(x, re.S) for x in config["keywords"]]
    
    print("\n开始获取关注列表...")
    follow_list = []
    page = 1
    while True:
        ret = await biliapi.get_followings(page)
        if ret["code"] == 0:
            if not ret["data"]["list"]:
                break
            follow_list.extend([x["mid"] for x in ret["data"]["list"]])
            print(f"已获取第{page}页关注列表，当前共{len(follow_list)}个")
            page += 1
            await asyncio.sleep(1)
        else:
            print(f"获取关注列表第{page}页失败")
            break

    print(f"成功获取{len(follow_list)}个关注的UP主")

    success_count = 0
    fail_count = 0
    processed_dynamics = set()
    current_time = int(time.time())

    for up_id in follow_list:
        try:
            print(f"\n检查UP主 {up_id} 的动态...")
            offset = ''
            
            while True:
                ret = await biliapi.get_user_dynamics(up_id, offset)
                if ret["code"] != 0:
                    print(f"获取UP主 {up_id} 动态失败: {ret.get('message', '未知错误')}")
                    break

                if not ret["data"].get("items"):
                    break

                for dynamic in ret["data"]["items"]:
                    try:
                        if not all(key in dynamic for key in ["id_str", "modules"]):
                            continue

                        dynamic_id = dynamic["id_str"]
                        if dynamic_id in processed_dynamics:
                            continue

                        # 检查动态内容
                        if "module_dynamic" not in dynamic["modules"]:
                            continue

                        content = ""
                        module_dynamic = dynamic["modules"]["module_dynamic"]
                        if module_dynamic and isinstance(module_dynamic, dict):
                            desc = module_dynamic.get("desc", {})
                            if isinstance(desc, dict):
                                content = desc.get("text", "")

                        if not content:
                            continue

                        # 检查是否是抽奖动态
                        is_lottery = False
                        for pattern in keywords:
                            if re.match(pattern, content):
                                is_lottery = True
                                break

                        if is_lottery:
                            print(f"\n发现抽奖动态: {content[:50]}...")
                            processed_dynamics.add(dynamic_id)

                            # 执行转发
                            print("开始转发...")
                            repost_content = random.choice(config["repost"])
                            repost_ret = await biliapi.repost_dynamic(dynamic_id, repost_content)
                            if repost_ret["code"] == 0:
                                print(f"转发成功! 内容: {repost_content}")
                                success_count += 1
                            else:
                                print(f"转发失败: {repost_ret.get('message', '未知错误')}")
                                fail_count += 1

                            # 评论
                            await asyncio.sleep(2)
                            print("开始评论...")
                            reply_content = random.choice(config["reply"])
                            reply_ret = await biliapi.dynamic_reply(dynamic_id, reply_content)
                            if reply_ret["code"] == 0:
                                print(f"评论成功! 内容: {reply_content}")
                            else:
                                print(f"评论失败: {reply_ret.get('message', '未知错误')}")

                            # 点赞
                            await asyncio.sleep(2)
                            print("开始点赞...")
                            like_ret = await biliapi.dynamic_like(dynamic_id)
                            if like_ret["code"] == 0:
                                print("点赞成功!")
                            else:
                                print(f"点赞失败: {like_ret.get('message', '未知错误')}")

                            # 组操作完成后的延迟
                            delay = random.randint(config["delay"][0], config["delay"][1])
                            print(f"本组操作完成，等待 {delay} 秒后继续下一组...")
                            await asyncio.sleep(delay)

                    except Exception as e:
                        print(f"处理动态时出错: {str(e)}")
                        continue

                # 处理翻页
                if "offset" in ret["data"] and ret["data"]["offset"]:
                    offset = ret["data"]["offset"]
                    await asyncio.sleep(2)
                else:
                    break

        except Exception as e:
            print(f"处理UP主 {up_id} 时出错: {str(e)}")
            continue

    print(f"\n任务完成! 成功转发: {success_count}, 失败: {fail_count}")

async def main():
    # 从环境变量获取 cookies 字符串并转换为 JSON
    cookies_str = os.environ["BILIBILI_COOKIES"]
    accounts = json.loads(cookies_str)

    # 创建所有账号的任务
    tasks = [process_account(account) for account in accounts]
    # 同时执行所有任务
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    print("程序启动")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
    print("程序结束")
