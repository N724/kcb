import aiohttp
import logging
from typing import Optional, Dict, List
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("smartcampus", "作者名", "智能校园课程与天气查询插件", "1.0.0")
class SmartCampusPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.base_url = "http://kcb.wzhy99.top/"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def _fetch_data(self, params: Dict[str, str]) -> Optional[str]:
        """执行API请求"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Compatible; Bot/2.0)",
                "Accept": "text/plain; charset=utf-8"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.base_url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"API异常状态码: {resp.status}")
                        return None
                    return await resp.text(encoding='utf-8')
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}", exc_info=True)
            return None

    def _format_response(self, raw_data: str) -> str:
        """格式化原始响应数据"""
        # 移除时间戳
        cleaned_data = raw_data.split('\n', 1)[-1]
        
        # 分割课程和天气信息
        sections = cleaned_data.split('\n' + '━'*60 + '\n')
        if len(sections) < 2:
            return "⚠️ 数据格式异常，请联系管理员"
        
        # 课程信息处理
        course_info = sections[0].replace('━━', '┈┈').replace('├', '│').replace('└', '╰')
        
        # 天气信息处理
        weather_info = sections[1].replace(' | ', ' ｜ ').replace('━━', '┈┈')
        
        return f"""
📚 课程信息
{course_info}

🌤️ 实时天气
{weather_info}
        """.strip()

    @filter.command("课程查询")
    async def handle_query(self, event: AstrMessageEvent):
        '''查询课程信息，格式：/课程查询 [模式] [周次] [星期]
        
        参数说明：
        - 模式：today/week/all（默认today）
        - 周次：1-18的数字（默认当前周）
        - 星期：1-7的数字（当模式为today时无效）
        '''
        try:
            args = event.message_str.split()[1:]  # 去除命令头
            
            # 参数解析
            params = {}
            if len(args) > 0 and args[0] in ('today', 'week', 'all'):
                params['mode'] = args[0]
                args = args[1:]
            
            if len(args) > 0 and args[0].isdigit():
                week = max(1, min(18, int(args[0])))
                params['week'] = str(week)
                args = args[1:]
            
            if len(args) > 0 and args[0].isdigit():
                day = max(1, min(7, int(args[0])))
                params['day'] = str(day)
            
            # 发送查询提示
            yield CommandResult().message("🔍 正在查询校园数据...")

            # 获取数据
            raw_data = await self._fetch_data(params)
            if not raw_data:
                yield CommandResult().error("⚠️ 数据服务暂时不可用")
                return

            # 处理错误提示
            if raw_data.startswith('⚠️'):
                yield CommandResult().error(raw_data)
                return

            # 格式化结果
            formatted = self._format_response(raw_data)
            yield CommandResult().message(formatted)

        except Exception as e:
            logger.error(f"指令处理异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 服务暂时不可用，请稍后再试")
