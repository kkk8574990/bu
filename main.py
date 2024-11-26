import asyncio
import aiohttp
import json
import random
import time
import logging
import re
import os
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

    async def get_user_dynamics(self, offset: str = '') -> dict:
        '''获取用户动态'''
        try:
            url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?offset={offset}&host_mid={self.uid}&timezone_offset=-480'
            headers = {
                **self.headers,
                'Origin': 'https://space.bilibili.com',
                'Referer': f'https://space.bilibili.com/{self.uid}/dynamic'
            }
            async with self.session.get(url, headers=headers) as response:
                return await response.json()
        except Exception as e:
            print(f"获取动态失败: {e}")
            return {"code": -1}

    async def repost_dynamic(self, dynamic_id: str, content: str) -> dict:
        '''转发动态'''
        try:
            url = 'https://api.bilibili.com/x/dynamic/repost'
            data = {
                'dynamic_id': dynamic_id,
                'content': content,
                'extension': '{"emoji_type":1}',
                'csrf': self.cookies['bili_jct']
            }
            async with self.session.post(url, data=data) as response:
                return await response.json()
        except Exception as e:
            print(f"转发失败: {e}")
            return {"code": -1}

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
            async with self.session.post(url, data=data) as response:
                return await response.json()
        except Exception as e:
            print(f"评论失败: {e}")
            return {"code": -1}

    async def dynamic_like(self, dynamic_id: str) -> dict:
        '''点赞动态'''
        try:
            url = 'https://api.bilibili.com/x/dynamic/like'
            data = {
                'dynamic_id': dynamic_id,
                'up': 1,
                'csrf': self.cookies['bili_jct']
            }
            async with self.session.post(url, data=data) as response:
                return await response.json()
        except Exception as e:
            print(f"点赞失败: {e}")
            return {"code": -1}

async def get_dynamic(biliapi):
    """获取动态的生成器函数"""
    offset = ''
    while True:
        try:
            ret = await biliapi.get_user_dynamics(offset=offset)
            if ret["code"] == -352:
                wait_time = random.uniform(60, 90)
                print(f"遇到风控，将等待 {wait_time:.1f} 秒后继续...")
                await asyncio.sleep(wait_time)
                continue
            elif ret["code"] != 0:
                print(f"获取动态失败: {ret.get('message', '未知错误')}")
                break

            if not ret["data"].get("items"):
                break

            for dynamic in ret["data"]["items"]:
                yield dynamic

            if "offset" in ret["data"] and ret["data"]["offset"]:
                offset = ret["data"]["offset"]
                await asyncio.sleep(2)
            else:
                break

        except Exception as e:
            print(f"获取动态出错: {str(e)}")
            break

async def lottery_task(biliapi: BiliAPI):
    config = {
        "reply": ["今天是个好日子中奖的好日子", "最可爱的就是这个啦,我超级喜欢",
                 "我们都是好朋友，我相信你还记得的，嘤嘤嘤","给我也整一个,我太爱了"],
        "repost": ["今天是个好日子中奖的好日子", "最可爱的就是这个啦,我超级喜欢",
                  "我们都是好朋友，我相信你还记得的，嘤嘤嘤","给我也整一个,我太爱了"],
        "keywords": ["^((?!恭喜).)*#互动抽奖#((?!恭喜).)*$", "^((?!恭喜).)*#抽奖#((?!恭喜).)*$",
                    ".*(转|抽|评).*(转|抽|评).*(转|抽|评).*"],
        "delay": [53, 337],
        "interval": (15, 20)  # 获取关注列表的延迟
    }

    # 计算时间区间（北京时间）
    now_time = int(time.time())
    today_time = now_time - (now_time + 28800) % 86400  # 转换为北京时间的零点
    time_quantum = [-43200, 43200]  # 时间范围：前12小时到后12小时
    start_time = today_time + time_quantum[0]
    end_time = today_time + time_quantum[1]

    print(f"\n时间区间：")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_time))}")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")

    keywords = [re.compile(x, re.S) for x in config["keywords"]]
    
    print("\n开始获取关注列表...")
    follow_list = []
    page = 1
    while True:
        # 添加15-20秒的随机延迟
        wait_time = random.uniform(config['interval'][0], config['interval'][1])
        print(f"将在 {wait_time:.1f} 秒后获取第{page}页关注列表...")
        await asyncio.sleep(wait_time)
        
        ret = await biliapi.get_followings(page)
        if ret["code"] == 0:
            if not ret["data"]["list"]:
                break
            follow_list.extend([x["mid"] for x in ret["data"]["list"]])
            print(f"已获取第{page}页关注列表，当前共{len(follow_list)}个")
            page += 1
        else:
            print(f"获取关注列表第{page}页失败")
            break

    print(f"成功获取{len(follow_list)}个关注的UP主")
    
    # 随机打乱关注列表顺序
    random.shuffle(follow_list)

    success_count = 0
    fail_count = 0
    processed_dynamics = set()

    async for dynamic in get_dynamic(biliapi):
        try:
            dynamic_id = dynamic["id_str"]
            if dynamic_id in processed_dynamics:
                continue
                
            # 检查动态时间是否在指定范围内
            timestamp = dynamic["module_author"]["pub_ts"]
            if timestamp > end_time:
                continue
            elif timestamp < start_time:
                print(f"动态时间早于开始时间，停止检查")
                break

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
                print(f"动态时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}")
                processed_dynamics.add(dynamic_id)

                # 转发
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

                delay = random.randint(config["delay"][0], config["delay"][1])
                print(f"本组操作完成，等待 {delay} 秒后继续...")
                await asyncio.sleep(delay)

        except Exception as e:
            print(f"处理动态时出错: {str(e)}")
            continue

    print(f"\n任务完成! 成功转发: {success_count}, 失败: {fail_count}")

async def process_account(account: dict):
    """处理单个账号的任务"""
    print(f"\n开始处理账号 {account['DedeUserID']}")
    async with BiliAPI(account) as biliapi:
        if await biliapi.login():
            await lottery_task(biliapi)

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
