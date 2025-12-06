from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import random
import uuid
from typing import Dict, List, Set
import time
import os

app = FastAPI(title="Monkeytype 多人打字竞速")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 游戏数据存储
class GameManager:
    def __init__(self):
        self.connected_users: Dict[str, WebSocket] = {}
        self.user_data: Dict[str, Dict] = {}
        self.rooms: Dict[str, Dict] = {}
        self.room_timers: Dict[str, asyncio.Task] = {}
        self.room_countdowns: Dict[str, asyncio.Task] = {}
        self.init_default_rooms()
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.connected_users[user_id] = websocket
        
    def disconnect(self, user_id: str):
        if user_id in self.connected_users:
            del self.connected_users[user_id]
        
        # 处理用户离开房间
        user_data = self.user_data.get(user_id, {})
        if 'room_id' in user_data:
            room_id = user_data['room_id']
            self.leave_room(user_id, room_id)
            
        if user_id in self.user_data:
            del self.user_data[user_id]
    
    def register_user(self, user_id: str, username: str):
        self.user_data[user_id] = {
            'id': user_id,
            'username': username,
            'room_id': None,
            'ready': False,
            'joined_at': time.time()
        }
    
    def load_chinese_texts(self):
        """加载中文文本"""
        try:
            lib_path = os.path.join(os.path.dirname(__file__), 'lib.txt')
            with open(lib_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析文本，每段以数字序号开头，后跟内容
            texts = []
            lines = content.strip().split('\n')
            i = 0
            while i < len(lines):
                if lines[i].strip().isdigit():
                    # 找到序号，下一行是内容
                    if i + 1 < len(lines):
                        text = lines[i + 1].strip()
                        if text:  # 确保内容不为空
                            texts.append(text)
                    i += 2  # 跳过序号和内容行
                else:
                    i += 1

            return texts
        except Exception as e:
            print(f"加载中文文本失败: {e}")
            return []

    def init_default_rooms(self):
        """初始化10个默认房间，前5个英文，后5个中文"""
        chinese_texts = self.load_chinese_texts()

        for i in range(1, 11):
            room_id = f"room{i}"
            is_chinese = i > 5  # room6-room10 为中文房间

            room_data = {
                'id': room_id,
                'users': [],
                'owner': None,  # 房主ID
                'game_started': False,
                'words': [],
                'text': '',  # 中文文本
                'room_type': 'chinese' if is_chinese else 'english',
                'start_time': None,
                'game_duration': 60,  # 60秒
                'player_progress': {},  # {user_id: {word_index, char_index, words_completed}}
                'created_at': time.time()
            }

            self.rooms[room_id] = room_data
    
    def join_room(self, user_id: str, room_id: str) -> bool:
        if room_id not in self.rooms:
            return False
            
        room = self.rooms[room_id]
        # 移除人数限制，允许多人加入
            
        if user_id not in room['users']:
            room['users'].append(user_id)
            self.user_data[user_id]['room_id'] = room_id
            self.user_data[user_id]['ready'] = False
            room['player_progress'][user_id] = {
                'word_index': 0,
                'char_index': 0,
                'words_completed': 0,
                'cursor_position': 0
            }
            
            # 如果房间为空，第一个加入的人成为房主
            if room['owner'] is None:
                room['owner'] = user_id
                
        return True
    
    def leave_room(self, user_id: str, room_id: str):
        if room_id in self.rooms:
            room = self.rooms[room_id]
            if user_id in room['users']:
                room['users'].remove(user_id)
                if user_id in room['player_progress']:
                    del room['player_progress'][user_id]
                
            # 如果离开的是房主，将房主转移给第一个用户
            if room['owner'] == user_id:
                if len(room['users']) > 0:
                    room['owner'] = room['users'][0]
                else:
                    room['owner'] = None
                
            # 取消倒计时
            if room_id in self.room_countdowns:
                self.room_countdowns[room_id].cancel()
                del self.room_countdowns[room_id]
                
            # 如果房间为空，重置房间
            if len(room['users']) == 0:
                if room_id in self.room_timers:
                    self.room_timers[room_id].cancel()
                    del self.room_timers[room_id]
                room['game_started'] = False
                room['words'] = []
                room['start_time'] = None
                room['owner'] = None
            else:
                # 如果还有用户，停止游戏
                room['game_started'] = False
                if room_id in self.room_timers:
                    self.room_timers[room_id].cancel()
                    del self.room_timers[room_id]
                
        # 更新用户数据
        if user_id in self.user_data:
            self.user_data[user_id]['room_id'] = None
            self.user_data[user_id]['ready'] = False
    
    async def start_countdown(self, room_id: str):
        """5秒倒计时后开始游戏"""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        if len(room['users']) == 0:
            return
        
        # 生成单词列表
        room['words'] = self.generate_words()
        
        # 发送倒计时
        for countdown in range(5, 0, -1):
            if room_id not in self.rooms or len(self.rooms[room_id]['users']) == 0:
                return
                
            for user_id in room['users']:
                if user_id in self.connected_users:
                    await self.send_message(user_id, {
                        'type': 'countdown',
                        'seconds': countdown
                    })
            
            await asyncio.sleep(1)
        
        # 开始游戏
        if room_id in self.rooms and len(self.rooms[room_id]['users']) > 0:
            await self.start_game(room_id)
    
    async def start_game(self, room_id: str):
        """开始游戏"""
        if room_id not in self.rooms:
            return

        room = self.rooms[room_id]
        room['game_started'] = True
        room['start_time'] = time.time()

        # 根据房间类型生成内容
        if room['room_type'] == 'chinese':
            room['text'] = self.generate_chinese_text()
        else:
            room['words'] = self.generate_words()

        # 重置所有玩家进度
        for user_id in room['users']:
            room['player_progress'][user_id] = {
                'word_index': 0,
                'char_index': 0,
                'words_completed': 0,
                'cursor_position': 0
            }

        # 通知所有用户游戏开始
        for user_id in room['users']:
            if user_id in self.connected_users:
                message = {
                    'type': 'game_started',
                    'room_id': room_id,
                    'duration': room['game_duration'],
                    'room_type': room['room_type']
                }
                if room['room_type'] == 'chinese':
                    message['text'] = room['text']
                    message['solo'] = False
                else:
                    message['words'] = room['words']
                    message['solo'] = False
                await self.send_message(user_id, message)

        # 启动游戏计时器
        self.room_timers[room_id] = asyncio.create_task(self.game_timer(room_id))
    
    async def start_solo_game(self, room_id: str):
        """开始单人练习游戏"""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        if len(room['users']) != 1:
            return  # 必须是单人模式
        
        room['game_started'] = True
        room['start_time'] = time.time()

        # 根据房间类型生成内容
        if room['room_type'] == 'chinese':
            room['text'] = self.generate_chinese_text()
        else:
            room['words'] = self.generate_words()

        # 重置玩家进度
        user_id = room['users'][0]
        room['player_progress'][user_id] = {
            'word_index': 0,
            'char_index': 0,
            'words_completed': 0,
            'cursor_position': 0
        }

        # 通知用户游戏开始
        if user_id in self.connected_users:
            message = {
                'type': 'game_started',
                'room_id': room_id,
                'duration': room['game_duration'],
                'solo': True,
                'room_type': room['room_type']
            }
            if room['room_type'] == 'chinese':
                message['text'] = room['text']
            else:
                message['words'] = room['words']
            await self.send_message(user_id, message)
        
        # 启动游戏计时器
        self.room_timers[room_id] = asyncio.create_task(self.game_timer(room_id))
    
    async def game_timer(self, room_id: str):
        """游戏计时器，根据房间设置的时长结束"""
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        duration = room.get('game_duration', 60)
        await asyncio.sleep(duration)  # 使用房间设置的时长
        
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        if not room['game_started']:
            return
        
        # 计算结果
        results = {}
        for user_id in room['users']:
            progress = room['player_progress'].get(user_id, {})
            words_completed = progress.get('words_completed', 0)
            results[user_id] = {
                'username': self.user_data[user_id]['username'],
                'words_completed': words_completed
            }
        
        # 发送结果
        for user_id in room['users']:
            if user_id in self.connected_users:
                await self.send_message(user_id, {
                    'type': 'game_ended',
                    'results': results
                })
        
        # 重置房间
        room['game_started'] = False
        room['words'] = []
        room['start_time'] = None
        for user_id in room['users']:
            room['player_progress'][user_id] = {
                'word_index': 0,
                'char_index': 0,
                'words_completed': 0,
                'cursor_position': 0
            }
    
    def generate_chinese_text(self) -> str:
        """生成中文文本，从lib.txt中随机选择两段"""
        chinese_texts = self.load_chinese_texts()
        if len(chinese_texts) < 2:
            return "这是一个中文打字测试。请快速准确地输入这段文字。"

        # 随机选择两段不同的文本
        selected_indices = random.sample(range(len(chinese_texts)), min(2, len(chinese_texts)))
        selected_texts = [chinese_texts[i] for i in selected_indices]

        # 合并成一段文本
        return ''.join(selected_texts)

    def generate_words(self) -> List[str]:
        """生成随机单词列表"""
        word_list = [
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
            'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
            'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
            'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
            'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
            'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
            'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us',
            'hello', 'world', 'python', 'fastapi', 'websocket', 'typing', 'speed', 'game',
            'multiplayer', 'competition', 'keyboard', 'practice', 'improve', 'skills', 'challenge'
        ]
        
        # 生成100个单词
        selected_words = []
        for _ in range(100):
            selected_words.append(random.choice(word_list))
        return selected_words
    
    async def update_player_progress(self, user_id: str, word_index: int, char_index: int, words_completed: int, cursor_position: int):
        """更新玩家进度"""
        user_data = self.user_data.get(user_id, {})
        if 'room_id' not in user_data:
            return
            
        room_id = user_data['room_id']
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        if not room['game_started']:
            return
        
        # 更新进度
        room['player_progress'][user_id] = {
            'word_index': word_index,
            'char_index': char_index,
            'words_completed': words_completed,
            'cursor_position': cursor_position
        }
        
        # 广播给房间内其他用户（包括所有玩家的进度）
        all_progress = {}
        for uid in room['users']:
            if uid in room['player_progress']:
                progress = room['player_progress'][uid]
                user_info = self.user_data.get(uid, {})
                all_progress[uid] = {
                    'username': user_info.get('username', ''),
                    'word_index': progress.get('word_index', 0),
                    'char_index': progress.get('char_index', 0),
                    'words_completed': progress.get('words_completed', 0),
                    'cursor_position': progress.get('cursor_position', 0)
                }
        
        for other_user_id in room['users']:
            if other_user_id in self.connected_users:
                await self.send_message(other_user_id, {
                    'type': 'players_progress',
                    'all_progress': all_progress
                })
    
    def get_room_data(self, room_id: str) -> Dict:
        if room_id not in self.rooms:
            return None
            
        room = self.rooms[room_id].copy()
        room['users'] = [
            {
                'id': uid,
                'username': self.user_data[uid]['username']
            }
            for uid in room['users']
        ]
        # 添加房主信息
        if room['owner']:
            owner_data = self.user_data.get(room['owner'], {})
            room['owner_username'] = owner_data.get('username', '')
        else:
            room['owner_username'] = ''
        return room
    
    def get_all_rooms(self) -> List[Dict]:
        """获取所有房间信息"""
        rooms = []
        for room_id in sorted(self.rooms.keys()):
            room_data = self.get_room_data(room_id)
            if room_data:
                rooms.append(room_data)
        return rooms
    
    def get_online_users(self) -> List[Dict]:
        online_users = []
        for user_id, user_data in self.user_data.items():
            if user_id in self.connected_users:
                online_users.append({
                    'id': user_id,
                    'username': user_data['username'],
                    'room_id': user_data['room_id']
                })
        return online_users
    
    async def send_message(self, user_id: str, message: Dict):
        if user_id in self.connected_users:
            try:
                await self.connected_users[user_id].send_text(json.dumps(message))
            except:
                pass
    
    async def broadcast_user_update(self):
        """广播用户列表更新"""
        online_users = self.get_online_users()
        
        for user_id in self.user_data:
            if user_id in self.connected_users:
                await self.send_message(user_id, {
                    'type': 'users_update',
                    'users': online_users
                })
    
    async def broadcast_rooms_update(self):
        """广播房间列表更新"""
        rooms = self.get_all_rooms()
        
        for user_id in self.user_data:
            if user_id in self.connected_users:
                await self.send_message(user_id, {
                    'type': 'rooms_update',
                    'rooms': rooms
                })

# 全局游戏管理器
game_manager = GameManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user_id = str(uuid.uuid4())
    
    await game_manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_websocket_message(user_id, message)
            
    except WebSocketDisconnect:
        game_manager.disconnect(user_id)
        await game_manager.broadcast_user_update()
        await game_manager.broadcast_rooms_update()

async def handle_websocket_message(user_id: str, message: Dict):
    message_type = message.get('type')
    
    if message_type == 'join_lobby':
        username = message.get('username', '匿名用户')
        game_manager.register_user(user_id, username)
        
        # 发送当前在线用户和房间信息
        await game_manager.send_message(user_id, {
            'type': 'users_update',
            'users': game_manager.get_online_users()
        })
        
        await game_manager.send_message(user_id, {
            'type': 'rooms_update',
            'rooms': game_manager.get_all_rooms()
        })
        
        # 广播用户加入
        await game_manager.broadcast_user_update()
        await game_manager.broadcast_rooms_update()
        
    elif message_type == 'join_room':
        room_id = message.get('room_id')
        
        if user_id not in game_manager.user_data:
            await game_manager.send_message(user_id, {
                'type': 'error',
                'message': '请先加入大厅'
            })
            return
        
        success = game_manager.join_room(user_id, room_id)
        
        if success:
            room_data = game_manager.get_room_data(room_id)
            room = game_manager.rooms[room_id]
            await game_manager.send_message(user_id, {
                'type': 'room_joined',
                'room_id': room_id,
                'users': room_data['users'],
                'is_owner': room['owner'] == user_id,
                'owner_username': room_data.get('owner_username', '')
            })
            
            # 单人模式不自动开始，等待用户点击开始练习
            
            # 通知房间内其他用户
            room = game_manager.rooms[room_id]
            for other_user_id in room['users']:
                if other_user_id != user_id and other_user_id in game_manager.connected_users:
                    room_data = game_manager.get_room_data(room_id)
                    await game_manager.send_message(other_user_id, {
                        'type': 'room_user_joined',
                        'users': room_data['users'],
                        'owner_username': room_data.get('owner_username', '')
                    })
            
            await game_manager.broadcast_user_update()
            await game_manager.broadcast_rooms_update()
        else:
            await game_manager.send_message(user_id, {
                'type': 'error',
                'message': '无法加入房间'
            })
        
    elif message_type == 'leave_room':
        user_data = game_manager.user_data.get(user_id, {})
        if 'room_id' in user_data:
            room_id = user_data['room_id']
            game_manager.leave_room(user_id, room_id)
            
            # 通知房间内其他用户
            if room_id in game_manager.rooms:
                room = game_manager.rooms[room_id]
                for other_user_id in room['users']:
                    if other_user_id in game_manager.connected_users:
                        await game_manager.send_message(other_user_id, {
                            'type': 'room_user_left',
                            'users': game_manager.get_room_data(room_id)['users'] if room_id in game_manager.rooms else []
                        })
            
            await game_manager.broadcast_rooms_update()
            await game_manager.broadcast_user_update()
            
            await game_manager.send_message(user_id, {
                'type': 'room_left'
            })
            
    elif message_type == 'player_progress':
        word_index = message.get('word_index', 0)
        char_index = message.get('char_index', 0)
        words_completed = message.get('words_completed', 0)
        cursor_position = message.get('cursor_position', 0)
        
        await game_manager.update_player_progress(
            user_id, word_index, char_index, words_completed, cursor_position
        )
        
    elif message_type == 'start_game':
        """房主开始游戏"""
        user_data = game_manager.user_data.get(user_id, {})
        if 'room_id' not in user_data:
            return
        
        room_id = user_data['room_id']
        if room_id not in game_manager.rooms:
            return
        
        room = game_manager.rooms[room_id]
        # 检查是否是房主
        if room['owner'] != user_id:
            await game_manager.send_message(user_id, {
                'type': 'error',
                'message': '只有房主可以开始游戏'
            })
            return
        
        # 检查游戏是否已开始
        if room['game_started']:
            return
        
        # 启动倒计时
        asyncio.create_task(game_manager.start_countdown(room_id))
    
    elif message_type == 'start_solo_practice':
        """开始单人练习模式（保留兼容性）"""
        user_data = game_manager.user_data.get(user_id, {})
        if 'room_id' not in user_data:
            return
        
        room_id = user_data['room_id']
        if room_id not in game_manager.rooms:
            return
        
        room = game_manager.rooms[room_id]
        if len(room['users']) != 1:
            return  # 不是单人模式
        
        # 启动单人游戏
        await game_manager.start_solo_game(room_id)

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

# 挂载静态文件
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=9013)
