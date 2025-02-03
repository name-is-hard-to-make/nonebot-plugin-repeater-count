from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="复读统计",
    description="群聊复读行为统计，支持复读排行/被复读排行/热词统计",
    usage="发送 '复读排行'/'被复读排行'/'复读词排行' + [时段类型] 查看统计",
    type="application",
    homepage="https://github.com/name-is-hard-to-make/nonebot-plugin-repeater-count",
    supported_adapters={"~onebot.v11"},
)

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from nonebot import get_driver, on_command, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

# 数据结构类型定义
RepData = Dict[str, Dict[str, Dict[str, Dict[str, int]]]]


class Recorder:
    def __init__(self):
        self.data_path = Path("data/repeater_data.json")
        self.last_message: Dict[int, Tuple[str, int]] = {}  # {group_id: (message, user_id)}
        self.data: RepData = {"total": {}}

        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.load_data()

    def load_data(self):
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                for group in loaded_data.values():
                    for period in group.values():
                        period.setdefault("victims", {})
                self.data = loaded_data

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


@victim_rank.handle()
async def handle_victim_rank(event: GroupMessageEvent, arg: Message = CommandArg()):
    await get_rank_data(victim_rank, event, arg, "victims")


async def get_rank_data(matcher: Matcher, event: GroupMessageEvent,
                        arg: Message, rank_type: str):
    """rank_type: users/words/victims"""
    group_id = str(event.group_id)
    period_type = arg.extract_plain_text().strip() or "total"
    period_map = recorder.get_period_keys()

    if period_type not in period_map:
        await matcher.finish("请使用正确的时段类型：total（默认）、year、month、day")

    period_key = period_map[period_type]
    target_data = recorder.data.get(group_id, {}).get(period_key, {})

    if not target_data:
        await matcher.finish("该时段暂无复读数据哦～")

    items = target_data.get(rank_type, {})

    if not items:
        await matcher.finish("该时段暂无相关数据")

    sorted_items = sorted(items.items(), key=lambda x: -x[1])[:10]

    descriptions = {
        "users": "复读机",
        "words": "复读词",
        "victims": "被复读"
    }
    await matcher.finish(
        f"{period_key} 时段的{descriptions[rank_type]}排行榜：\n" +
        "\n".join(f"{i + 1}. {item[0]} - {item[1]}次" for i, item in enumerate(sorted_items))
    )


@rep_rank.handle()
async def handle_rep_rank(event: GroupMessageEvent, arg: Message = CommandArg()):
    await get_rank_data(rep_rank, event, arg, "users")


@word_rank.handle()
async def handle_word_rank(event: GroupMessageEvent, arg: Message = CommandArg()):
    await get_rank_data(word_rank, event, arg, "words")
