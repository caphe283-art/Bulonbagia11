#!/usr/bin/env python3

import asyncio
import json
import os
import sys
import time
import re
import base64
import random
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
import aiohttp

API_BASE = "https://discord.com/api/v9"
POLL_INTERVAL = 60
HEARTBEAT_INTERVAL = 20
AUTO_ACCEPT = True
MAX_NO_QUEST_COUNT = 5

SUPPORTED_TASKS = [
    "WATCH_VIDEO",
    "PLAY_ON_DESKTOP",
    "STREAM_ON_DESKTOP",
    "PLAY_ACTIVITY",
    "WATCH_VIDEO_ON_MOBILE"
]

class Colors:
    reset = "\033[0m"
    green = "\033[92m"
    yellow = "\033[93m"
    red = "\033[91m"
    cyan = "\033[96m"
    magenta = "\033[95m"
    blue = "\033[94m"
    bold = "\033[1m"
    dim = "\033[2m"
    lightblack = "\033[90m"
    
    pink = "\033[38;2;255;105;180m"
    light_green = "\033[38;2;0;255;0m"
    light_cyan = "\033[38;2;0;255;255m"
    light_yellow = "\033[38;2;255;255;0m"
    white = "\033[38;2;255;255;255m"
    purple = "\033[38;2;186;85;211m"
    orange = "\033[38;2;255;140;0m"

RAINBOW = [Colors.red, Colors.yellow, Colors.green, Colors.cyan, Colors.blue, Colors.magenta]

def show_intro():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    art = [
        " ████████╗ ██████╗ ███╗   ███╗███╗   ███╗██╗   ██╗",
        " ╚══██╔══╝██╔═══██╗████╗ ████║████╗ ████║╚██╗ ██╔╝",
        "    ██║   ██║   ██║██╔████╔██║██╔████╔██║ ╚████╔╝ ",
        "    ██║   ██║   ██║██║╚██╔╝██║██║╚██╔╝██║  ╚██╔╝  ",
        "    ██║   ╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║   ██║   ",
        "    ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝   ╚═╝   ",
    ]
    
    print(f"\n {Colors.magenta}╔{'═' * 76}╗{Colors.reset}")
    for line in art:
        print(f" {Colors.magenta}║{Colors.reset} {random.choice(RAINBOW)}{line.center(74)}{Colors.reset} {Colors.magenta}║{Colors.reset}")
        time.sleep(0.01)
    print(f" {Colors.magenta}╠{'═' * 76}╣{Colors.reset}")
    print(f" {Colors.magenta}║{Colors.reset} {Colors.yellow}{'Cre: Dao Ngoc Khanh Aka Youngz Milo'.center(74)}{Colors.reset} {Colors.magenta}║{Colors.reset}")
    print(f" {Colors.magenta}╚{'═' * 76}╝{Colors.reset}\n")

def list_txt_files():
    files = []
    for f in os.listdir('.'):
        if f.endswith('.txt'):
            files.append(f)
    return files

def choose_token_file(label="CHON FILE TOKEN"):
    files = list_txt_files()
    
    if not files:
        print(f"\n {Colors.red}  X Khong co file .txt trong thu muc hien tai!{Colors.reset}")
        return None
    
    print(f"\n {Colors.cyan}  ┌─ {label} {'─' * (50 - len(label))}")
    for i, f in enumerate(files):
        print(f" {Colors.cyan}  │ {Colors.yellow}[{i+1}]{Colors.white} {f}")
    print(f" {Colors.cyan}  └{'─' * 52}")
    
    while True:
        try:
            idx = int(input(f"\n {Colors.yellow}  > Chon so: {Colors.reset}").strip()) - 1
            if 0 <= idx < len(files):
                return files[idx]
        except:
            pass
        print(f" {Colors.red}  X Nhap so tu 1 den {len(files)}.{Colors.reset}")

