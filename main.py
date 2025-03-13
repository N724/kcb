import re
import logging
from typing import Optional, Dict, List
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("smartcampus", "作者名", "智能校园课程与天气查询插件", "1.2.0")
class SmartCampusPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.base_url = "http://kcb.wzhy99.top/"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def _fetch_data(self, params: Dict[str, str]) -> Optional[str]:
        """执行API请求（保持原有实现）"""
        # ... 同前文代码 ...

    def _format_response(self, raw_data: str) -> str:
        """严格遵循API文档的格式化方法"""
        # 移除时间戳（精确匹配[YYYY-MM-DD HH:MM:SS]格式）
        cleaned_data = re.sub(r'^$$\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$$\n', '', raw_data, count=1)
        
        # 使用正则表达式分割模块
        separator = r'\n━{50,}\n'
        sections = re.split(separator, cleaned_data)
        
        # 验证模块结构
        if len(sections) < 3:
            logger.error(f"异常数据结构:\n{raw_data}")
            return "⚠️ 数据格式异常，请联系管理员"
        
        # 提取课程和天气模块
        course_section = sections[1].strip()
        weather_section = sections[2].strip()

        # 课程表处理（保留原始格式）
        course_lines = []
        for line in course_section.split('\n'):
            if line.startswith('🔸'):
                course_lines.append(f"\n📅 {line[2:]}")
            elif line.startswith(('├', '│', '└')):
                course_lines.append(line)
            else:
                course_lines.append(f"│ {line}")
        
        # 天气信息处理
        weather_lines = []
        for line in weather_section.split('\n'):
            if line.startswith('⚠️'):
                weather_lines.append(f"❗️**预警**：{line[3:]}")
            elif '：' in line:
                parts = line.split('：', 1)
                weather_lines.append(f"▫️ {parts[0]}：{parts[1]}")
            else:
                weather_lines.append(line)

        return (
            "📚 **课程信息**\n" + '\n'.join(course_lines) +
            "\n\n🌤️ **实时天气**\n" + '\n'.join(weather_lines) +
            "\n\n数据更新周期：每10分钟 | 校历自动校准"
        )

    @filter.command("课程查询")
async def handle_query(self, context: Context, event: AstrMessageEvent, args: List[str]):
    '''查询课程信息，格式：/课程查询 [模式] [周次] [星期]'''
    try:
        # 调试日志验证参数
        logger.debug(f"收到请求: 上下文类型={type(context).__name__} 事件类型={type(event).__name__} 参数={args}")
        
        params = {}
        current_args = args.copy()
        
        # 参数解析逻辑
        if current_args:
            # 处理模式参数
            if current_args[0].lower() in ('today', 'week', 'all'):
                params['mode'] = current_args[0].lower()
                current_args.pop(0)
            
            # 处理周次参数
            if current_args and current_args[0].isdigit():
                week = max(1, min(18, int(current_args[0])))
                params['week'] = str(week)
                current_args.pop(0)
            
            # 处理星期参数
            if current_args and current_args[0].isdigit():
                day = max(1, min(7, int(current_args[0])))
                params['day'] = str(day)
                current_args.pop(0)
        
        # 发送查询提示
        yield CommandResult().message("🔍 正在查询校园数据...")

        # 获取API数据
        raw_data = await self._fetch_data(params)
        if not raw_data:
            yield CommandResult().error("⚠️ 数据服务暂时不可用")
            return

        # 处理原始数据
        if raw_data.startswith('⚠️'):
            yield CommandResult().error(raw_data)
            return

        # 格式化响应
        try:
            formatted = self._format_response(raw_data)
        except Exception as format_error:
            logger.error(f"格式化失败: {str(format_error)}\n原始数据:{raw_data}")
            yield CommandResult().error("⚠️ 数据解析异常，请稍后重试")
            return
            
        yield CommandResult().message(formatted)

    except Exception as e:
        logger.error(f"全局异常: {str(e)}", exc_info=True)
        yield CommandResult().error("💥 服务暂时不可用，请稍后再试")
