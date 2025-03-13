import aiohttp
import re
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
        self.api_url = "http://kcb.wzhy99.top/"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def _fetch_data(self, params: Dict[str, str]) -> Optional[str]:
        """执行API请求"""
        try:
            headers = {
                "User-Agent": "AstrBot/1.0",
                "Accept": "text/plain; charset=utf-8"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url, params=params, headers=headers) as resp:
                    logger.debug(f"API响应状态: {resp.status}")
                    
                    # 处理特殊状态码
                    if resp.status in (400, 503):
                        return await resp.text(encoding='utf-8')
                    
                    if resp.status != 200:
                        logger.error(f"HTTP异常状态码: {resp.status}")
                        return None
                        
                    return await resp.text(encoding='utf-8')

        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}", exc_info=True)
            return None

    def _format_response(self, raw_data: str) -> str:
        """格式化API响应数据"""
        # 移除时间戳
        cleaned_data = re.sub(r'^$$\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$$\n', '', raw_data, count=1)
        
        # 分割模块
        separator = r'\n━{20,}\n'  # 匹配20个以上短横线
        sections = re.split(separator, cleaned_data)
        
        if len(sections) < 3:
            logger.error(f"无效数据格式: {raw_data}")
            return "⚠️ 数据解析失败，请联系管理员"

        # 处理课程信息
        course_section = sections[1].strip()
        course_lines = []
        for line in course_section.split('\n'):
            if line.startswith('🔸'):
                course_lines.append(f"\n📅 {line[2:].strip()}")
            elif line.startswith(('├─', '└─')):
                course_lines.append(line.replace('─', '─', 1))
            else:
                course_lines.append(f"│ {line}")

        # 处理天气信息
        weather_section = sections[2].strip()
        weather_lines = ["🌤️ 实时天气"]
        for line in weather_section.split('\n'):
            if line.startswith('⚠️'):
                weather_lines.append(f"\n⚠️ **预警**：{line[3:]}")
            elif '：' in line:
                key, value = line.split('：', 1)
                weather_lines.append(f"▫️ {key}：{value}")
            else:
                weather_lines.append(line)

        return (
            "📚 课程信息\n" + '\n'.join(course_lines) + 
            "\n\n" + '\n'.join(weather_lines) +
            "\n\n🔔 数据更新：课程每日校准 | 天气10分钟更新"
        )

    @filter.command("课程查询")
    async def handle_query(self, context: Context, event: AstrMessageEvent, args: List[str]):
        '''查询课程及天气信息
        
        参数格式：
        /课程查询 [模式] [周次] [星期]
        
        参数说明：
        • 模式：today（当天）/week（本周）/all（全周）
        • 周次：1-18的数字（默认当前周）
        • 星期：1-7的数字（仅当模式为today时无效）
        '''
        try:
            # 参数解析
            params = {}
            current_args = args.copy()
            
            # 解析模式参数
            if current_args and current_args[0].lower() in ('today', 'week', 'all'):
                params['mode'] = current_args.pop(0).lower()
            
            # 解析周次参数
            if current_args and current_args[0].isdigit():
                week = int(current_args[0])
                params['week'] = str(max(1, min(18, week)))
                current_args.pop(0)
            
            # 解析星期参数
            if current_args and current_args[0].isdigit():
                day = int(current_args[0])
                params['day'] = str(max(1, min(7, day)))
                current_args.pop(0)
            
            # 无效参数检测
            if current_args:
                yield CommandResult().error(f"⚠️ 无法识别的参数: {' '.join(current_args)}")
                return

            # 发送查询提示
            yield CommandResult().message("⏳ 正在获取最新校园数据...")

            # 请求API
            raw_data = await self._fetch_data(params)
            if not raw_data:
                yield CommandResult().error("⚠️ 服务暂时不可用，请稍后重试")
                return
                
            # 处理API错误响应
            if raw_data.startswith('⚠️'):
                yield CommandResult().error(raw_data.strip())
                return

            # 格式化数据
            try:
                formatted = self._format_response(raw_data)
            except Exception as e:
                logger.error(f"格式化失败: {str(e)}\n原始数据:\n{raw_data}")
                yield CommandResult().error("⚠️ 数据解析异常，请联系管理员")
                return

            yield CommandResult().message(formatted)

        except Exception as e:
            logger.error(f"处理异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 系统繁忙，请稍后再试")
