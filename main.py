import aiohttp
import logging
from typing import Optional, Dict, List
from aiohttp import ClientTimeout
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("course", "作者", "智能课程表查询", "1.0.0")
class CoursePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "http://kcb.wzhy99.top"
        self.timeout = ClientTimeout(total=10)

    async def fetch_course(self, day: Optional[str] = None) -> Optional[str]:
        """获取课程数据"""
        try:
            params = {"day": day} if day else None
            logger.debug(f"请求参数：{params}")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"API请求失败 HTTP {resp.status}")
                        return None
                    return await resp.text()
        except aiohttp.ClientError as e:
            logger.error(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知异常: {str(e)}", exc_info=True)
            return None

    def _parse_course_data(self, text: str) -> Dict:
        """解析课程数据"""
        result = {
            "courses": [],
            "curfew": "",
            "current_week": ""
        }
        
        # 解析周次信息
        if "教学周" in text:
            result["current_week"] = text.split("📅")[1].split("\n")[0].strip()
        
        # 解析课程信息
        course_blocks = [b for b in text.split("┌") if "【" in b]
        for block in course_blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if len(lines) < 3:
                continue
                
            course = {
                "name": lines[0].split("【")[1].split("】")[0],
                "teacher": lines[1].split("🧑🏫")[1].split("🏫")[0].strip(),
                "location": lines[1].split("🏫")[1].split("⏰")[0].strip(),
                "time": lines[2].split("⏰")[1].split("└")[0].strip()
            }
            result["courses"].append(course)
        
        # 解析门禁信息
        if "门禁：" in text:
            result["curfew"] = text.split("⏰ 门禁：")[1].split("\n")[0].strip()
        
        return result

    def _format_message(self, data: Dict) -> List[str]:
        """生成格式化消息"""
        msg = [
            "📅 智能课程表查询",
            "━" * 20,
            f"📌 {data.get('current_week', '')}"
        ]
        
        if data["courses"]:
            msg.append("\n📚 今日课程：")
            for course in data["courses"]:
                msg.extend([
                    f"🔹 【{course['name']}】",
                    f"👨🏫 教师：{course['teacher']}",
                    f"🏫 地点：{course['location']}",
                    f"⏰ 时间：{course['time']}",
                    "━" * 15
                ])
        else:
            msg.append("\n🎉 今日没有课程安排！")
        
        if data["curfew"]:
            msg.append(f"\n⚠️ 门禁通知：{data['curfew']}")
        
        return msg

    @filter.command("课表")
    async def course_query(self, event: AstrMessageEvent):
        '''查询课程表，格式：/课表 [星期数]（1-7）'''
        try:
            args = event.message_str.split()
            day = None
            
            # 参数处理
            if len(args) > 1:
                if not args[1].isdigit() or not 1 <= int(args[1]) <= 7:
                    yield CommandResult().error("❌ 参数必须为1-7的数字\n示例：/课表3 查周三课表")
                    return
                day = args[1]
            
            yield CommandResult().message("⏳ 正在查询课程表...")
            
            # 获取数据
            raw_data = await self.fetch_course(day)
            if not raw_data:
                yield CommandResult().error("⚠️ 课程数据获取失败")
                return
                
            # 解析数据
            parsed_data = self._parse_course_data(raw_data)
            if not parsed_data:
                yield CommandResult().error("💢 数据解析失败")
                return
                
            yield CommandResult().message("\n".join(self._format_message(parsed_data)))

        except Exception as e:
            logger.error(f"处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 课程查询服务暂时不可用")

    @filter.command("课表帮助")
    async def course_help(self, event: AstrMessageEvent):
        """获取帮助信息"""
        help_msg = [
            "📘 使用说明：",
            "/课表 - 查询当天课程表",
            "/课表 <星期数> - 查询指定星期（1=周一，7=周日）",
            "/课表帮助 - 显示本帮助",
            "━" * 20,
            "功能特性：",
            "🔸 实时课程查询",
            "🔸 教室与教师信息",
            "🔸 门禁时间提醒",
            "🔸 智能周次识别"
        ]
        yield CommandResult().message("\n".join(help_msg))
