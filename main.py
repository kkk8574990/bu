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
                    return await response.json()
                    
            except Exception as e:
                if i < retry_times - 1:
                    print(f"转发出错，正在重试: {str(e)}")
                    await asyncio.sleep(3)
                else:
                    return {"code": -1, "message": str(e)}

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
            url = 'https://api.bilibili.com/x/dynamic/feed/dyn/thumb'
            
            # 新的参数格式
            data = {
                'dynamic_id': str(dynamic_id),  # 改为 dynamic_id
                'up': 1,  # 1是点赞，2是取消点赞
                'csrf': self.cookies['bili_jct']
            }
            
            headers = {
                **self.headers,
                'authority': 'api.bilibili.com',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://t.bilibili.com',
                'referer': 'https://t.bilibili.com/',
                'accept': 'application/json, text/plain, */*'
            }
            
            async with self.session.post(url, data=data) as response:
                return await response.json()
        except Exception as e:
            print(f"点赞失败: {e}")
            return {"code": -1}
async def get_dynamic(biliapi: BiliAPI, uid: int = None):
    """获取动态的生成器函数"""
    offset = ''
    while True:
        try:
            if uid is None:
                uid = biliapi.uid

            ret = await biliapi.get_user_dynamics(uid, offset)
            
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
                if not dynamic.get("id_str") or not dynamic.get("modules"):
                    continue
                yield dynamic

            if ret["data"].get("has_more") and ret["data"].get("offset"):
                offset = ret["data"]["offset"]
                await asyncio.sleep(5)
            else:
                break

        except Exception as e:
            print(f"获取动态出错: {str(e)}")
            break

