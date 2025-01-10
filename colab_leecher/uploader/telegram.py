# copyright 2023 © Xron Trix | https://github.com/Xrontrix10

import logging
from PIL import Image
from asyncio import sleep, Lock
from os import path as ospath
from datetime import datetime
from pyrogram.errors import FloodWait
from colab_leecher.utility.variables import BOT, Transfer, BotTimes, Messages, MSG, Paths
from colab_leecher.utility.helper import sizeUnit, fileType, getTime, status_bar, thumbMaintainer, videoExtFix

# Add this global variable
upload_semaphore = Lock()

async def progress_bar(current, total):
    global status_msg, status_head
    upload_speed = 4 * 1024 * 1024
    elapsed_time_seconds = (datetime.now() - BotTimes.task_start).seconds
    if current > 0 and elapsed_time_seconds > 0:
        upload_speed = current / elapsed_time_seconds
    eta = (Transfer.total_down_size - current - sum(Transfer.up_bytes)) / upload_speed
    percentage = (current + sum(Transfer.up_bytes)) / Transfer.total_down_size * 100
    await status_bar(
        down_msg=Messages.status_head,
        speed=f"{sizeUnit(upload_speed)}/s",
        percentage=percentage,
        eta=getTime(eta),
        done=sizeUnit(current + sum(Transfer.up_bytes)),
        left=sizeUnit(Transfer.total_down_size),
    )

async def upload_file(file_path, og_file_name):
    global BOT, MSG, BotTimes, Messages, Paths, Transfer

    file_name = ospath.basename(file_path)
    file_type = fileType(file_path)
    og_file_name = og_file_name.replace("_", " ")

    Messages.status_head = f"<b>📤 UPLOADING » </b>\n\n<code>{og_file_name}</code>\n"
    BotTimes.task_start = datetime.now()

    if file_type == "video" and BOT.Setting.stream_upload == "video":
        await videoExtFix(file_path)
        thumb_path = await thumbMaintainer(file_path)
        width, height, duration = await videoExtFix(file_path)
        try:
            async with upload_semaphore:
                MSG.sent_file = await MSG.sent_msg.reply_video(
                    video=file_path,
                    caption=f"**{og_file_name}**",
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=thumb_path,
                    supports_streaming=True,
                    progress=progress_bar,
                )
        except FloodWait as e:
            await sleep(e.value)
            return await upload_file(file_path, og_file_name)

    elif file_type == "audio":
        thumb_path = Paths.THMB_PATH if ospath.exists(Paths.THMB_PATH) else None
        try:
            async with upload_semaphore:
                MSG.sent_file = await MSG.sent_msg.reply_audio(
                    audio=file_path,
                    caption=f"**{og_file_name}**",
                    thumb=thumb_path,
                    progress=progress_bar,
                )
        except FloodWait as e:
            await sleep(e.value)
            return await upload_file(file_path, og_file_name)

    elif file_type == "document":
        if BOT.Setting.stream_upload == "document" and ospath.getsize(file_path) > 2000 * 1000 * 1000:
            try:
                with Image.open(Paths.THMB_PATH) as img:
                    width, height = img.size
                async with upload_semaphore:
                    MSG.sent_file = await MSG.sent_msg.reply_document(
                        document=file_path,
                        caption=f"**{og_file_name}**",
                        thumb=Paths.THMB_PATH,
                        force_document=True,
                        progress=progress_bar,
                    )
            except FloodWait as e:
                await sleep(e.value)
                return await upload_file(file_path, og_file_name)
        else:
            try:
                async with upload_semaphore:
                    MSG.sent_file = await MSG.sent_msg.reply_document(
                        document=file_path,
                        caption=f"**{og_file_name}**",
                        force_document=True,
                        progress=progress_bar,
                    )
            except FloodWait as e:
                await sleep(e.value)
                return await upload_file(file_path, og_file_name)

    Transfer.up_bytes.append(ospath.getsize(file_path))
    Transfer.sent_file.append(MSG.sent_file)
    Transfer.sent_file_names.append(og_file_name)

async def TelegramUploader():
    for dirpath, _, filenames in ospath.walk(Paths.down_path):
        for f in sorted(filenames):
            up_path = ospath.join(dirpath, f)
            await upload_file(up_path, f)
    return True