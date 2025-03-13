import aiohttp
import re
import logging
from typing import Optional, Dict, List
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("smartcampus", "作者名", "智能校园课程查询插件", "1.0.0")
class SmartCampusPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.base_url = "http://kcb.wzhy99.top/"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def _fetch_data(self, params: Dict[str, str]) -> Optional[str]:
        """执行API请求（严格保持模板结构）"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"API错误 HTTP {resp.status}")
                        return None
                    return await resp.text(encoding='utf-8')
        except aiohttp.ClientError as e:
            logger.error(f"网络异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}", exc_info=True)
            return None

    def _format_message(self, raw_data: str) -> str:
        """消息格式化（保持模板风格）"""
        try:
            # 移除时间戳
            cleaned = re.sub(r'^$$\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$$\n', '', raw_data)
            
            # 分割模块
            parts = re.split(r'\n━+?\n', cleaned)
            if len(parts) < 3:
                return "⚠️ 数据格式异常，请稍后重试"
            
            # 课程信息处理
            course_info = []
            for line in parts[1].split('\n'):
                if line.startswith('🔸'):
                    course_info.append(f"📅 {line[2:]}")
                elif line.startswith('├'):
                    course_info.append(f"├ {line[2:]}")
                elif line.startswith('└'):
                    course_info.append(f"└ {line[2:]}")
                else:
                    course_info.append(f"│ {line}")

            # 天气信息处理
            weather_info = []
            for line in parts[2].split('\n'):
                if '：' in line:
                    key, val = line.split('：', 1)
                    weather_info.append(f"▫️ {key}：{val}")
                elif line.startswith('⚠️'):
                    weather_info.append(f"❗️ {line[3:]}")
                else:
                    weather_info.append(line)

            return (
                "📚 课程信息\n" + '\n'.join(course_info) +
                "\n\n🌤️ 实时天气\n" + '\n'.join(weather_info) +
                "\n\n🔔 数据更新：教学周每日校准 | 天气每10分钟刷新"
            )
        except Exception as e:
            logger.error(f"格式化失败: {str(e)}")
            return "⚠️ 数据处理异常，请联系管理员"

    @filter.command("课程查询")
    async def netcourse_query(self, event: AstrMessageEvent):
        '''查询课程信息（严格遵循模板参数结构）'''
        try:
            # 参数解析
            args = event.message_str.split()[1:]
            params = {}
            
            # 处理模式参数
            if args and args[0] in ('today', 'week', 'all'):
                params['mode'] = args.pop(0)
            
            # 处理周次参数
            if args and args[0].isdigit():
                params['week'] = str(max(1, min(18, int(args.pop(0)))))
            
            # 处理星期参数
            if args and args[0].isdigit():
                params['day'] = str(max(1, min(7, int(args.pop(0)))))
            
            # 无效参数检查
            if args:
                yield CommandResult().error(f"⚠️ 无效参数: {' '.join(args)}")
                return

            # 发送查询提示
            yield CommandResult().message("⏳ 正在查询中，请稍候...")

            # 获取数据
            raw_data = await self._fetch_data(params)
            if not raw_data:
                yield CommandResult().error("⚠️ 服务暂时不可用")
                return

            # 处理错误信息
            if raw_data.startswith('⚠️'):
                yield CommandResult().error(raw_data)
                return

            # 格式化结果
            result = self._format_message(raw_data)
            yield CommandResult().message(result)

        except Exception as e:
            logger.error(f"处理异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 系统繁忙，请稍后再试")
