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
        
    async def fetch_schedule(self, params: Dict[str, str]) -> Optional[str]:
        """获取课程数据"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Compatible; Bot/2.0)",
                "Accept-Charset": "UTF-8"
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url, params=params, headers=headers) as resp:
                    if resp.status in (200, 503):
                        return await resp.text(encoding='UTF-8')
                    elif resp.status == 400:
                        return f"⚠️ {await resp.text()}"
                    logger.error(f"API异常状态码: {resp.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}", exc_info=True)
            return None

    def _parse_response(self, text: str) -> str:
        """解析API响应并格式化"""
        # 移除时间戳
        cleaned_text = re.sub(r'$$\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$$\n', '', text)
        
        # 分割课程和天气模块
        parts = cleaned_text.split('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
        if len(parts) < 3:
            return "⚠️ 数据解析异常，请稍后再试"
            
        course_section = parts[1].strip()
        weather_section = parts[2].strip()
        
        # 优化课程显示
        course_lines = []
        for line in course_section.split('\n'):
            if line.startswith('🔸'):
                course_lines.append(f"\n📌 {line[2:]}")
            elif line.startswith('├'):
                course_lines.append(f"├─📖 {line[2:]}")
            elif line.startswith('│'):
                course_lines.append(f"│  {line[1:]}")
            elif line.startswith('└'):
                course_lines.append(f"└─⏰ {line[2:]}")
            else:
                course_lines.append(line)
        
        # 优化天气显示
        weather_lines = []
        for line in weather_section.split('\n'):
            if line.startswith('📍'):
                weather_lines.append(f"🌍 {line[2:]}")
            elif line.startswith('⚠️'):
                weather_lines.append(f"⚠️ **预警**：{line[3:]}")
            else:
                weather_lines.append(line.replace(' | ', ' | '))
        
        return (
            "📚 **课程信息**\n" + '\n'.join(course_lines) +
            "\n\n🌤️ **天气信息**\n" + '\n'.join(weather_lines) +
            "\n\n🔍 数据更新周期：每10分钟 | 教学周自动校准"
        )

    @filter.command("课程查询")
    async def query_schedule(self, event: AstrMessageEvent):
        '''查询课程及天气，支持参数：/课程查询 [mode=今天/week/all] [day=1-7] [week=1-18]'''
        try:
            args = event.message_str.split()
            params = {}
            
            # 参数解析
            for arg in args[1:]:
                if '=' in arg:
                    k, v = arg.split('=', 1)
                    params[k.strip()] = v.strip()
            
            # 参数验证
            valid_params = {}
            if 'mode' in params:
                if params['mode'] in ('today', 'week', 'all'):
                    valid_params['mode'] = params['mode']
                else:
                    yield CommandResult().error("⚠️ 模式参数错误，可选值：today/week/all")
                    return
                    
            if 'day' in params:
                try:
                    day = max(1, min(7, int(params['day'])))
                    valid_params['day'] = str(day)
                except ValueError:
                    yield CommandResult().error("⚠️ 星期参数应为1-7的整数")
                    return
                    
            if 'week' in params:
                try:
                    week = max(1, min(18, int(params['week'])))
                    valid_params['week'] = str(week)
                except ValueError:
                    yield CommandResult().error("⚠️ 周次参数应为1-18的整数")
                    return
            
            yield CommandResult().message("🔍 正在查询校园数据...")
            
            # 获取数据
            response = await self.fetch_schedule(valid_params)
            if not response:
                yield CommandResult().error("⚠️ 数据服务暂时不可用")
                return
                
            if response.startswith('⚠️'):
                yield CommandResult().error(response)
                return
                
            # 格式化输出
            formatted = self._parse_response(response)
            yield CommandResult().message(formatted)
            
        except Exception as e:
            logger.error(f"指令处理异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 服务繁忙，请稍后再试")