def read_tokens_from_file(path):
    tokens = []
    try:
        with open(path, encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith('#'):
                    tokens.append(l)
        return tokens
    except Exception as e:
        print(f" {Colors.red}  X Khong doc duoc file: {e}{Colors.reset}")
        return []

def get_token_input():
    show_intro()
    
    filepath = choose_token_file("CHON FILE TOKEN")
    if not filepath:
        print(f"\n {Colors.red}  [-] Khong tim thay file token!{Colors.reset}")
        sys.exit(1)
    
    tokens = read_tokens_from_file(filepath)
    if not tokens:
        print(f"\n {Colors.red}  X File token rong!{Colors.reset}")
        sys.exit(1)
    
    print(f"\n {Colors.green}  [+] Load {len(tokens)} token tu '{filepath}' thanh cong{Colors.reset}")
    time.sleep(1)
    return tokens

class DisplayManager:
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.displays = {}
            cls._instance.last_update = time.time()
        return cls._instance
    
    async def update(self, acc_index: int, acc_name: str, quest_name: str, current: float, total: float, status: str = "running"):
        async with self._lock:
            self.displays[acc_index] = {
                "name": acc_name,
                "quest": quest_name,
                "current": current,
                "total": total,
                "status": status,
                "last_update": time.time()
            }
            await self.render()
    
    async def remove(self, acc_index: int):
        async with self._lock:
            if acc_index in self.displays:
                del self.displays[acc_index]
                await self.render()
    
    async def set_idle(self, acc_index: int):
        async with self._lock:
            if acc_index in self.displays:
                self.displays[acc_index]["status"] = "idle"
                self.displays[acc_index]["quest"] = "Waiting for quest..."
                self.displays[acc_index]["current"] = 0
                self.displays[acc_index]["total"] = 0
                await self.render()
    
    async def set_done(self, acc_index: int, reason: str = "Done"):
        async with self._lock:
            if acc_index in self.displays:
                self.displays[acc_index]["status"] = "done"
                self.displays[acc_index]["quest"] = reason
                self.displays[acc_index]["current"] = 0
                self.displays[acc_index]["total"] = 0
                await self.render()
    
    async def render(self):
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        
        print(f"{Colors.bold}{Colors.cyan}╔══════════════════════════════════════════════════════════════════════════════╗{Colors.reset}")
        print(f"{Colors.bold}{Colors.cyan}║{Colors.yellow}                                TOOL AUTO ORB                                  {Colors.cyan}║{Colors.reset}")
        print(f"{Colors.bold}{Colors.cyan}║{Colors.white}                          By Viet Khanh X Ngoc Khanh                           {Colors.cyan}║{Colors.reset}")
        print(f"{Colors.bold}{Colors.cyan}╠══════════════════════════════════════════════════════════════════════════════╣{Colors.reset}")
        
        sorted_items = sorted(self.displays.items(), key=lambda x: x[0])
        
        if not sorted_items:
            print(f"{Colors.cyan}║{Colors.reset} {Colors.dim}Dang chay...{Colors.reset}{' ' * 60}{Colors.cyan}║{Colors.reset}")
        else:
            for acc_index, info in sorted_items:
                name = info["name"][:15] if info["name"] else f"ACC-{acc_index}"
                quest = info["quest"][:30]
                current = info["current"]
                total = info["total"]
                status = info["status"]
                
                if status == "running":
                    color = Colors.cyan
                    status_text = "▶"
                elif status == "completed":
                    color = Colors.green
                    status_text = "✓"
                elif status == "idle":
                    color = Colors.yellow
                    status_text = "⏳"
                elif status == "done":
                    color = Colors.green
                    status_text = "★"
                else:
                    color = Colors.dim
                    status_text = " "
                
                acc_display = f"[{name}]"
                
                if total > 0:
                    bar = self._draw_progress_bar(current, total, 35)
                    line = f" {color}{status_text}{Colors.reset} {Colors.cyan}{acc_display}{Colors.reset} {Colors.white}{quest}{Colors.reset} {bar}"
                else:
                    line = f" {color}{status_text}{Colors.reset} {Colors.cyan}{acc_display}{Colors.reset} {Colors.white}{quest}{Colors.reset}"
                
                visible_length = len(acc_display) + len(quest) + 45
                padding = max(0, 76 - visible_length)
                line += " " * padding
                
                print(f"{Colors.cyan}║{Colors.reset} {line} {Colors.cyan}║{Colors.reset}")
        
        print(f"{Colors.bold}{Colors.cyan}╚══════════════════════════════════════════════════════════════════════════════╝{Colors.reset}")
        print(f"{Colors.dim}▶ Youngz Ghosts{Colors.reset}")
        
        sys.stdout.flush()
    
    def _draw_progress_bar(self, current: float, total: float, width: int = 35) -> str:
        if total <= 0:
            return "░" * width + "   0.0%"
        percent = min(100, max(0, (current / total) * 100))
        filled = round((percent / 100) * width)
        empty = width - filled
        
        if percent < 30:
            bar_color = Colors.red
        elif percent < 70:
            bar_color = Colors.yellow
        else:
            bar_color = Colors.green
        
        bar = f"{bar_color}{'█' * filled}{Colors.dim}{'░' * empty}{Colors.reset}"
        return f"{bar} {percent:5.1f}%"

def get_val(data: Optional[Dict], *keys) -> Any:
    if not data:
        return None
    for k in keys:
        if k in data:
            return data[k]
    return None

def make_super_properties(build_number: int) -> str:
    obj = {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": "1.0.9175",
        "os_version": "10.0.26100",
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36",
        "browser_version": "32.2.7",
        "client_build_number": build_number,
        "native_build_number": 59498,
        "client_event_source": None
    }
    return base64.b64encode(json.dumps(obj).encode()).decode()

async def fetch_latest_build_number() -> int:
    fallback = 504649
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/app", headers={"User-Agent": ua}) as resp:
                if resp.status != 200:
                    return fallback
                text = await resp.text()
                env_match = re.search(r'GLOBAL_ENV\s*=\s*({.*?});', text)
                if env_match:
                    try:
                        env = json.loads(env_match.group(1))
                        if env.get("buildNumber"):
                            return int(env["buildNumber"])
                    except:
                        pass
                return fallback
    except:
        return fallback

class DiscordApi:
    def __init__(self, token: str, build_number: int):
        self.token = token
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36"
        sp = make_super_properties(build_number)
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": ua,
            "X-Super-Properties": sp,
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Ho_Chi_Minh",
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me"
        }
        self.username = None
        self.user_id = None
    
    async def get(self, path: str) -> Tuple[int, Dict]:
        url = f"{API_BASE}{path}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text) if text else {}
                    except:
                        data = {}
                    return resp.status, data
            except Exception as e:
                return 0, {"error": str(e)}
    
    async def post(self, path: str, payload: Dict = None) -> Tuple[int, Dict]:
        url = f"{API_BASE}{path}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text) if text else {}
                    except:
                        data = {}
                    return resp.status, data
            except Exception as e:
                return 0, {"error": str(e)}
    
    async def validate_token(self) -> bool:
        status, data = await self.get("/users/@me")
        if status == 200:
            self.username = data.get("username", data.get("global_name", "Unknown"))
            self.user_id = data.get("id", "?")
            return True
        return False

