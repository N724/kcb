import aiohttp
import logging
import re
from datetime import datetime
from typing import Optional, Dict, List
from aiohttp import ClientTimeout
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("course_schedule", "作者", "智能课程表查询", "2.0.0")
class CoursePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.base_url = "http://kcb.wzhy99.top"
        self.timeout = ClientTimeout(total=10)
        self.weekday_map = {
            0: "日", 1: "一", 2: "二",
            3: "三", 4: "四", 5: "五", 6: "六"
        }

    async def fetch_courses(self, day: Optional[int] = None) -> Optional[str]:
        """获取课程表数据"""
        try:
            url = self.base_url
            params = {"day": day} if day is not None else None
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"API请求失败 HTTP {resp.status}")
                        return None
                    return await resp.text()
        except Exception as e:
            logger.error(f"请求异常: {str(e)}")
            return None

    def _parse_course_data(self, raw_text: str) -> Dict:
        """解析课程表文本数据"""
        result = {
            "week_info": "",
            "courses": [],
            "curfew": "",
            "current_time": ""
        }

        # 提取基础信息
        time_match = re.search(r"当前时间：(.+?)\n", raw_text)
        if time_match:
            result["current_time"] = time_match.group(1).strip()

        week_match = re.search(r"第\s*(\d+)\s*教学周（(.+?)）", raw_text)
        if week_match:
            result["week_info"] = f"第 {week_match.group(1)} 教学周（{week_match.group(2)}）"

        # 解析课程信息
        course_blocks = re.split(r"-{5,}", raw_text)
        if len(course_blocks) > 1:
            for line in course_blocks[1].split("\n"):
                line = line.strip()
                if "【" in line:
                    course = {
                        "name": re.search(r"【(.*?)】", line).group(1),
                        "teacher": "",
                        "location": "",
                        "time": "",
                        "weeks": ""
                    }
                elif "🧑🏫" in line:
                    parts = line.split("🏫")
                    course["teacher"] = parts[0].split(" ")[-1].strip()
                    course["location"] = parts[1].split("⏰")[0].strip()
                elif "⏰" in line:
                    course["time"] = re.search(r"⏰\s*(.+?)\s*\└", line).group(1)
                    course["weeks"] = re.search(r"周次：(.+)", line).group(1)
                    result["courses"].append(course)
                elif "门禁" in line:
                    result["curfew"] = line.replace("⏰", "").strip()

        return result

    def _format_message(self, data: Dict) -> List[str]:
        """生成格式化消息"""
        msg = [
            f"📅 {data['week_info']}" if data["week_info"] else "📅 教学周信息未获取",
            f"🕒 数据时间：{data['current_time'] or '未知时间'}"
        ]

        if data["courses"]:
            msg.append("\n📚 今日课程安排：")
            for course in data["courses"]:
                course_info = [
                    f"🏷 【{course['name']}】",
                    f"👨🏫 教师：{course['teacher']}",
                    f"🏛 地点：{course['location']}",
                    f"⏱ 时间：{course['time']}",
                    f"📆 周次：{course['weeks']}",
                    "━"*20
                ]
                msg.extend(course_info)
        else:
            msg.append("\n🎉 今日没有课程安排！")

        if data["curfew"]:
            msg.append(f"\n⚠️ 门禁通知：{data['curfew']}")

        return msg

    @filter.command("课表")
    async def get_course(self, event: AstrMessageEvent):
        """查询课程表 格式：/课表 [星期数]（如/课表3）"""
        try:
            # 解析参数
            args = event.message_str.split()
            day = None

            if len(args) > 1:
                if not args[1].isdigit():
                    yield CommandResult().error("❌ 参数必须是数字（0-6）\n示例：/课表3 查周三课表")
                    return
                
                day = int(args[1])
                if not 0 <= day <= 6:
                    yield CommandResult().error("❌ 星期数范围错误（0-6）\n0=当天 1=周一 ...6=周日")
                    return

            # 获取数据
            raw_data = await self.fetch_courses(day)
            if not raw_data:
                yield CommandResult().error("⚠️ 课表数据获取失败，请稍后重试")
                return

            # 处理数据
            parsed_data = self._parse_course_data(raw_data)
            formatted_msg = self._format_message(parsed_data)

            # 添加星期提示
            if day is not None:
                weekday = self.weekday_map.get(day, "")
                if weekday:
                    formatted_msg.insert(1, f"📌 星期{weekday}课程表")

            yield CommandResult().message("\n".join(formatted_msg))

        except Exception as e:
            logger.error(f"处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 课表查询服务暂时不可用")

    @filter.command("课表帮助")
    async def course_help(self, event: AstrMessageEvent):
        """获取帮助信息"""
        help_msg = [
            "📘 使用说明：",
            "/课表 - 获取当天课程表",
            "/课表 <星期数> - 获取指定星期课表（0=当天 1=周一...6=周日）",
            "/课表帮助 - 显示本帮助信息",
            "━"*20,
            "示例：",
            "🔸 /课表    → 今天课程",
            "🔸 /课表3  → 周三课程",
            "🔸 /课表0  → 当天课程"
        ]
        yield CommandResult().message("\n".join(help_msg))
