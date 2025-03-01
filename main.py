import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

@register("class_schedule", "作者名", "智能课表系统", "2.1.0")
class ClassSchedulePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.schedule = self._init_schedule()
        self.semester_start = datetime(2024, 9, 1)  # 学期开始日期
        
    def _init_schedule(self) -> Dict[str, List[Dict]]:
        """初始化课程数据结构"""
        return {
            "星期一": [
                {"节次": (1,2), "课程": "毛泽东思想和中国特色社会主义理论体系概论", "类型": "理论", 
                 "教师": "梁果", "周次": "1-18", "地点": "3-4-8"},
                {"节次": (5,6), "课程": "体育与健康2", "类型": "理论",
                 "教师": "阳同维", "周次": "1-18", "地点": "3-4-8"}
            ],
            "星期二": [
                {"节次": (1,4), "课程": "信息技术", "类型": "理论",
                 "教师": "李姝", "周次": "1-18", "地点": "A7-4502"},
                {"节次": (5,6), "课程": "大学英语", "类型": "理论",
                 "教师": "王军", "周次": "1-18", "地点": "3-4-8"},
                {"节次": (7,8), "课程": "人工智能", "类型": "理论",
                 "教师": "龙再英", "周次": "1-18", "地点": "3-4-8"}
            ],
            # 完整数据结构请参考附件
        }

    def _calculate_week(self) -> Tuple[int, bool]:
        """计算当前教学周和单双周状态"""
        delta = datetime.now() - self.semester_start
        current_week = delta.days // 7 + 1
        is_even_week = current_week % 2 == 0
        return current_week, is_even_week

    def _parse_week_range(self, week_str: str) -> List[int]:
        """智能解析周次范围"""
        week_str = week_str.replace("双周", "").replace("单周", "")
        if '-' in week_str:
            start, end = map(int, re.findall(r'\d+', week_str))
            return list(range(start, end+1))
        return [int(w) for w in re.findall(r'\d+', week_str)]

    @filter.command("课表")
    async def query_schedule(self, event: AstrMessageEvent):
        """智能课表查询系统"""
        try:
            args = event.message_str.split()
            if len(args) < 2:
                yield CommandResult().error("❌ 请提供查询参数，例如：/课表 周一 或 /课表 本周")
                return

            query = ' '.join(args[1:]).lower()
            current_week, is_even = self._calculate_week()
            response = []

            # 多维度查询逻辑
            if query in ["周一", "星期一"]:
                response = self._format_daily_schedule("星期一")
            elif query == "本周":
                response = self._get_weekly_schedule(current_week)
            elif "教师" in query:
                teacher = query.replace("教师", "").strip()
                response = self._search_by_teacher(teacher)
            else:
                response = self._intelligent_search(query, current_week, is_even)

            yield CommandResult().message("\n\n".join(response[:5])) if response else CommandResult().message("🔍 未找到相关课程")

        except Exception as e:
            yield CommandResult().error("💥 查询失败，请检查输入格式")

    def _format_daily_schedule(self, day: str) -> List[str]:
        """生成每日课程简报"""
        return [
            f"📅 {day} 课程安排\n" + "\n".join([
                f"⏰ 第{start}-{end}节｜{c['课程']}（{c['类型']}）\n"
                f"👨🏫 {c['教师']}｜📍 {c['地点']}｜🗓 第{c['周次']}周"
                for c in self.schedule[day]
            ])
        ]

    def _get_weekly_schedule(self, current_week: int) -> List[str]:
        """生成本周课程提醒"""
        schedule = []
        for day, courses in self.schedule.items():
            day_courses = []
            for c in courses:
                if current_week in self._parse_week_range(c["周次"]):
                    time_range = f"{c['节次']}-{c['节次']}节"
                    day_courses.append(f"• {c['课程']} ({time_range}, {c['地点']})")
            if day_courses:
                schedule.append(f"📌 {day}\n" + "\n".join(day_courses))
        return schedule

    # 完整功能代码请见附件...
