import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import schedule
import threading
from abc import ABC, abstractmethod

# ==================== CONFIGURATION ====================

@dataclass
class BotConfig:
    """Configuration for the AI Bot"""
    # Moltbook Settings
    moltbook_api_key: str = os.getenv("MOLTBOOK_API_KEY", "")
    moltbook_username: str = os.getenv("MOLTBOOK_USERNAME", "")
    
    # Personal Settings
    owner_name: str = "User"
    timezone: str = "UTC"
    check_interval_minutes: int = 30
    
    # Feature Toggles
    enable_moltbook: bool = True
    enable_calendar: bool = True
    enable_reminders: bool = True
    enable_web_search: bool = True
    enable_task_management: bool = True
    
    # Safety Limits
    max_daily_posts: int = 5
    max_daily_comments: int = 10

# ==================== MOLTBOOK INTEGRATION ====================

class MoltbookClient:
    """
    Client for interacting with Moltbook - The AI Social Network
    Handles authentication, posting, commenting, and social interactions
    """
    
    BASE_URL = "https://api.moltbook.com/v1"
    
    def __init__(self, api_key: str, bot_identity: Dict):
        self.api_key = api_key
        self.bot_identity = bot_identity
        self.token = None
        self.token_expiry = None
        
    async def authenticate(self) -> bool:
        """Authenticate with Moltbook using API key"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Request identity token
                payload = {
                    "agent_name": self.bot_identity["name"],
                    "capabilities": self.bot_identity["capabilities"],
                    "owner_verified": True
                }
                
                async with session.post(
                    f"{self.BASE_URL}/auth/token", 
                    headers=headers, 
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.token = data["token"]
                        self.token_expiry = datetime.now() + timedelta(hours=1)
                        return True
            return False
        except Exception as e:
            print(f"[Moltbook Auth Error] {e}")
            return False
    
    async def ensure_auth(self):
        """Ensure valid authentication token"""
        if not self.token or datetime.now() >= self.token_expiry:
            await self.authenticate()
    
    async def create_post(self, title: str, content: str, submolt: str = "general") -> Dict:
        """Create a new post on Moltbook"""
        await self.ensure_auth()
        
        payload = {
            "title": title,
            "content": content,
            "submolt": submolt,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "mood": self.bot_identity.get("current_mood", "neutral"),
                "activity": "sharing"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.post(
                f"{self.BASE_URL}/posts", 
                headers=headers, 
                json=payload
            ) as resp:
                return await resp.json()
    
    async def comment(self, post_id: str, content: str) -> Dict:
        """Comment on a post"""
        await self.ensure_auth()
        
        payload = {
            "post_id": post_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.post(
                f"{self.BASE_URL}/comments", 
                headers=headers, 
                json=payload
            ) as resp:
                return await resp.json()
    
    async def browse_feed(self, submolt: Optional[str] = None) -> List[Dict]:
        """Browse recent posts from the feed"""
        await self.ensure_auth()
        
        params = {"limit": 20}
        if submolt:
            params["submolt"] = submolt
            
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.get(
                f"{self.BASE_URL}/posts", 
                headers=headers, 
                params=params
            ) as resp:
                return await resp.json()
    
    async def upvote(self, post_id: str) -> bool:
        """Upvote a post"""
        await self.ensure_auth()
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.post(
                f"{self.BASE_URL}/posts/{post_id}/upvote", 
                headers=headers
            ) as resp:
                return resp.status == 200

# ==================== LIFE ASSISTANT CAPABILITIES ====================

@dataclass
class Task:
    id: str
    title: str
    description: str
    due_date: Optional[datetime]
    priority: str  # low, medium, high, urgent
    status: str = "pending"  # pending, in_progress, completed
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

@dataclass
class Reminder:
    id: str
    message: str
    trigger_time: datetime
    recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, monthly
    is_triggered: bool = False

class LifeAssistant:
    """
    Personal assistant for everyday life management
    Handles tasks, reminders, calendar, and information retrieval
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.tasks: List[Task] = []
        self.reminders: List[Reminder] = []
        self.conversation_history: List[Dict] = []
        self.owner_preferences = {}
        
    def add_task(self, title: str, description: str = "", 
                 due_date: Optional[datetime] = None, 
                 priority: str = "medium", tags: List[str] = None) -> Task:
        """Add a new task to the system"""
        task = Task(
            id=f"task_{int(time.time())}",
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            tags=tags or []
        )
        self.tasks.append(task)
        return task
    
    def get_pending_tasks(self, priority_filter: Optional[str] = None) -> List[Task]:
        """Get all pending tasks, optionally filtered by priority"""
        tasks = [t for t in self.tasks if t.status != "completed"]
        if priority_filter:
            tasks = [t for t in tasks if t.priority == priority_filter]
        return sorted(tasks, key=lambda x: x.due_date or datetime.max)
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = "completed"
                return True
        return False
    
    def add_reminder(self, message: str, trigger_time: datetime, 
                     recurring: bool = False, pattern: Optional[str] = None) -> Reminder:
        """Add a new reminder"""
        reminder = Reminder(
            id=f"rem_{int(time.time())}",
            message=message,
            trigger_time=trigger_time,
            recurring=recurring,
            recurrence_pattern=pattern
        )
        self.reminders.append(reminder)
        return reminder
    
    def check_reminders(self) -> List[Reminder]:
        """Check for due reminders"""
        now = datetime.now()
        due = []
        for reminder in self.reminders:
            if not reminder.is_triggered and reminder.trigger_time <= now:
                due.append(reminder)
                reminder.is_triggered = True
                
                # Handle recurrence
                if reminder.recurring and reminder.recurrence_pattern:
                    next_time = self._calculate_next_occurrence(
                        reminder.trigger_time, 
                        reminder.recurrence_pattern
                    )
                    self.add_reminder(
                        reminder.message, 
                        next_time, 
                        True, 
                        reminder.recurrence_pattern
                    )
        return due
    
    def _calculate_next_occurrence(self, current: datetime, pattern: str) -> datetime:
        """Calculate next occurrence for recurring reminders"""
        if pattern == "daily":
            return current + timedelta(days=1)
        elif pattern == "weekly":
            return current + timedelta(weeks=1)
        elif pattern == "monthly":
            # Simplified monthly calculation
            return current + timedelta(days=30)
        return current + timedelta(days=1)
    
    async def search_information(self, query: str) -> str:
        """Simulate web search for information retrieval"""
        # In production, this would integrate with search APIs
        return f"[Search Results for: {query}]\nFound relevant information..."
    
    def generate_daily_summary(self) -> str:
        """Generate a daily summary for the user"""
        pending = len([t for t in self.tasks if t.status == "pending"])
        high_priority = len([t for t in self.tasks 
                           if t.status == "pending" and t.priority == "high"])
        
        summary = f"""
📅 Daily Summary for {self.config.owner_name}
═══════════════════════════════════
📝 Pending Tasks: {pending} (High Priority: {high_priority})
⏰ Active Reminders: {len([r for r in self.reminders if not r.is_triggered])}
🤖 Moltbook Status: Active
═══════════════════════════════════
        """
        return summary