async def get_dynamic(biliapi: BiliAPI, uid: int = None):
    """获取动态的生成器函数"""
    offset = ''
    while True:
        try:
            if uid is None:
                uid = biliapi.uid

            ret = await biliapi.get_user_dynamics(uid, offset)
            
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
                if not dynamic.get("id_str") or not dynamic.get("modules"):
                    continue
                yield dynamic

            if ret["data"].get("has_more") and ret["data"].get("offset"):
                offset = ret["data"]["offset"]
                await asyncio.sleep(5)
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
        "interval": (8, 12),
        "check_interval": [15, 32]
    }

    # 计算7天前的时间戳
    now_time = int(time.time())
    seven_days_ago = now_time - 7 * 24 * 3600
    
    print(f"\n时间区间：")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_time))}")
    print(f"7天前时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(seven_days_ago))}")

    keywords = [re.compile(x, re.S) for x in config["keywords"]]
    
    # 获取完整关注列表
    # 获取完整关注列表
    print("\n开始获取关注列表...")
    follow_list = []
    page = 1
    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
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
                retry_count = 0  # 成功后重置重试计数
            else:
                retry_count += 1
                print(f"获取关注列表第{page}页失败，将在10秒后重试... ({retry_count}/{max_retries})")
                await asyncio.sleep(10)
        except Exception as e:
            retry_count += 1
            print(f"获取关注列表出错: {str(e)}，将在10秒后重试... ({retry_count}/{max_retries})")
            await asyncio.sleep(10)

    total_follows = len(follow_list)
    if total_follows == 0:
        print("未能获取到任何关注列表，退出任务")
        return
        
    print(f"成功获取{total_follows}个关注的UP主")
    
    # 根据星期几来划分关注列表
    weekday = time.localtime().tm_wday  # 0-6，0是周一
    section_size = 500  # 每次处理的关注数量
    total_sections = max(1, (total_follows + section_size - 1) // section_size)  # 确保至少有1个分段
    current_section = weekday % total_sections  # 根据星期确定处理哪一段
    
    start_idx = current_section * section_size
    end_idx = min(start_idx + section_size, total_follows)
    
    # 获取今天要处理的关注列表片段
    follow_list_section = follow_list[start_idx:end_idx]
    print(f"\n今天是星期{weekday + 1}，将处理第{current_section + 1}段关注列表")
    print(f"处理范围: {start_idx + 1}-{end_idx}，共{len(follow_list_section)}个UP主")
    
    if not follow_list_section:
        print("当前分段没有需要处理的UP主，退出任务")
        return
    
    # 随机打乱当前段的关注列表顺序
    random.shuffle(follow_list_section)

    # 记录已经转发过的动态ID
    already_repost_dyid = set()
    success_count = 0
    fail_count = 0
    processed_dynamics = set()

    # 首先获取自己的转发动态列表
    print("\n开始获取已转发动态列表...")
    async for x in get_dynamic(biliapi, biliapi.uid):
        try:
            module_author = x.get("module_author", {})
            module_dynamic = x.get("modules", {}).get("module_dynamic", {})
            
            # 检查是否是转发的动态
            if (module_author.get("mid") == biliapi.uid and  
                module_dynamic.get("type") == "DYNAMIC_TYPE_FORWARD"):
                # 获取原动态ID
                orig_dy_id = module_dynamic.get("orig_dy_id_str")
                if orig_dy_id and orig_dy_id != '0':
                    already_repost_dyid.add(int(orig_dy_id))
                    print(f"记录到已转发动态: {orig_dy_id}")
        except Exception as e:
            print(f"处理已转发动态时出错: {str(e)}")
            continue
    
    print(f"共记录到 {len(already_repost_dyid)} 个已转发动态")

    # 处理新动态
    print("\n开始处理新动态...")
    for up_id in follow_list_section:
        try:
            wait_time = random.uniform(config['check_interval'][0], config['check_interval'][1])
            print(f"\n将在 {wait_time:.1f} 秒后检查UP主 {up_id} 的动态...")
            await asyncio.sleep(wait_time)
            
            async for dynamic in get_dynamic(biliapi, up_id):
                try:
                    # 基本信息检查
                    dynamic_id = dynamic["id_str"]
                    modules = dynamic["modules"]
                    
                    # 获取时间戳
                    module_author = modules.get("module_author", {})
                    pub_ts = module_author.get("pub_ts")
                    if not pub_ts:
                        pub_ts = int(str(dynamic_id)[:10])
                    
                    # 获取动态类型并判断是否是视频动态
                    module_dynamic = modules.get("module_dynamic", {})
                    major = module_dynamic.get("major", {})
                    if major and major.get("type") == "MAJOR_TYPE_ARCHIVE":
                        continue
                    
                    # 检查是否在七天内
                    if pub_ts < seven_days_ago:
                        print(f"动态时间超过7天，停止检查该UP主")
                        break

                    # 检查是否已经转发
                    if int(dynamic_id) in already_repost_dyid:
                        print(f"动态 {dynamic_id} 已经转发过，跳过")
                        continue
                    
                    if dynamic_id in processed_dynamics:
                        continue

                    # 获取动态内容
                    desc = module_dynamic.get("desc", {})
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
                        print(f"动态时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pub_ts))}")
                        processed_dynamics.add(dynamic_id)

                        # 转发，增加标签处理
                        print("开始转发...")
                        # 提取动态中的标签
                        tags = re.findall(r'#([^#]+)#', content)
                        repost_content = random.choice(config["repost"])
                        if tags:
                            tags = [f"#{tag}#" for tag in tags if tag not in ["互动抽奖", "抽奖"]]
                            repost_content = f"{repost_content} {' '.join(tags)}"

                        repost_ret = await biliapi.repost_dynamic(dynamic_id, repost_content)
                        if repost_ret["code"] == 0:
                            print(f"转发成功! 内容: {repost_content}")
                            success_count += 1
                            already_repost_dyid.add(int(dynamic_id))
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

        except Exception as e:
            print(f"处理UP主 {up_id} 时出错: {str(e)}")
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
    cookies_str = os.environ.get("BILIBILI_COOKIES")
    if not cookies_str:
        print("未找到 BILIBILI_COOKIES 环境变量")
        return
        
    try:
        accounts = json.loads(cookies_str)
    except json.JSONDecodeError:
        print("BILIBILI_COOKIES 格式错误")
        return

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
