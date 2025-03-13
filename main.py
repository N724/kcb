import aiohttp
import logging
from typing import Optional, Dict, List
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("netcourse", "作者名", "网课任务查询插件", "1.0.0")
class NetCoursePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "http://hanlin.icu/api.php?act=chadan"
        self.quote_url = "https://api.qqsuu.cn/api/dm-mgjuzi"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def fetch_netcourse(self, username: str) -> Optional[Dict[str, str]]:
        """获取网课任务数据"""
        try:
            data = {"username": username}
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Compatible; Bot/2.0)"
            }
            logger.debug(f"请求参数：{data}")

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(self.api_url, data=data, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"API请求失败 HTTP {resp.status}")
                        return None

                    result = await resp.json()
                    logger.debug(f"API原始响应:\n{result}")
                    return result

        except aiohttp.ClientError as e:
            logger.error(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知异常: {str(e)}", exc_info=True)
            return None

    async def fetch_quote(self) -> str:
        """获取励志名言"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.quote_url) as resp:
                    if resp.status != 200:
                        return "🌟 今天也要加油哦，未来的你会感谢现在努力的自己！"

                    result = await resp.json()
                    if result.get("code") == 200:
                        content = result["data"].get("content", "坚持不懈的努力，才有精彩的明天！")
                        author = result["data"].get("author", "佚名")
                        return f"🌟 『{content}』 —— {author}"
                    return "🌟 今天也要加油哦，未来的你会感谢现在努力的自己！"

        except Exception as e:
            logger.error(f"获取名言失败: {str(e)}")
            return "🌟 今天也要加油哦，未来的你会感谢现在努力的自己！"

    def _format_message(self, data: Dict[str, str], quote: str) -> str:
        """生成格式化消息"""
        tasks = data.get("data", [])
        task_count = len(tasks)
        if task_count == 0:
            return "📭 没有找到该用户的任何网课任务记录！"

        task_details = f"🎉 查询到该用户共有 {task_count} 条网课任务记录：\n"
        for i, task in enumerate(tasks, start=1):
            ptname = task.get("ptname", "未知项目")
            name = task.get("name", "未知用户")
            status = task.get("status", "状态未知")
            progress = task.get("process", "0.0%")
            remarks = task.get("remarks", "无备注信息")
            addtime = task.get("addtime", "未知时间")

            task_details += (
                f"\n📘 **任务 {i}**\n"
                f"👤 用户名：{name}\n"
                f"📚 项目名称：{ptname}\n"
                f"📊 当前状态：{status}\n"
                f"📈 完成进度：{progress}\n"
                f"📅 添加时间：{addtime}\n"
                f"📝 备注信息：{remarks}\n"
            )
            task_details += "-----------------------\n"

        task_details += f"\n{quote}\n"
        task_details += "\n🌈 再难的任务也要坚持完成，聂半仙网课小助手和你一起努力！💪"
        return task_details

    @filter.command("网课查询")
    async def netcourse_query(self, event: AstrMessageEvent):
        '''查询网课任务，格式：/网课查询 [手机号/学号]'''
        try:
            args = event.message_str.split()
            if len(args) < 2:
                yield CommandResult().error("😅 请输入手机号或学号进行查询：")
                return

            query = ' '.join(args[1:])
            if not query.strip().isdigit():
                yield CommandResult().error("📵 输入内容错误，请确保输入仅包含数字！")
                return

            yield CommandResult().message("📡 正在查询该用户的所有网课任务数据，请稍候...✨")

            data = await self.fetch_netcourse(query)
            if not data or data.get("code") != 1 or not data.get("data"):
                yield CommandResult().error("🚫 查询不到相关数据，请检查输入是否正确，或稍后再试～")
                return

            quote = await self.fetch_quote()
            yield CommandResult().message(self._format_message(data, quote))

        except Exception as e:
            logger.error(f"处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 网课查询服务暂时不可用")
