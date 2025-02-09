from nonebot.plugin import PluginMetadata
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import textwrap
import asyncio

from nonebot import get_driver, on_command, on_message, get_bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_localstore import get_data_dir

__plugin_meta__ = PluginMetadata(
    name="复读统计",
    description="群聊复读行为统计，支持复读排行/被复读排行/热词统计",
    usage="发送 '复读排行'/'被复读排行'/'复读词排行' + [时段类型] 查看统计",
    type="application",
    homepage="https://github.com/name-is-hard-to-make/nonebot-plugin-repeater-count",
    supported_adapters={"~onebot.v11"},
)

# 字体路径配置（需要实际存在的字体文件）
FONT_PATH = "fonts/simhei.ttf"  # 请替换为实际字体路径

# 数据结构类型定义
RepData = Dict[str, Dict[str, Dict[str, Dict[str, int]]]]

class Recorder:
    def __init__(self):
        data_dir = get_data_dir("repeater_count")
        self.data_path = data_dir / "repeater_data.json"
        self.last_message: Dict[int, Tuple[str, int]] = {}
        self.data: RepData = {"total": {}}
        self.name_cache: Dict[int, Dict[int, str]] = {}

        data_dir.mkdir(parents=True, exist_ok=True)
        self.load_data()

    def load_data(self):
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

    def save_data(self):
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_period_keys(self) -> Dict[str, str]:
        now = datetime.now()
        return {
            "total": "total",
            "year": str(now.year),
            "month": f"{now.year}-{now.month:02d}",
            "day": f"{now.year}-{now.month:02d}-{now.day:02d}"
        }

    def update_data(self, group_id: int, user_id: int, message: str):
        group_id_str = str(group_id)
        user_id_str = str(user_id)
        periods = self.get_period_keys()

        last_msg, last_user = self.last_message.get(group_id, ("", 0))

        if message == last_msg and user_id != last_user:
            victim_id_str = str(last_user)

            for period in periods.values():
                if group_id_str not in self.data:
                    self.data[group_id_str] = {}
                group_data = self.data[group_id_str]

                if period not in group_data:
                    group_data[period] = {
                        "users": {},
                        "words": {},
                        "victims": {}
                    }
                group_data[period]["users"][user_id_str] = group_data[period]["users"].get(user_id_str, 0) + 1
                group_data[period]["victims"][victim_id_str] = group_data[period]["victims"].get(victim_id_str, 0) + 1
                group_data[period]["words"][message] = group_data[period]["words"].get(message, 0) + 1

            self.last_message[group_id] = (message, user_id)
            self.save_data()
        else:
            self.last_message[group_id] = (message, user_id)

    async def get_user_name(self, group_id: int, user_id: int) -> str:
        if group_id not in self.name_cache:
            self.name_cache[group_id] = {}
        
        if user_id not in self.name_cache[group_id]:
            try:
                bot = get_bot()
                member_info = await bot.get_group_member_info(
                    group_id=group_id,
                    user_id=user_id,
                    no_cache=True
                )
                name = member_info.get('card') or member_info.get('nickname', str(user_id))
                self.name_cache[group_id][user_id] = name
            except Exception:
                return str(user_id)
        return self.name_cache[group_id][user_id]

recorder = Recorder()
repeater_matcher = on_message(priority=10, block=False)

@repeater_matcher.handle()
async def handle_repeater(event: GroupMessageEvent):
    message = event.get_plaintext().strip()
    if message:
        recorder.update_data(
            group_id=event.group_id,
            user_id=event.user_id,
            message=message
        )

victim_rank = on_command("被复读排行", aliases={"受害者排行"}, priority=5, block=True)
rep_rank = on_command("复读排行", aliases={"复读统计"}, priority=5, block=True)
word_rank = on_command("复读词排行", priority=5, block=True)

