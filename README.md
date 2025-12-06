# Monkeytype 多人对战

一个类似 Monkeytype 的多人在线打字竞速游戏，基于 Vue.js 和 FastAPI 构建，支持实时对战和单人练习模式。

## 功能特性

- 🎮 **多人在线对战**：支持2人实时打字对战
- 🏃‍♂️ **单人练习模式**：单人进入房间可随时开始练习
- 🏠 **10个固定房间**：左侧显示10个固定房间，方便快速加入
- 👥 **在线用户列表**：右侧显示大厅在线用户列表
- ⏱️ **自动开始**：两人进入房间5秒倒计时后自动开始游戏
- 👀 **双人光标显示**：同时显示自己和对手的光标位置
- 💡 **实时打字提示**：每打一个字都有颜色提示（绿色正确，红色错误）
- ⌨️ **空格跳转**：按空格键可直接跳转到下一个单词
- ⏰ **30秒计时**：游戏时长固定30秒
- 📊 **单词计数**：统计完成的单词数量，看谁打的单词多

## 技术栈

### 前端
- Vue.js 3 - 现代化前端框架
- Vite - 快速构建工具
- WebSocket - 实时通信
- CSS Grid/Flexbox - 响应式布局

### 后端
- FastAPI - 高性能Python Web框架
- WebSocket - 实时双向通信
- asyncio - 异步编程
- UUID - 唯一标识符生成

## 项目结构

```
kot/
├── frontend/                 # 前端项目
│   ├── src/
│   │   ├── App.vue          # 主应用组件
│   │   └── main.js          # 入口文件
│   ├── index.html           # HTML模板
│   ├── package.json         # 依赖配置
│   └── vite.config.js       # Vite配置
├── backend/                  # 后端项目
│   ├── main.py              # 主服务器文件
│   └── requirements.txt     # Python依赖
├── start.sh                 # 启动脚本
└── README.md               # 说明文档
```

## 快速开始

### 方法一：使用启动脚本（推荐）

1. 进入项目目录：
```bash
cd kot
```

2. 给启动脚本执行权限：
```bash
chmod +x start.sh
```

3. 启动应用：
```bash
./start.sh
```

### 方法二：手动启动

#### 启动后端服务器

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境并安装依赖：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. 启动服务器：
```bash
python main.py
```

后端服务器将在 http://localhost:9013 启动

#### 启动前端开发服务器

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端开发服务器将在 http://localhost:3000 启动（或通过后端访问 http://localhost:9013）

## 使用说明

1. **连接服务器**：打开浏览器访问 http://localhost:9013（后端端口）
2. **设置用户名**：输入用户名后点击"进入大厅"
3. **查看界面布局**：
   - 左侧：10个固定房间列表，显示房间状态和当前玩家
   - 右侧：在线用户列表和游戏区域
4. **加入房间**：
   - 点击左侧任意房间加入
   - 单人模式：进入后点击"开始练习"按钮
   - 双人模式：等待另一人加入，5秒倒计时后自动开始
5. **游戏进行**：
   - 打字区域显示所有单词
   - 绿色字符表示正确，红色字符表示错误
   - 按空格键可直接跳转到下一个单词
   - 同时显示自己和对手的光标位置
   - 顶部显示单词数、WPM和剩余时间
6. **游戏结束**：30秒后自动结束，显示排名和成绩

## WebSocket通信协议

### 客户端发送消息

- `join_lobby` - 加入大厅（需要username）
- `join_room` - 加入房间（需要room_id）
- `leave_room` - 离开房间
- `start_solo_practice` - 开始单人练习
- `player_progress` - 发送游戏进度（word_index, char_index, words_completed, cursor_position）

### 服务器发送消息

- `users_update` - 在线用户列表更新
- `rooms_update` - 房间列表更新
- `room_joined` - 加入房间成功（包含users和is_solo）
- `room_user_joined` / `room_user_left` - 房间用户变化
- `countdown` - 倒计时（seconds）
- `game_started` - 游戏开始（包含words, duration, solo）
- `opponent_progress` - 对手进度更新
- `game_ended` - 游戏结束（包含results排名）

## 开发说明

### 前端开发

前端使用Vue 3 Composition API，主要功能包括：

- 实时WebSocket连接管理
- 打字区域渲染和状态管理
- 游戏统计计算（WPM、准确率）
- 对手进度显示
- 响应式UI组件

### 后端开发

后端使用FastAPI的WebSocket支持，主要功能包括：

- 用户连接管理和状态跟踪
- 房间创建和加入逻辑
- 游戏开始和进度同步
- 实时消息广播
- 单词生成算法

## 自定义配置

### 修改游戏参数

在 `backend/main.py` 中可以修改：

- 游戏时间：修改 `game_duration` 变量（默认30秒）
- 单词数量：修改 `generate_words()` 方法中的单词列表和数量
- 房间人数限制：修改 `join_room()` 方法中的 `>= 2` 条件
- 倒计时时间：修改 `start_countdown()` 方法中的 `range(5, 0, -1)`

### 修改UI样式

在 `frontend/src/App.vue` 的 `<style>` 部分可以自定义：

- 颜色主题
- 字体大小
- 布局样式
- 动画效果

## 故障排除

### 常见问题

1. **端口被占用**：修改 `vite.config.js` 或 `main.py` 中的端口号
2. **依赖安装失败**：检查Python和Node.js版本
3. **WebSocket连接失败**：检查防火墙设置和代理配置

### 日志查看

- 后端日志：直接在终端查看输出
- 前端日志：打开浏览器开发者工具查看Console

## 许可证

MIT License