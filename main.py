import logging
from datetime import datetime
from typing import Dict, List
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

# 完整课程数据结构
SCHEDULE_DATA = {
    1: [  # 周一
        {"name": "毛泽东思想和中国特色社会主义理论体系概论", "type": "理论", "teacher": "梁果", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [1,2], 
         "time": "早上一二节 (8:40-10:10)", "emoji": "📖"},
        {"name": "体育与健康2", "type": "理论", "teacher": "阳同维", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [5,6], 
         "time": "下午一二节 (13:30-15:00)", "emoji": "🏃"}
    ],
    2: [  # 周二
        {"name": "信息技术", "type": "理论", "teacher": "李姝", 
         "weeks": "1-18周", "classroom": "A7-4502", "sections": [1,2,3,4], 
         "time": "早上一二三四节 (8:40-12:00)", "emoji": "💻"},
        {"name": "大学英语", "type": "理论", "teacher": "王军", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [5,6], 
         "time": "下午一二节 (13:30-15:00)", "emoji": "🇬🇧"},
        {"name": "人工智能", "type": "理论", "teacher": "龙再英", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [7,8], 
         "time": "下午三四节 (15:10-16:40)", "emoji": "🤖"}
    ],
    3: [  # 周三
        {"name": "高等数学", "type": "理论", "teacher": "陈小丹", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [1,2], 
         "time": "早上一二节 (8:40-10:10)", "emoji": "🧮"},
        {"name": "餐饮服务与数字化运营", "type": "理论", "teacher": "翟玮", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [3,4], 
         "time": "早上三四节 (10:30-12:00)", "emoji": "🍽️"},
        {"name": "餐饮服务与数字化运营", "type": "理论", "teacher": "翟玮", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [5,6], 
         "time": "下午五六节 (13:30-15:00)", "emoji": "🍷"},
        {"name": "形势与政策2", "type": "理论", "teacher": "付世琪", 
         "weeks": "13-16周", "classroom": "3-4-8", "sections": [7,8], 
         "time": "下午七八节 (15:10-16:40)", "emoji": "📜"}
    ],
    4: [  # 周四
        {"name": "大学英语", "type": "理论", "teacher": "王军", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [1,2], 
         "time": "早上一二节 (8:40-10:10)", "emoji": "🇬🇧"},
        {"name": "思想道德与法治", "type": "理论", "teacher": "邓清月", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [3,4], 
         "time": "早上三四节 (10:30-12:00)", "emoji": "⚖️"},
        {"name": "酒水知识与调酒技术", "type": "理论", "teacher": "朱悦", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [7,8], 
         "time": "下午七八节 (15:10-16:40)", "emoji": "🍸"}
    ],
    5: [  # 周五
        {"name": "高等数学", "type": "理论", "teacher": "陈小丹", 
         "weeks": "1-18周", "classroom": "3-4-8", "sections": [1,2], 
         "time": "早上一二节 (8:40-10:10)", "emoji": "🧮"},
        {"name": "思想道德与法治", "type": "理论", "teacher": "邓清月", 
         "weeks": "2-18（双）周", "classroom": "3-4-8", "sections": [3,4], 
         "time": "早上三四节 (10:30-12:00)", "emoji": "⚖️", 
         "note": "✨ 双周才上课哦！"}
    ]
}

# 作息时间表（带颜文字）
TIME_SCHEDULE = '''
🌸 元气满满の作息表 🌸
🍳 上午课程 | 1-4节
┌───────────────┬───────────────┐
│ 08:40 - 09:20 │ 09:30 - 10:10 │
├───────────────┼───────────────┤
│ 10:30 - 11:10 │ 11:20 - 12:00 │
└───────────────┴───────────────┘

🌞 下午课程 | 5-8节
┌───────────────┬───────────────┐
│ 13:30 - 14:10 │ 14:20 - 15:00 │
├───────────────┼───────────────┤
│ 15:10 - 15:50 │ 16:00 - 16:40 │
└───────────────┴───────────────┘

🌙 晚间课程 | 9-10节
┌───────────────┬───────────────┐
│ 19:00 - 19:40 │ 19:50 - 20:30 │
└───────────────┴───────────────┘

🚨 门禁小贴士
▸ 校门禁出：🕖 19:00 
▸ 宿舍查寝：🕙 22:00 
▸ 温馨提示：晚归会被辅导员约谈哦 (＞﹏＜)
'''

@register("schedule", "作者名", "智能课程表插件", "2.0.0")
class SchedulePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.week_days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def _get_day(self, text: str) -> int:
        """智能解析日期"""
        text = text.replace("星期", "").replace("周", "").strip()
        day_map = {"一":1, "二":2, "三":3, "四":4, "五":5, 
                  "今天": datetime.today().isoweekday(),
                  "明天": (datetime.today().isoweekday() % 7) +1}
        return day_map.get(text, datetime.today().isoweekday())

    def _format_note(self, course: Dict) -> str:
        """生成课程备注"""
        if "note" in course:
            return f"\n📌 注意：{course['note']}"
        if "（双）" in course["weeks"]:
            return "\n🚩 特别提醒：本课程双周才上哦！"
        return ""

    def _format_course(self, courses: List[Dict]) -> str:
        """生成带样式的课程信息"""
        return "\n\n".join([
            f"{course['emoji']} 【{course['name']}】\n"
            f"├👨🏫 教师：{course['teacher']}\n"
            f"├🏫 教室：{course['classroom']}\n"
            f"├⏰ 时间：{course['time']}\n"
            f"└📆 周次：{course['weeks']}"
            f"{self._format_note(course)}"
            for course in courses
        ])

    async def _get_day_schedule(self, day: int) -> str:
        """获取某天课表"""
        if day not in SCHEDULE_DATA or not SCHEDULE_DATA[day]:
            return f"{self.week_days[day-1]} 没有课程安排 🎉\n可以好好休息啦～"
            
        return (
            f"📅 {self.week_days[day-1]} 课程表\n"
            "┌──────────────────────────────┐\n"
            f"{self._format_course(SCHEDULE_DATA[day])}\n"
            "└──────────────────────────────┘\n"
            f"⏰ 今日门禁：{'19:00' if day < 5 else '无限制'} | 查寝时间：22:00"
        )

    @filter.command("课表")
    async def query_schedule(self, event: AstrMessageEvent):
        '''查询课表：/课表 [今天/明天/周一] (默认今天)'''
        try:
            args = event.message_str.split()
            day = self._get_day(args if len(args)>1 else "")
            
            if day > 5:
                yield CommandResult().message("🎉 周末没有课程！快去享受生活吧～")
                return

            response = await self._get_day_schedule(day)
            yield CommandResult().message(response)

        except Exception as e:
            logger.error(f"课表查询异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 课程表服务暂时不可用")

    @filter.command("本周课表")
    async def weekly_schedule(self, event: AstrMessageEvent):
        '''查看本周完整课表'''
        try:
            msg = ["📚 本周课程总览 🌈", "━"*30]
            for day in range(1,6):
                day_msg = await self._get_day_schedule(day)
                msg.append(day_msg + "\n" + "━"*30)
            
            msg.append("💡 温馨提示：双击课程可查看详细信息")
            yield CommandResult().message("\n".join(msg))

        except Exception as e:
            logger.error(f"周课表生成异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 周课表生成失败")

    @filter.command("作息")
    async def show_schedule(self, event: AstrMessageEvent):
        """查看详细作息时间"""
        yield CommandResult().message(TIME_SCHEDULE)