async def generate_bar_chart(title: str, data: List[Tuple[str, int]]) -> Optional[Path]:
    try:
        img_width = 1000
        img_height = 800
        img = Image.new('RGB', (img_width, img_height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype(FONT_PATH, 28)
            text_font = ImageFont.truetype(FONT_PATH, 24)
            small_font = ImageFont.truetype(FONT_PATH, 20)
        except IOError:
            font = ImageFont.load_default()
            title_font = text_font = small_font = font

        title_lines = textwrap.wrap(title, width=20)
        title_height = len(title_lines) * 30
        for i, line in enumerate(title_lines):
            draw.text((img_width//2, 40 + i*30), 
                     line, fill=(0, 0, 0), 
                     font=title_font, anchor='mt')

        max_count = max((count for _, count in data), default=1)
        bar_height = 40
        spacing = 25
        start_y = 60 + title_height

        for index, (name, count) in enumerate(data[:10]):
            y = start_y + index * (bar_height + spacing)
            
            max_name_width = 250  
            name_lines = []
            current_line = []
            current_width = 0
            
            for char in f"{index+1}. {name}":
                char_width = text_font.getlength(char)
                if current_width + char_width > max_name_width and current_line:
                    name_lines.append("".join(current_line))
                    current_line = []
                    current_width = 0
                current_line.append(char)
                current_width += char_width
            if current_line:
                name_lines.append("".join(current_line))

            name_font = text_font if len(name_lines) < 2 else small_font
            for line_num, line in enumerate(name_lines):
                line_y = y + (bar_height - len(name_lines)*name_font.size) // 2 + line_num*name_font.size
                draw.text((50, line_y), 
                         line, 
                         fill=(0, 0, 0), 
                         font=name_font, 
                         anchor='lm')

            bar_max_width = img_width - 350  
            bar_width = int((count / max_count) * bar_max_width)
            bar_x_start = 300
            draw.rectangle([bar_x_start, y, bar_x_start + bar_width, y + bar_height], 
                          fill=(79, 129, 189))
            
            count_text = f"{count}"
            text_width = text_font.getlength(count_text)
            draw.text((bar_x_start + bar_width + 20, y + bar_height//2),
                     count_text,
                     fill=(0, 0, 0),
                     font=text_font,
                     anchor='lm')

        temp_dir = get_data_dir("repeater_count") / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        img.save(file_path)
        return file_path
    except Exception as e:
        print(f"生成图表失败: {str(e)}")
        return None

async def get_rank_data(matcher: Matcher, event: GroupMessageEvent,
                        arg: Message, rank_type: str):
    group_id = event.group_id
    period_type = arg.extract_plain_text().strip() or "total"
    period_map = recorder.get_period_keys()

    if period_type not in period_map:
        await matcher.finish("请使用正确的时段类型：total（默认）、year、month、day")

    period_key = period_map[period_type]
    target_data = recorder.data.get(str(group_id), {}).get(period_key, {})

    if not target_data:
        await matcher.finish("该时段暂无复读数据哦～")

    items = target_data.get(rank_type, {})
    if not items:
        await matcher.finish("该时段暂无相关数据")

    sorted_items = sorted(items.items(), key=lambda x: -x[1])[:10]

    # 转换用户ID为昵称
    display_items = []
    for item in sorted_items:
        identifier, count = item
        if rank_type in ["users", "victims"]:
            try:
                name = await recorder.get_user_name(group_id, int(identifier))
            except:
                name = identifier
        else:
            name = identifier
        display_items.append((name, count))

    # 生成文字结果
    descriptions = {
        "users": "🏆 复读机排行榜",
        "words": "🔥 热词排行榜",
        "victims": "😵 受害者排行榜"
    }
    text_result = f"{descriptions[rank_type]}（{period_key}）\n"
    text_result += "\n".join([f"{i+1}. {name} - {count}次" for i, (name, count) in enumerate(display_items)])

    # 生成并发送图表
    chart_title = f"{descriptions[rank_type]} ({period_key})"
    chart_path = await generate_bar_chart(chart_title, display_items)
    
    if chart_path:
        await matcher.send(MessageSegment.image(chart_path))
    await matcher.finish(text_result)

@victim_rank.handle()
async def handle_victim_rank(event: GroupMessageEvent, arg: Message = CommandArg()):
    await get_rank_data(victim_rank, event, arg, "victims")

@rep_rank.handle()
async def handle_rep_rank(event: GroupMessageEvent, arg: Message = CommandArg()):
    await get_rank_data(rep_rank, event, arg, "users")

@word_rank.handle()
async def handle_word_rank(event: GroupMessageEvent, arg: Message = CommandArg()):
    await get_rank_data(word_rank, event, arg, "words")
