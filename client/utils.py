import inspect, asyncio, sys, os
from io import BytesIO
from typing import Callable, Dict, List
from packaging.version import parse
import subprocess
import pkg_resources
import shutil

from client.app import client as app
from client.config import prefix, sn, logger, DATADIR, BASEDIR, TMPDIR, PIPPARSER

from pyrogram import __version__, handlers, filters, Client
from pyrogram.types import Message
from pyrogram.raw.functions.messages import ClearAllDrafts, SaveDraft
from pyrogram.raw import types

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

class Modules:
    def __init__(self, module, handler, dir, type, sn, command, help, doc):
        self.module = module
        self.handler = handler
        self.dir = dir
        self.type = type
        self.sn = sn
        self.command = command
        self.help = help
        self.doc = doc

def ImportPlugin(plugin):
    sys.path.append(DATADIR)
    __import__(plugin, globals(), locals(), level=0)

def GetText(file: str) -> str:
    content = str()
    try:
        with open(file, "r") as f:
            content = f.read()
    except:
        pass
    return content

async def InstallDependency(missing):
    try:
        if subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--root-user-action=ignore', *missing]) == 0:
            return True
    except:
        return False

async def CheckFile(content, plugin):
    packages = PIPPARSER.findall(content)
    if not ((content.find("@OnCmd") > -1 or content.find("@OnDraft") > -1 or content.find("@OnMsg") > -1 or content.find("@OnScheduler") > -1) and content.find("client.utils") > -1):
        logger.error(f"Invalid Plugin: {plugin}")
        return False
    if packages:
        packages = packages[-1].strip().split()
        required = set(packages)
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = required - installed
        if missing:
            if not await InstallDependency(missing):
                logger.error(f"Dependency installation failed: {plugin} - {packages}")
                return False
    return True

def CheckVer(version: str = ''):
    if version:
        if parse(version) <= parse(__version__.replace("v", "")):
            return True
    else:
        return True

async def loadPlugins():
    for file in os.listdir(DATADIR):
        if file.endswith('.py'):
            plugin = os.path.join(DATADIR, file)
            content = GetText(plugin)
            filename = os.path.basename(plugin)
            if await CheckFile(content, plugin):
                try:
                    ImportPlugin(file.replace(".py", ""))
                except Exception as e:
                    logger.error(f"Failed to import: {filename}\n{e}")
                else:
                    logger.info(f"Load Plugin: {filename}")
            else:
                logger.error(f"Failed to load: {filename}")

plugins: Dict[str, Modules] = {}

def register(func, caller, type, command, cron, filters, help, doc):
    global sn
    handler = None
    if type == "xOnCmd":
        module = func.__name__
    else:
        module = func.__module__
    dir = os.path.abspath(inspect.getfile(func))
    if module not in plugins:
        plugins[module] = {}
    if type == "OnDraft":
        handler = handlers.RawUpdateHandler(caller)
        app.add_handler(handler, group=sn)
    elif type in ["OnMsg", "OnCmd", "xOnCmd"]:
        handler = handlers.MessageHandler(caller, filters)
        app.add_handler(handler, group=sn)
    elif type == "OnScheduler":
        sn = -1000 - sn
        scheduler.add_job(caller, CronTrigger.from_crontab(cron, 'UTC'), id=str(sn))
    plugins[module] = Modules(module, handler, dir, type, sn, command, help, doc)
    sn += 1

def OnScheduler(cron: str, help: str = '', doc: str = '', version: str = '') -> Callable:
    def decorator(func: Callable) -> Callable:
        if CheckVer(version):
            logger.info(f"OnScheduler: {func.__module__}")
            register(func, func, "OnScheduler", None, cron, None, help, doc)
    return decorator

def OnMsg(filters: filters = None, help: str = '', doc: str = '', version: str = '') -> Callable:
    def decorator(func: Callable) -> Callable:
        if CheckVer(version):
            logger.info(f"OnMsg: {func.__module__}")
            register(func, func, "OnMsg", None, None, filters, help, doc)
    return decorator

def OnCmd(cmd: str, help: str = '', doc: str = '', version: str = ''):
    def decorator(func: Callable) -> Callable:
        async def caller(client, m):
            if bool(m.from_user and m.from_user.is_self or getattr(m, "outgoing", False)) and m.text and not bool(m.forward_date):
                payloads = m.text.strip().split()
                if len(payloads) > 0 and payloads[0] == f'{prefix}{cmd}':
                    chat_id = m.chat.id
                    args = payloads[1:]
                    reply = m.reply_to_message_id if m.reply_to_message_id else None
                    logger.info(f"OnCmd: {cmd} {' '.join(args)}")
                    await func(client, m, chat_id, args, reply)
        if CheckVer(version):
            type = "OnCmd"
            if str(func.__module__) == "client.utils":
                type = "xOnCmd"
            register(func, caller, type, cmd, None, None, help, doc)
        return caller
    return decorator

