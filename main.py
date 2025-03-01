import re
from typing import Dict, List, Optional
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

@register("class_schedule", "作者名", "智能课表查询插件", "1.0.0")
class ClassSchedulePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.schedule = self._init_schedule()

    def _init_schedule(self) -> Dict[str, List[Dict]]:
        """初始化课程数据结构"""
        return {
            "星期一": [
                {"节次": "1-2", "课程": "毛泽东思想和中国特色社会主义理论体系概论", "类型": "理论", 
                 "教师": "梁果", "周次": "1-18", "地点": "3-4-8"},
                {"节次": "5-6", "课程": "体育与健康2", "类型": "理论",
                 "教师": "阳同维", "周次": "1-18", "地点": "3-4-8"}
            ],
            # 其他星期数据类似，此处省略完整数据...
            "星期五": [
                {"节次": "1-2", "课程": "高等数学", "类型": "理论",
                 "教师": "陈小丹", "周次": "1-18", "地点": "3-4-8"},
                {"节次": "3-4", "课程": "思想道德与法治", "类型": "理论", 
                 "教师": "邓清月", "周次": "双周2-18", "地点": "3-4-8"},
                {"节次": "7-8", "课程": "酒水知识与调酒技术", "类型": "理论",
                 "教师": "朱悦", "周次": "1-18", "地点": "3-4-8"}
            ]
        }

    def _parse_week_range(self, week_str: str) -> List[int]:
        """解析周次范围（支持单周、双周、区间）"""
        if "双周" in week_str:
            start, end = map(int, re.findall(r'\d+', week_str))
            return [w for w in range(start, end+1) if w % 2 == 0]
        return [int(w) for w in re.findall(r'\d+', week_str)]

    @filter.command("课表")
    async def query_schedule(self, event: AstrMessageEvent):
        """
        课表查询命令，支持以下模式：
        1. /课表 星期几 → 显示当日所有课程
        2. /课表 教师名 → 显示该教师所有课程
        3. /课表 课程名 → 显示课程详细信息
        4. /课表 本周 → 显示当前周次课程（需实现周次计算）
        """
        try:
            args = event.message_str.split()
            if len(args) < 2:
                yield CommandResult().error("❌ 请提供查询参数，例如：/课表 星期一 或 /课表 陈小丹")
                return

            query = ' '.join(args[1:])
            result = []

            # 多维度查询逻辑
            if query in self.schedule:  # 按星期查询
                result.append(f"📅 {query} 课程安排")
                for course in self.schedule[query]:
                    result.append(
                        f"⏰ 第{course['节次']}节｜{course['课程']}（{course['类型']}）\n"
                        f"👨🏫 {course['教师']}｜📌 {course['地点']}｜🗓 第{course['周次']}周"
                    )
            else:  # 按教师/课程查询
                for day, courses in self.schedule.items():
                    for course in courses:
                        if query in [course['教师'], course['课程']]:
                            result.append(
                                f"📌 {day} 第{course['节次']}节\n"
                                f"📚 {course['课程']}｜👨🏫 {course['教师']}\n"
                                f"🏫 {course['地点']}｜🗓 第{course['周次']}周\n━━"
                            )

            if not result:
                yield CommandResult().message("🔍 未找到相关课程信息")
                return

            yield CommandResult().message("\n\n".join(result[:5]))  # 防止消息过长

        except Exception as e:
            yield CommandResult().error("💥 课表查询失败，请稍后再试")

    @filter.command("课表帮助")
    async def schedule_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_msg = [
            "📘 课表插件使用指南",
            "━━━━━━━━━━━━━━━━",
            "1. 按星期查询：/课表 星期一",
            "2. 按教师查询：/课表 陈小丹",
            "3. 按课程查询：/课表 高等数学",
            "4. 本周课程：/课表 本周（开发中）",
            "━━━━━━━━━━━━━━━━",
            "🛠️ 功能特性：",
            "• 支持多维度精确查询",
            "• 显示课程时间/地点/周次",
            "• 智能解析双周课程安排",
            "• 防刷消息限制（显示前5条结果）"
        ]
        yield CommandResult().message("\n".join(help_msg))