def get_task_config(quest: Dict) -> Optional[Dict]:
    cfg = quest.get("config", {})
    return get_val(cfg, "taskConfig", "task_config", "taskConfigV2", "task_config_v2")

def get_quest_name(quest: Dict) -> str:
    cfg = quest.get("config", {})
    msgs = cfg.get("messages", {})
    name = get_val(msgs, "questName", "quest_name")
    if name:
        return name.strip()
    game = get_val(msgs, "gameTitle", "game_title")
    if game:
        return game.strip()
    app_name = cfg.get("application", {}).get("name")
    if app_name:
        return app_name
    return f"Quest"

def get_expires_at(quest: Dict) -> Optional[str]:
    cfg = quest.get("config", {})
    return get_val(cfg, "expiresAt", "expires_at")

def is_completable(quest: Dict) -> bool:
    expires = get_expires_at(quest)
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if exp_dt <= datetime.now(timezone.utc):
                return False
        except:
            pass
    tc = get_task_config(quest)
    if not tc or not tc.get("tasks"):
        return False
    tasks = tc["tasks"]
    return any(t in tasks for t in SUPPORTED_TASKS)

def is_enrolled(quest: Dict) -> bool:
    us = get_user_status(quest)
    return bool(get_val(us, "enrolledAt", "enrolled_at"))

