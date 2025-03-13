import aiohttp
import logging
import re
from typing import Optional, Dict, List
from aiohttp import ClientTimeout
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("smart_campus", "作者", "智能校园助手", "2.1.0")
class SmartCampusPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "http://kcb.wzhy99.top/api.php"
        self.timeout = ClientTimeout(total=15)
        self.weekday_map = {str(i): f"周{'一二三四五六日'[i-1]}" for i in range(1,8)}

    async def fetch_data(self, params: Dict) -> Optional[str]:
        """获取校园数据"""
        try:
            logger.debug(f"请求参数：{params}")
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"API异常 HTTP {resp.status}")
                        return None
                    return await resp.text()
        except Exception as e:
            logger.error(f"请求失败: {str(e)}")
            return None

    def _parse_campus_data(self, raw_text: str) -> Dict:
        """解析校园数据"""
        result = {
            "time": "",
            "week_info": "",
            "courses": [],
            "weather": {},
            "curfew": ""
        }

        # 提取基础信息
        time_match = re.search(r"🕒 查询时间：(.+?)\n", raw_text)
        if time_match:
            result["time"] = time_match.group(1).strip()

        week_match = re.search(r"📅 第(\d+)教学周（(.+?)）", raw_text)
        if week_match:
            result["week_info"] = f"第{week_match.group(1)}教学周（{week_match.group(2)}）"

        # 分割课程和天气区块
        blocks = re.split(r"━{5,}", raw_text)
        course_block = blocks[1] if len(blocks) > 1 else ""
        weather_block = blocks[2] if len(blocks) > 2 else ""

        # 解析课程信息
        course_sections = re.findall(r"🔸 (.+?)\n([\s\S]+?)(?=🔸|🕒)", raw_text)
        for section in course_sections:
            course_day, content = section
            for course in re.findall(r"├ 🇦-🇿]? 【(.+?)】\n([\s\S]+?)(?=├|└)", content):
                name, details = course
                course_data = {
                    "name": name,
                    "teacher": re.search(r"👨🏫 (.+?) 🏫", details).group(1),
                    "location": re.search(r"🏫 (.+?)\n", details).group(1),
                    "time": re.search(r"⏰ (.+?) 📆", details).group(1),
                    "weeks": re.search(r"📆 (.+)", details).group(1)
                }
                result["courses"].append(course_data)

        # 解析天气信息
        weather_lines = weather_block.split("\n")
        for line in weather_lines:
            if "🌡️" in line:
                result["weather"]["temperature"] = re.search(r"温度：(.+?) \|", line).group(1)
                result["weather"]["feels_like"] = re.search(r"体感：(.+)", line).group(1)
            elif "💧" in line:
                result["weather"]["humidity"] = re.search(r"湿度：(.+?) \|", line).group(1)
                result["weather"]["visibility"] = re.search(r"能见度：(.+)", line).group(1)
            elif "⚠️" in line:
                result["weather"]["alert"] = line.split("：")[1].strip()

        # 解析门禁信息
        if "🚪" in raw_text:
            result["curfew"] = re.search(r"🚪 (.+?) 🔍", raw_text).group(1)

        return result

    def _format_message(self, data: Dict) -> List[str]:
        """生成格式化消息"""
        msg = [
            f"🕒 {data['time']}",
            f"📅 {data['week_info']}",
            "━"*25
        ]

        # 课程信息
        if data["courses"]:
            msg.append("\n📚 今日课程：")
            for course in data["courses"]:
                msg.extend([
                    f"🏷 【{course['name']}】",
                    f"👨🏫 {course['teacher']} 🏫 {course['location']}",
                    f"⏰ {course['time']}",
                    f"📆 {course['weeks']}",
                    "━"*15
                ])
        else:
            msg.append("\n🎉 今日没有课程安排！")

        # 天气信息
        msg.append("\n🌤️ 实时天气：")
        weather_items = [
            f"🌡️ 温度：{data['weather'].get('temperature','N/A')}",
            f"💧 湿度：{data['weather'].get('humidity','N/A')}",
            f"👥 体感：{data['weather'].get('feels_like','N/A')}"
        ]
        if alert := data['weather'].get('alert'):
            weather_items.append(f"⚠️ 预警：{alert}")
        msg.extend(weather_items)

        # 门禁信息
        if data["curfew"]:
            msg.append(f"\n🚪 门禁时间：{data['curfew']}")

        return msg

    @filter.command("校园")
    async def campus_query(self, event: AstrMessageEvent):
        '''校园信息查询 格式：/校园 [参数]'''
        try:
            args = event.message_str.split()
            params = {"mode": "today"}
            
            # 参数解析
            if len(args) > 1:
                if args[1].isdigit() and 1 <= int(args[1]) <= 7:
                    params = {"day": args[1]}
                elif args[1] in ["week", "all"]:
                    params = {"mode": args[1]}
                elif args[1].startswith("week"):
                    if (week_num := args[1][4:]).isdigit():
                        params = {"week": week_num}
            
            # 获取数据
            raw_data = await self.fetch_data(params)
            if not raw_data:
                yield CommandResult().error("⚠️ 数据获取失败")
                return
                
            # 解析数据
            parsed_data = self._parse_campus_data(raw_data)
            yield CommandResult().message("\n".join(self._format_message(parsed_data)))

        except Exception as e:
            logger.error(f"处理异常: {str(e)}")
            yield CommandResult().error("💥 服务暂时不可用")

    @filter.command("校园帮助")
    async def campus_help(self, event: AstrMessageEvent):
        """获取帮助信息"""
        help_msg = [
            "📘 智能校园助手使用指南",
            "━"*20,
            "/校园 - 查询当天信息",
            "/校园 [数字] - 查询指定星期（1-7）",
            "/校园 week - 本周所有课程",
            "/校园 weekN - 指定教学周（例：week3）",
            "━"*20,
            "✨ 功能包含：",
            "🔸 实时课程表查询",
            "🔸 精准天气监控",
            "🔸 教学周计算",
            "🔸 门禁提醒"
        ]
        yield CommandResult().message("\n".join(help_msg))
