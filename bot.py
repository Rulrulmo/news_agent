from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, time, timedelta
import re
import pytz
from env import TELEGRAM_BOT_TOKEN
from news_crew import NewsCrew

KOREA_TZ = pytz.timezone("Asia/Seoul")
DAILY_INTERVAL_SECONDS = 24 * 60 * 60
MAX_MESSAGE_LENGTH = 3000  # 텔레그램 메시지 최대 길이 (여유분 고려)


def kickoff_crew() -> str:
    """Get news briefing from crew."""
    news_crew = NewsCrew()
    result = news_crew.crew().kickoff()
    return result.raw


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """긴 메시지를 여러 개의 짧은 메시지로 분할합니다."""
    if len(text) <= max_length:
        return [text]

    messages = []
    current_message = ""

    # 줄 단위로 분할하여 처리
    lines = text.split("\n")

    for line in lines:
        # 현재 줄을 추가했을 때 길이가 초과하는지 확인
        if len(current_message + "\n" + line) > max_length:
            # 현재 메시지가 비어있지 않으면 저장
            if current_message:
                messages.append(current_message)
                current_message = ""

            # 한 줄 자체가 너무 긴 경우 강제로 분할
            if len(line) > max_length:
                while len(line) > max_length:
                    messages.append(line[:max_length])
                    line = line[max_length:]
                current_message = line
            else:
                current_message = line
        else:
            # 현재 메시지에 추가
            if current_message:
                current_message += "\n" + line
            else:
                current_message = line

    # 마지막 메시지 저장
    if current_message:
        messages.append(current_message)

    return messages


async def send_long_message(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str
) -> None:
    """긴 텍스트를 여러 메시지로 나누어 전송합니다."""
    messages = split_message(text)

    for i, message in enumerate(messages):
        if i > 0:
            # 첫 번째 메시지가 아닌 경우 메시지 번호 표시
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📰 뉴스 브리핑 ({i+1}/{len(messages)}):\n\n{message}",
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=f"📰 오늘의 뉴스 브리핑:\n\n{message}"
            )


def parse_time_string(time_str: str) -> time:
    """Parse time string in HH:MM format."""
    pattern = r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$"
    match = re.match(pattern, time_str)

    if not match:
        raise ValueError(
            "시간 형식이 올바르지 않습니다. HH:MM 형식으로 입력해주세요. (예: 09:30)"
        )

    return time(hour=int(match.group(1)), minute=int(match.group(2)))


def calculate_next_run_time(schedule_time: time) -> tuple[datetime, float]:
    """Calculate next run time and seconds until then."""
    now = datetime.now()
    target_time = datetime.combine(now.date(), schedule_time)

    if target_time <= now:
        target_time += timedelta(days=1)

    seconds_until = (target_time - now).total_seconds()
    return target_time, seconds_until


def format_time_display(dt: datetime, korea_tz: pytz.BaseTzInfo) -> str:
    """Format datetime for display in Korea timezone."""
    if dt.tzinfo is None:
        dt_utc = pytz.UTC.localize(dt)
    else:
        dt_utc = dt.astimezone(pytz.UTC)

    dt_korea = dt_utc.astimezone(korea_tz)
    return dt_korea.strftime("%Y-%m-%d %H:%M:%S")


# Job Functions
async def scheduled_news_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job that sends daily news briefing."""
    if not context.job or not context.job.chat_id:
        return

    chat_id = context.job.chat_id

    await context.bot.send_message(
        chat_id=chat_id, text="🕙 예정된 시간입니다! 뉴스 브리핑을 시작합니다..."
    )

    result = kickoff_crew()

    await send_long_message(context, chat_id, result)


async def set_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set daily news schedule."""
    if not update.message or not update.effective_chat:
        return

    if not context.job_queue:
        await update.message.reply_text(
            "❌ 스케줄링 기능을 사용할 수 없습니다. 봇을 다시 시작해주세요."
        )
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "⏰ 사용법: /schedule HH:MM\n"
            "예시: /schedule 09:00\n"
            "매일 지정된 시간에 뉴스 브리핑을 받을 수 있습니다."
        )
        return

    try:
        schedule_time = parse_time_string(context.args[0])
        chat_id = update.effective_chat.id

        current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        for job in current_jobs:
            job.schedule_removal()

        target_time, seconds_until = calculate_next_run_time(schedule_time)

        context.job_queue.run_repeating(
            scheduled_news_job,
            interval=DAILY_INTERVAL_SECONDS,
            first=seconds_until,
            chat_id=chat_id,
            name=str(chat_id),
        )

        await update.message.reply_text(
            f"✅ 매일 {target_time.strftime('%H:%M')}에 뉴스 브리핑을 보내드리겠습니다! (한국시간)\n"
            f"🕒 현재 시간: {datetime.now().strftime('%H:%M')} (한국시간)\n"
            f"🕒 첫 실행: {target_time.strftime('%Y-%m-%d %H:%M')} (한국시간)\n"
            f"⏰ {int(seconds_until // 60)}분 {int(seconds_until % 60)}초 후"
        )

    except ValueError as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")
    except Exception as e:
        await update.message.reply_text(
            f"❌ 스케줄 설정 중 오류가 발생했습니다: {str(e)}"
        )


async def cancel_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel daily news schedule."""
    if not update.message or not update.effective_chat or not context.job_queue:
        return

    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if not current_jobs:
        await update.message.reply_text("⚠️ 예약된 스케줄이 없습니다.")
        return

    for job in current_jobs:
        job.schedule_removal()

    await update.message.reply_text("❌ 뉴스 브리핑 스케줄이 취소되었습니다.")


async def check_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not context.job_queue:
        return

    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if not current_jobs:
        await update.message.reply_text("📅 예약된 스케줄이 없습니다.")
        return

    for job in current_jobs:
        next_run = job.next_run_time
        if next_run and isinstance(next_run, datetime):
            next_run_display = format_time_display(next_run, KOREA_TZ)
            current_time_display = datetime.now(KOREA_TZ).strftime("%Y-%m-%d %H:%M:%S")

            await update.message.reply_text(
                f"📅 현재 예약된 스케줄:\n"
                f"🕒 다음 실행: {next_run_display} (한국시간)\n"
                f"🕒 현재 시간: {current_time_display} (한국시간)"
            )


async def get_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    await update.message.reply_text(
        "🤖 뉴스 브리핑을 준비하고 있습니다. 잠시만 기다려주세요..."
    )

    result = kickoff_crew()
    chat_id = update.effective_chat.id

    await send_long_message(context, chat_id, result)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user:
        welcome_message = (
            f"안녕하세요 {update.effective_user.first_name}! 📰 뉴스 브리핑 봇입니다.\n\n"
            "사용 가능한 명령어:\n"
            "• /get → 즉시 뉴스 브리핑\n"
            "• /schedule HH:MM → 매일 정해진 시간에 뉴스 브리핑\n"
            "• /check → 현재 스케줄 상태 확인\n"
            "• /cancel → 예약된 뉴스 브리핑 취소\n\n"
            "예시: /schedule 10:00"
        )
        chat_id = update.effective_chat.id if update.effective_chat else ""
        await context.bot.send_message(chat_id=chat_id, text=welcome_message)


def run_bot() -> None:
    """Start the bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    handlers = [
        ("start", start),
        ("get", get_news),
        ("schedule", set_schedule),
        ("check", check_schedule),
        ("cancel", cancel_schedule),
    ]

    for command, handler in handlers:
        app.add_handler(CommandHandler(command, handler))

    app.run_polling()