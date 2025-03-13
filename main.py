import aiohttp
import logging
import re
from typing import Optional, Dict, List
from aiohttp import ClientTimeout
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("course", "作者", "智能课程表插件", "1.0.0")
class CoursePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "http://kcb.wzhy99.top/api.php"
        self.timeout = ClientTimeout(total=15)

    async def fetch_data(self, params: Dict) -> Optional[str]:
        """执行API请求"""
        try:
            logger.debug(f"请求参数：{params}")
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"API响应异常：{resp.status}")
                        return None
                    return await resp.text()
        except Exception as e:
            logger.error(f"请求失败：{str(e)}")
            return None

    def _parse_data(self, raw_text: str) -> Dict:
        """解析原始数据"""
        result = {
            "time": "",
            "week": "",
            "courses": [],
            "weather": {},
            "curfew": ""
        }
        
        # 提取基础信息
        time_match = re.search(r"🕒 查询时间：(.+)", raw_text)
        if time_match:
            result["time"] = time_match.group(1)
        
        week_match = re.search(r"📅 第(\d+)教学周", raw_text)
        if week_match:
            result["week"] = f"第{week_match.group(1)}教学周"

        # 解析课程信息
        course_blocks = re.findall(r"🔸 (.+?)\n(.+?)(?=🔸|🕒)", raw_text, re.DOTALL)
        for block in course_blocks:
            course = {
                "name": re.search(r"【(.+?)】", block[0]).group(1),
                "teacher": re.search(r"👨🏫 (.+?) 🏫", block[1]).group(1),
                "location": re.search(r"🏫 (.+?)\n", block[1]).group(1),
                "time": re.search(r"⏰ (.+?) 📆", block[1]).group(1),
                "weeks": re.search(r"📆 (.+)", block[1]).group(1)
            }
            result["courses"].append(course)

        # 解析天气信息
        weather_match = re.search(r"🌡️ 温度：(.+?) \|", raw_text)
        if weather_match:
            result["weather"]["temp"] = weather_match.group(1)
        
        # 解析门禁时间
        curfew_match = re.search(r"🚪 (.+?) 🔍", raw_text)
        if curfew_match:
            result["curfew"] = curfew_match.group(1)

        return result

    def _format_message(self, data: Dict) -> List[str]:
        """生成消息内容"""
        msg = [
            "📅 智能课程表",
            "━"*20,
            f"🕒 {data['time']}",
            f"📆 {data['week']}"
        ]
        
        if data["courses"]:
            msg.append("\n📚 今日课程：")
            for course in data["courses"]:
                msg.extend([
                    f"▫️ 【{course['name']}】",
                    f"👨🏫 {course['teacher']} 🏫 {course['location']}",
                    f"⏰ {course['time']}",
                    "━"*15
                ])
        else:
            msg.append("\n🎉 今日没有课程安排！")

        if data["curfew"]:
            msg.append(f"\n🚪 门禁时间：{data['curfew']}")

        return msg

    @filter.command("课表")
    async def course_query(self, event: AstrMessageEvent):
        '''查询课程表 格式：/课表 [星期]'''
        try:
            # 参数处理
            args = event.message_str.split()
            params = {}
            
            if len(args) > 1:
                if args[1].isdigit():
                    params["day"] = args[1]
                elif args[1].startswith("week"):
                    params["week"] = args[1][4:]
            
            # 获取数据
            raw_data = await self.fetch_data(params)
            if not raw_data:
                yield CommandResult().error("⚠️ 数据获取失败")
                return
                
            # 解析数据
            parsed_data = self._parse_data(raw_data)
            if not parsed_data["courses"]:
                yield CommandResult().message("🎉 今日没有课程安排！")
                return
                
            yield CommandResult().message("\n".join(self._format_message(parsed_data)))

        except Exception as e:
            logger.error(f"处理异常：{str(e)}")
            yield CommandResult().error("💥 服务暂时不可用")

    @filter.command("课表帮助")
    async def course_help(self, event: AstrMessageEvent):
        """帮助信息"""
        help_msg = [
            "📘 使用说明：",
            "/课表 - 查询当天课程",
            "/课表 [数字] - 查询指定星期（1-7）",
            "/课表 weekN - 查询第N周课程",
            "━"*20,
            "示例：",
            "🔸 /课表3 → 周三课程",
            "🔸 /课表week5 → 第5周课程"
        ]
        yield CommandResult().message("\n".join(help_msg))