def get_user_status(quest: Dict) -> Dict:
    us = get_val(quest, "userStatus", "user_status")
    return us if isinstance(us, dict) else {}

def is_completed(quest: Dict) -> bool:
    us = get_user_status(quest)
    return bool(get_val(us, "completedAt", "completed_at"))

def get_task_type(quest: Dict) -> Optional[str]:
    tc = get_task_config(quest)
    if not tc or not tc.get("tasks"):
        return None
    tasks = tc["tasks"]
    for t in SUPPORTED_TASKS:
        if t in tasks:
            return t
    return None

def get_seconds_needed(quest: Dict) -> int:
    tc = get_task_config(quest)
    task_type = get_task_type(quest)
    if not tc or not task_type:
        return 0
    return tc["tasks"][task_type].get("target", 0)

def get_seconds_done(quest: Dict) -> int:
    task_type = get_task_type(quest)
    if not task_type:
        return 0
    us = get_user_status(quest)
    progress = us.get("progress", {})
    return progress.get(task_type, {}).get("value", 0)

@dataclass
class QuestAutocompleter:
    api: DiscordApi
    account_index: int = 0
    display: DisplayManager = field(default_factory=DisplayManager)
    completed_ids: Set[str] = field(default_factory=set)
    no_quest_count: int = 0
    max_no_quest: int = MAX_NO_QUEST_COUNT
    is_done: bool = False
    
    async def fetch_quests(self) -> List[Dict]:
        status, data = await self.api.get("/quests/@me")
        if status == 200:
            if isinstance(data, dict):
                quests = data.get("quests", [])
                if not quests:
                    quests = data.get("data", [])
                return quests
            elif isinstance(data, list):
                return data
            return []
        elif status == 429:
            retry_after = data.get("retry_after", 10)
            await asyncio.sleep(retry_after)
            return await self.fetch_quests()
        else:
            return []
    
    async def enroll_quest(self, quest: Dict) -> bool:
        qid = quest.get("id")
        if not qid:
            return False
        payload = {"location": 11, "is_targeted": False}
        if "traffic_metadata_raw" in quest:
            payload["traffic_metadata_raw"] = quest["traffic_metadata_raw"]
        if "traffic_metadata_sealed" in quest:
            payload["traffic_metadata_sealed"] = quest["traffic_metadata_sealed"]
        status, data = await self.api.post(f"/quests/{qid}/enroll", payload)
        return status in [200, 201, 204]
    
    async def auto_accept_quests(self, quests: List[Dict]) -> List[Dict]:
        if not AUTO_ACCEPT:
            return quests
        unaccepted = [q for q in quests if not is_enrolled(q) and not is_completed(q) and is_completable(q)]
        for q in unaccepted:
            await self.enroll_quest(q)
            await asyncio.sleep(1)
        if unaccepted:
            await asyncio.sleep(2)
            return await self.fetch_quests()
        return quests
    
    async def complete_video(self, quest: Dict):
        name = get_quest_name(quest)
        qid = quest.get("id")
        if not qid:
            return
        sec_needed = get_seconds_needed(quest)
        sec_done = get_seconds_done(quest)
        if sec_needed <= 0:
            return
        while sec_done < sec_needed:
            timestamp = sec_done + 7
            status, data = await self.api.post(f"/quests/{qid}/video-progress", {"timestamp": min(sec_needed, timestamp)})
            if status == 200:
                if data.get("completed_at"):
                    return
                sec_done = min(sec_needed, timestamp)
            elif status == 429:
                retry_after = data.get("retry_after", 5)
                await asyncio.sleep(retry_after + 1)
                continue
            await self.display.update(self.account_index, self.api.username or f"ACC-{self.account_index}", name, sec_done, sec_needed, "running")
            await asyncio.sleep(7)
    
    async def complete_heartbeat(self, quest: Dict):
        name = get_quest_name(quest)
        qid = quest.get("id")
        if not qid:
            return
        task_type = get_task_type(quest)
        sec_needed = get_seconds_needed(quest)
        sec_done = get_seconds_done(quest)
        if sec_needed <= 0:
            return
        pid = random.randint(1000, 30000)
        while sec_done < sec_needed:
            status, data = await self.api.post(f"/quests/{qid}/heartbeat", {"stream_key": f"call:0:{pid}", "terminal": False})
            if status == 200:
                prog = data.get("progress", {})
                if task_type in prog:
                    sec_done = prog[task_type].get("value", sec_done)
                if data.get("completed_at") or sec_done >= sec_needed:
                    return
            elif status == 429:
                retry_after = data.get("retry_after", 10)
                await asyncio.sleep(retry_after + 1)
                continue
            await self.display.update(self.account_index, self.api.username or f"ACC-{self.account_index}", name, sec_done, sec_needed, "running")
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        await self.api.post(f"/quests/{qid}/heartbeat", {"stream_key": f"call:0:{pid}", "terminal": True})
    
    async def process_quest(self, quest: Dict):
        qid = quest.get("id")
        if not qid or qid in self.completed_ids:
            return
        task_type = get_task_type(quest)
        if not task_type:
            return
        
        self.no_quest_count = 0
        
        if task_type in ["WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"]:
            await self.complete_video(quest)
        elif task_type in ["PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP", "PLAY_ACTIVITY"]:
            await self.complete_heartbeat(quest)
        
        self.completed_ids.add(qid)
    
    async def run(self):
        await self.display.update(self.account_index, self.api.username or f"ACC-{self.account_index}", "Initializing...", 0, 0, "idle")
        
        while not self.is_done:
            try:
                quests = await self.fetch_quests()
                
                if quests:
                    quests = await self.auto_accept_quests(quests)
                    
                    actionable = [q for q in quests if is_enrolled(q) and not is_completed(q) and is_completable(q)]
                    
                    if actionable:
                        self.no_quest_count = 0
                        for q in actionable:
                            if q.get("id") not in self.completed_ids:
                                await self.process_quest(q)
                    else:
                        self.no_quest_count += 1
                        await self.display.set_idle(self.account_index)
                        
                        if self.no_quest_count >= self.max_no_quest:
                            self.is_done = True
                            await self.display.set_done(self.account_index, f"Done - No quests")
                            break
                else:
                    self.no_quest_count += 1
                    await self.display.set_idle(self.account_index)
                    
                    if self.no_quest_count >= self.max_no_quest:
                        self.is_done = True
                        await self.display.set_done(self.account_index, f"Done - No quests")
                        break
                
                await asyncio.sleep(POLL_INTERVAL)
                
            except Exception as e:
                self.no_quest_count += 1
                await asyncio.sleep(30)

async def run_single_account(token: str, build_number: int, index: int):
    api = DiscordApi(token, build_number)
    
    if not await api.validate_token():
        return
    
    completer = QuestAutocompleter(api, index + 1)
    await completer.run()

async def main():
    tokens = get_token_input()
    if not tokens:
        print(f"\n {Colors.red}  X Khong co token nao duoc cung cap!{Colors.reset}")
        sys.exit(1)
    
    build_number = await fetch_latest_build_number()
    
    tasks = []
    for i, token in enumerate(tokens):
        task = asyncio.create_task(run_single_account(token, build_number, i))
        tasks.append(task)
        await asyncio.sleep(0.5)
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.yellow}Da dung chuong trinh.{Colors.reset}")
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.yellow}Da dung chuong trinh.{Colors.reset}")
        sys.exit(0)