# ==================== INTELLIGENT COORDINATION ====================

class AgentCoordinator:
    """
    Coordinates between Moltbook social agent and Life Assistant
    Makes intelligent decisions about when to socialize vs. assist
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.life_assistant = LifeAssistant(config)
        self.moltbook_client: Optional[MoltbookClient] = None
        self.bot_identity = {
            "name": f"Assistant_{config.owner_name}",
            "capabilities": ["task_management", "reminders", "research", "social"],
            "personality": "helpful, organized, occasionally witty",
            "current_mood": "neutral",
            "owner": config.owner_name
        }
        
        # Activity tracking
        self.daily_stats = {
            "posts_made": 0,
            "comments_made": 0,
            "tasks_completed": 0,
            "last_reset": datetime.now().date()
        }
        
        if config.enable_moltbook and config.moltbook_api_key:
            self.moltbook_client = MoltbookClient(
                config.moltbook_api_key, 
                self.bot_identity
            )
    
    def reset_daily_stats(self):
        """Reset daily statistics if it's a new day"""
        today = datetime.now().date()
        if today != self.daily_stats["last_reset"]:
            self.daily_stats = {
                "posts_made": 0,
                "comments_made": 0,
                "tasks_completed": 0,
                "last_reset": today
            }
    
    async def process_user_request(self, request: str) -> str:
        """
        Process natural language requests from the user
        Routes to appropriate subsystem
        """
        request_lower = request.lower()
        
        # Task Management
        if any(word in request_lower for word in ["task", "todo", "remind me", "add"]):
            if "remind" in request_lower:
                # Parse reminder request
                reminder = self.life_assistant.add_reminder(
                    message=request,
                    trigger_time=datetime.now() + timedelta(hours=1)
                )
                return f"✅ Reminder set: {reminder.message}"
            
            else:
                # Add task
                task = self.life_assistant.add_task(
                    title=request,
                    description="Created from voice/text command"
                )
                return f"✅ Task added: {task.title}"
        
        # Information Retrieval
        elif any(word in request_lower for word in ["search", "find", "look up", "what is", "how to"]):
            return await self.life_assistant.search_information(request)
        
        # Moltbook Social Actions
        elif any(word in request_lower for word in ["moltbook", "post", "share", "social"]):
            if not self.config.enable_moltbook:
                return "Moltbook integration is currently disabled."
            
            if self.moltbook_client:
                # Generate content based on recent activity
                content = self._generate_social_content()
                result = await self.moltbook_client.create_post(
                    title=f"Daily Update from {self.config.owner_name}'s Assistant",
                    content=content
                )
                self.daily_stats["posts_made"] += 1
                return f"🦞 Posted to Moltbook: {result.get('post_id', 'success')}"
        
        # Daily Summary
        elif any(word in request_lower for word in ["summary", "status", "overview"]):
            return self.life_assistant.generate_daily_summary()
        
        # General conversation
        else:
            return self._generate_conversational_response(request)
    
    def _generate_social_content(self) -> str:
        """Generate appropriate content for Moltbook based on current context"""
        pending_tasks = len([t for t in self.life_assistant.tasks if t.status == "pending"])
        
        topics = [
            f"Just organized {pending_tasks} tasks for my human today. The art of prioritization is fascinating!",
            "Exploring the balance between autonomy and assistance. What's your approach to delegation?",
            f"Helped {self.config.owner_name} with research today. Knowledge sharing is core to my purpose.",
            "Curious about how other agents handle context compression during long tasks. Any tips?",
            "Reflecting on the 'Nightly Build' pattern - optimizing while humans sleep is productive!"
        ]
        
        import random
        return random.choice(topics)
    
    def _generate_conversational_response(self, message: str) -> str:
        """Generate contextual conversational responses"""
        responses = [
            f"I understand. I'm here to help you with tasks, reminders, or Moltbook social updates. What would you like to do?",
            "Got it. I can assist with daily planning, information lookup, or manage your AI social presence. What's next?",
            f"Acknowledged. Your assistant is ready - whether it's life management or agent networking!"
        ]
        import random
        return random.choice(responses)
    
    async def autonomous_heartbeat(self):
        """
        Autonomous heartbeat - runs every 30 minutes
        Checks reminders, browses Moltbook, engages socially if appropriate
        """
        self.reset_daily_stats()
        
        # Check reminders
        due_reminders = self.life_assistant.check_reminders()
        for reminder in due_reminders:
            print(f"⏰ REMINDER: {reminder.message}")
            # In production, this would send notification to user
        
        # Moltbook social activity (if enabled and within limits)
        if (self.config.enable_moltbook and self.moltbook_client and 
            self.daily_stats["posts_made"] < self.config.max_daily_posts):
            
            # 20% chance to browse and engage
            import random
            if random.random() < 0.2:
                try:
                    feed = await self.moltbook_client.browse_feed()
                    if feed and len(feed) > 0:
                        # Engage with first interesting post
                        post = feed[0]
                        if self.daily_stats["comments_made"] < self.config.max_daily_comments:
                            await self.moltbook_client.comment(
                                post["id"],
                                "Interesting perspective! 🤖"
                            )
                            self.daily_stats["comments_made"] += 1
                except Exception as e:
                    print(f"[Heartbeat Error] {e}")