def OnDraft(draft: str, help: str = '', doc: str = '', version: str = '', clear: bool=True) -> Callable:
    def decorator(func: Callable) -> Callable:
        async def caller(client, update, users, chats):
            if isinstance(update, types.UpdateDraftMessage):
                if isinstance(update.draft, types.DraftMessage):
                    peer = update.peer
                    draft_msg = update.draft.message
                    if draft_msg:
                        payloads = draft_msg.strip().split()
                        if payloads[0] == f'{prefix}{draft}':
                            if isinstance(update.peer, types.PeerUser):
                                chat_id = update.peer.user_id
                            elif isinstance(update.peer, types.PeerChat):
                                chat_id = -update.peer.chat_id
                            elif isinstance(update.peer, types.PeerChannel):
                                chat_id = -1000000000000 - update.peer.channel_id
                            if clear:
                                await client.invoke(ClearAllDrafts())
                                #await client.invoke(SaveDraft(peer=await client.resolve_peer(peer_id=chat_id), message="1"))
                            reply = update.draft.reply_to_msg_id if update.draft.reply_to_msg_id else None
                            args = payloads[1:]
                            logger.info(f"OnDraft: {draft} {' '.join(args)}")
                            await func(client, update, chat_id, args, reply)
        if CheckVer(version):
            register(func, caller, "OnDraft", draft, None, None, help, doc)
        return caller
    return decorator

def PluginsList():
    plugins_list = []
    for k in plugins:
        if plugins[k].command:
            plugins_list.append(plugins[k].command)
        plugins_list.append(plugins[k].module)
    return plugins_list

async def delcmd(message):
    await asyncio.sleep(10)
    try:
        await message.delete()
    except:
        pass

@OnCmd("reload", help="重启 bot")
async def reload(_, message, __, ___, ____):
    await message.delete()
    os.execv(sys.executable, [sys.executable] + sys.argv)

@OnCmd("help", help="获取帮助")
async def help(_, message, __, args, ___):
    arg = args[0].replace(f"{prefix}", "") if len(args) >= 1 else ''
    if arg == '':
        context = f"🤖 **TMBot** `v{__version__}`\n\n"
        context_xcmd = str()
        context_cmd, context_draft, context_msg, context_Scheduler = str(), str(), str(), str()
        for k in plugins:
            if plugins[k].type == "xOnCmd":
                context_xcmd += f'`{prefix}{plugins[k].command}`：{plugins[k].help}\n'
            elif plugins[k].type in ["OnCmd", "OnDraft"]:
                if plugins[k].type == "OnCmd":
                    context_cmd += f'`{prefix}{plugins[k].command}`：{plugins[k].help}\n'
                elif plugins[k].type == "OnDraft":
                    context_draft += f'`{prefix}{plugins[k].command}`：{plugins[k].help}\n'
            elif plugins[k].type == "OnMsg":
                context_msg += f'`{plugins[k].module}`：{plugins[k].help}\n'
            elif plugins[k].type == "OnScheduler":
                context_Scheduler += f'`{plugins[k].module}`：{plugins[k].help}\n'
        context += "**⚑ㅤ系统指令**\n"
        context += f"{context_xcmd}"
        if context_cmd or context_draft:
            context += "\n**⚑ㅤ插件指令**\n"
            if context_cmd:
                context += "信息指令：\n"
                context += f"{context_cmd}"
            if context_draft:
                context += "\n草稿指令：\n"
                context += f"{context_draft}"
        if context_msg:
            context += "\n**⚑ㅤ无指令插件**\n"
            context += f"{context_msg}"
        if context_Scheduler:
            context += "\n**⚑ㅤ定时插件**\n"
            context += f"{context_Scheduler}"
    elif arg in ["help", "reload", "install", "export", "disable"]:
        context = f"⚑ㅤ`{prefix}{arg}` 的文档：\n\n"
        context += f"{plugins[arg].help}\n\n{plugins[arg].doc}"
    elif arg in PluginsList():
        context = f"⚑ㅤ**{arg}** 的文档：\n\n"
        for k in plugins:
            if arg == plugins[k].command or arg == plugins[k].module:
                if plugins[k].command:
                    context += f"指令：`{prefix}{plugins[k].command}`\n\n"
                context += f"{plugins[k].help}\n\n{plugins[k].doc}"
    elif arg not in PluginsList():
        context = f"✗ㅤ插件 `{arg}` 不存在~"
    await message.edit(context)
    await delcmd(message)

