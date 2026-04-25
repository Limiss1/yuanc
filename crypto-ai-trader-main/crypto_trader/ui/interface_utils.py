import asyncio
import psutil


def format_bytes(size):
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} YB"


async def start_timer(timer):
    count = 1
    while True:
        count += 1
        mins, sec = divmod(count, 60)
        hour, mins = divmod(mins, 60)
        days, hour = divmod(hour, 24)
        timer.log(f"Uptime: {days:>3} day(s), {hour:02}:{mins:02}:{sec:02}", save_log=False)
        await asyncio.sleep(1)


async def start_process_monitor(process_monitor):
    process = psutil.Process()
    while True:
        try:
            with process.oneshot():
                threads = process.num_threads()
                cpu = process.cpu_percent()
                mem = process.memory_info()
                process_monitor.log(
                    f"CPU: {cpu:>5}%, Mem: {mem.rss / 1024 / 1024:.0f}MB, Threads: {threads}",
                    save_log=False,
                )
        except Exception:
            pass
        await asyncio.sleep(1)


async def start_trade_monitor(trade_monitor, app=None):
    trade_monitor.log("Trades: 0, Total P&L: 0.00 USDT, Return %: 0.00%", save_log=False)

    while True:
        try:
            if app is not None and app._engine_running:
                trade_count = app._trade_count
                total_pnl = app._total_pnl
                return_pct = app._return_pct
                trade_monitor.log(
                    f"Trades: {trade_count}, "
                    f"Total P&L: {total_pnl:+.2f} USDT, "
                    f"Return %: {return_pct:+.2%}",
                    save_log=False,
                )
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(2.0)