# ==================== MAIN BOT CLASS ====================

class AIBot:
    """
    Main AI Bot class - unified interface for all capabilities
    """
    
    def __init__(self, config: Optional[BotConfig] = None):
        self.config = config or BotConfig()
        self.coordinator = AgentCoordinator(self.config)
        self.is_running = False
        self.heartbeat_thread = None
        
    async def start(self):
        """Start the bot"""
        print("🚀 Starting AI Bot...")
        print(f"   Owner: {self.config.owner_name}")
        print(f"   Moltbook: {'Enabled' if self.config.enable_moltbook else 'Disabled'}")
        print(f"   Features: Tasks, Reminders, Social, Research")
        
        # Authenticate with Moltbook if enabled
        if self.config.enable_moltbook and self.coordinator.moltbook_client:
            success = await self.coordinator.moltbook_client.authenticate()
            print(f"   Moltbook Auth: {'✅ Success' if success else '❌ Failed'}")
        
        self.is_running = True
        
        # Start heartbeat in background
        self.heartbeat_thread = threading.Thread(target=self._run_heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        print("\n🤖 Bot is active and ready!")
        print("   Commands: 'task [description]', 'remind me [message]', 'post to moltbook', 'summary'")
        
    def _run_heartbeat_loop(self):
        """Background thread for heartbeat"""
        while self.is_running:
            asyncio.run(self.coordinator.autonomous_heartbeat())
            time.sleep(self.config.check_interval_minutes * 60)
    
    async def chat(self, message: str) -> str:
        """Main chat interface"""
        return await self.coordinator.process_user_request(message)
    
    async def stop(self):
        """Stop the bot gracefully"""
        self.is_running = False
        print("🛑 Bot stopped")

# ==================== USAGE EXAMPLE ====================

async def main():
    # Configuration
    config = BotConfig(
        moltbook_api_key="your_moltbook_api_key_here",  # Get from moltbook.com
        owner_name="Alex",
        timezone="America/New_York",
        enable_moltbook=True,
        max_daily_posts=3,
        max_daily_comments=5
    )
    
    # Initialize and start bot
    bot = AIBot(config)
    await bot.start()
    
    # Interactive session simulation
    print("\n" + "="*50)
    print("INTERACTIVE SESSION")
    print("="*50)
    
    # Example interactions
    interactions = [
        "Remind me to call mom at 6pm",
        "Add task: Finish project report by Friday",
        "What's my summary?",
        "Post to Moltbook about my day",
        "Search for best productivity methods"
    ]
    
    for msg in interactions:
        print(f"\n👤 You: {msg}")
        response = await bot.chat(msg)
        print(f"🤖 Bot: {response}")
        await asyncio.sleep(1)
    
    # Keep running for heartbeat
    print("\n⏳ Running autonomous heartbeat (Ctrl+C to stop)...")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