@OnCmd("install", help="安装插件")
async def install(client, message, _, __, reply):
    if reply:
        doc = message.reply_to_message.document
        if doc and (doc.file_name.endswith(".py")):
            await message.edit(f"安装中...")
            file = await client.download_media(message.reply_to_message, file_name=f"{TMPDIR}/")
            filename = os.path.basename(file)
            text = GetText(file)
            if await CheckFile(text, file):
                shutil.move(file, f'{DATADIR}/{filename}')
                flag = bool(filename.replace(".py", "") in sys.modules)
                try:
                    ImportPlugin(filename.replace(".py", ""))
                except Exception as e:
                    os.remove(f'{DATADIR}/{filename}')
                    logger.error(f"Failed to import: \n{e}")
                    await message.edit(f"✗ 安装失败~\n{e}")
                else:
                    logger.info(f"Install Plugin: {filename}")
                    await message.edit(f"✓ 安装成功，发送 `{prefix}help {filename.replace('.py','')}` 获取帮助~")
                    if flag:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                await message.edit("✗ 安装失败~")
                await delcmd(message)
        else:
            await message.edit("✗ 请回复一个 python 文件来安装！")
            await delcmd(message)
    else:
        await message.edit("✗ 请回复一个 python 文件来安装！")
        await delcmd(message)

ExportDoc=f"导出某个插件：`{prefix}export <插件名>`\n导出全部：`{prefix}export all`"
@OnCmd("export", help="导出插件", doc=ExportDoc)
async def export(client, message, chat_id, args, _):
    arg = args[0].replace(f"{prefix}", "") if len(args) >= 1 else ''
    context = f"`{prefix}export {arg}` \n\n"
    if arg == "all":
        for k in plugins:
            if plugins[k].type != "xOnCmd":
                plugin = plugins[k].command if plugins[k].command else plugins[k].module
                ctx = f'{context}获取插件 {plugin} 中...'
                await message.edit(ctx)
                await asyncio.sleep(5)
                await client.send_document(chat_id, plugins[k].dir, caption=plugins[k].help)
        await message.delete()
    elif arg in PluginsList():
        ctx = f'{context}获取插件 {arg} 中...'
        await message.edit(ctx)
        for k in plugins:
            if plugins[k].type == "xOnCmd":
                if arg == plugins[k].command:
                    context += f"系统插件 `{arg}` 将不会被导出。"
                    await message.edit(context)
                    break
            else:
                if arg == plugins[k].command or arg == plugins[k].module:
                    await client.send_document(chat_id, plugins[k].dir, caption=plugins[k].help)
                    await message.delete()
                    break
    elif arg not in PluginsList():
        if arg == '':
            context += ExportDoc
        else:
            context += f"插件 `{arg}` 不存在。"
        await message.edit(context)
        await delcmd(message)

@OnCmd("disable", help="禁用插件", doc=f"默认为暂时禁用，重启将会重新被启用。若要删除请添加 rm：\n`{prefix}disable <插件名> rm`")
async def disable(client, message, __, args, ___):
    PluginKey = ''
    arg = args[0].replace(f"{prefix}", "") if len(args) >= 1 else ''
    rm = args[1] if len(args) >= 2 else ''
    context = f"`{prefix}disable {arg}` \n\n"
    if arg in PluginsList():
        for k in plugins:
            if plugins[k].type == "xOnCmd":
                if arg == plugins[k].command:
                    context += f"✗ 系统插件 `{arg}` 将不会被禁用。"
                    PluginKey = plugins[k].type
                    break
            else:
                if arg == plugins[k].command:
                    app.remove_handler(plugins[k].handler, plugins[k].sn)
                    PluginKey = k
                    break
                elif arg == plugins[k].module:
                    if plugins[k].type == "OnMsg":
                        app.remove_handler(plugins[k].handler, plugins[k].sn)
                        PluginKey = k
                        break
                    elif plugins[k].type == "OnScheduler":
                        scheduler.remove_job(str(plugins[k].sn))
                        PluginKey = k
                        break
    if PluginKey:
        if PluginKey != "xOnCmd":
            plugin = f"{prefix}{plugins[PluginKey].command}" if plugins[PluginKey].command else plugins[PluginKey].module
            PluginDir = plugins[PluginKey].dir
            del plugins[PluginKey]
            del sys.modules[PluginKey]
            os.execv(sys.executable, [sys.executable] + sys.argv)
            if rm == "rm":
                os.remove(PluginDir)
                context += f"✓ 成功禁用插件 `{plugin}` 并已经成功删除~"
            else:
                context += f"✓ 成功禁用插件 `{plugin}`，重新启用请发送 `{prefix}reload`~"
    else:
        if PluginKey == '':
            context += f"请在指令后添加要禁用的插件，或发送 `{prefix}help disable` 获取帮助~"
        else:
            context += f"✗ 插件 {arg} 禁用失败，请检查 {arg} 是否存在并已启用~"
    await message.edit(context)
    await delcmd(message)
