<template>
  <div id="app">
    <div class="container">
      <!-- 左侧：在线用户列表 -->
      <div class="users-panel-left" v-if="connected && username">
        <h2 class="panel-title">在线用户</h2>
        <div class="users-list-left">
              <div 
            v-for="user in onlineUsers" 
                :key="user.id"
            class="user-item-left"
          >
            <span class="user-name-left">{{ user.username }}</span>
            <span v-if="user.room_id" class="user-status-left in-room">房间中</span>
            <span v-else class="user-status-left online">在线</span>
          </div>
        </div>
      </div>

      <!-- 右侧：用户列表和游戏区域 -->
      <div class="main-panel">
        <!-- 连接状态 -->
        <div v-if="!connected" class="connection-screen">
          <div class="loading">连接服务器中...</div>
        </div>

        <!-- 登录界面 -->
        <div v-if="connected && !username" class="login-screen">
          <div class="login-content">
            <h1 class="app-title">King of Type</h1>
            <p class="app-subtitle">与好友实时对战，提升打字速度</p>
            <div class="login-form">
              <input
                v-model="usernameInput"
                @keyup.enter="joinLobby"
                placeholder="输入用户名"
                class="username-input"
                autofocus
              />
              <button @click="joinLobby" class="btn-primary">进入大厅</button>
            </div>
          </div>
        </div>

        <!-- 大厅界面 -->
        <div v-if="connected && username && !currentRoom" class="lobby-screen">
          <div class="lobby-header">
            <h2>欢迎，{{ username }}！</h2>
            <p>选择房间开始游戏</p>
          </div>
          
          <!-- 房间列表 - 平铺卡片布局 -->
          <div class="rooms-grid">
            <div 
              v-for="room in rooms" 
              :key="room.id"
              :class="['room-card', {
                active: currentRoom === room.id,
                playing: room.game_started,
                chinese: room.type === 'chinese'
              }]"
              @click="joinRoom(room.id)"
            >
              <div class="room-card-header">
                <span class="room-card-name">
                  {{ room.id.replace('room', '房间 ') }}
                  <span v-if="room.type === 'chinese'" class="room-type-badge">中文</span>
                </span>
                <span class="room-card-status">{{ room.users.length }}人</span>
              </div>
              <div class="room-card-players" v-if="room.users.length > 0">
              <div 
                  v-for="user in room.users" 
                :key="user.id"
                  class="room-card-player"
              >
                  {{ user.username }}
              </div>
            </div>
              <div class="room-card-footer">
                <span v-if="room.game_started" class="status-badge playing">游戏中</span>
                <span v-else class="status-badge available">可加入</span>
              </div>
          </div>
          </div>
          
        </div>

        <!-- 游戏界面 -->
        <div v-if="currentRoom" class="game-screen">
          <!-- 游戏统计 -->
          <div class="game-stats">
            <div class="stat">
              <div class="stat-value">{{ wordsCompleted }}</div>
              <div class="stat-label">{{ roomType === 'chinese' ? '字数' : '单词数' }}</div>
            </div>
            <div class="stat">
              <div class="stat-value">{{ timeLeft }}</div>
              <div class="stat-label">剩余时间</div>
            </div>
          </div>

          <!-- 倒计时 -->
          <div v-if="countdown > 0" class="countdown-overlay">
            <div class="countdown-number">{{ countdown }}</div>
          </div>

          <!-- 游戏提示 -->
          <div v-if="!gameStarted && !countdown" class="game-prompt">
            <div class="prompt-content">
              <h3>等待开始游戏</h3>
              <p>房间人数: {{ roomUsers.length }}人</p>
              <p v-if="isOwner" class="owner-hint">你是房主，点击下方按钮开始游戏</p>
              <p v-else-if="ownerUsername" class="owner-hint">房主: {{ ownerUsername }}</p>
              <button v-if="isOwner" @click="startGameAsOwner" class="btn-primary">开始游戏</button>
              <p v-else class="waiting-hint">等待房主开始游戏...</p>
            </div>
          </div>

          <!-- 打字区域 -->
          <div
            v-if="gameStarted"
            class="typing-area"
            @click="focusInput"
            ref="typingArea"
          >
            <!-- 中文模式：显示完整文本 -->
            <div v-if="roomType === 'chinese'" class="words-wrapper chinese-text" ref="wordsWrapper">
              <div class="chinese-container" style="position: relative;">
                <!-- 所有玩家的光标（包括当前用户） -->
                <template v-for="(progress, userId) in allPlayersProgress" :key="userId">
                <span
                    v-if="gameStarted && progress.cursor_position !== null && progress.cursor_position !== undefined"
                    class="cursor player-cursor"
                  :style="{
                      left: progress.cursor_position + 'px',
                      top: progress.cursor_line + 'px',
                      background: getCursorColor(userId)
                  }"
                  >
                    <span 
                      class="cursor-label"
                      :class="getLabelClass(progress.cursor_line)"
                    >{{ progress.username }}</span>
                  </span>
                </template>

                <!-- 当前用户在比赛文本上的光标（显示已完成位置） -->
                <span
                  v-if="gameStarted && roomType === 'chinese' && chineseCompletedLength > 0"
                  class="cursor my-game-cursor"
                  :style="{
                    left: getGameCursorPosition() + 'px',
                    top: getGameCursorLine() + 'px'
                  }"
                >
                  <span 
                    class="cursor-label"
                    :class="getLabelClassForGameCursor()"
                  >{{ username }}</span>
                </span>

                <!-- 当前用户的输入框（显示在光标位置） -->
                <div 
                  v-if="gameStarted && myCursorPosition !== null && myCursorPosition !== undefined"
                  class="chinese-input-box"
                  :style="{
                    left: myCursorPosition + 'px',
                    top: myCursorLine + 'px'
                  }"
                >
                  <input
                    ref="chineseInputField"
                    v-model="currentInput"
                    @input="handleInput"
                    @keydown="handleKeydown"
                    @compositionstart="handleCompositionStart"
                    @compositionend="handleCompositionEnd"
                    class="chinese-input"
                    :disabled="!gameStarted"
                    autocomplete="off"
                    autocorrect="off"
                    autocapitalize="off"
                    spellcheck="false"
                  />
                </div>

                <div class="chinese-text-content">
                  <span
                    v-for="(char, charIndex) in chineseText"
                    :key="charIndex"
                    :class="['char', {
                      correct: getCharState(0, charIndex) === true,
                      incorrect: getCharState(0, charIndex) === false
                    }]"
                  >
                    {{ char }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 英文模式：显示单词列表 -->
            <div v-else class="words-wrapper" ref="wordsWrapper">
              <div class="words-lines">
                <div 
                  v-for="(item, displayIndex) in displayedWords" 
                  :key="item.wordIndex"
                  :data-word-index="item.wordIndex"
                  :class="['word', { 
                    current: item.wordIndex === currentWordIndex,
                    completed: item.wordIndex < currentWordIndex && !isSkipped(item.wordIndex),
                    skipped: isSkipped(item.wordIndex)
                  }]"
                >
                  <!-- 所有玩家的光标 -->
                  <template v-for="(progress, userId) in allPlayersProgress" :key="userId">
                  <span 
                      v-if="gameStarted && item.wordIndex === progress.word_index && progress.cursor_position !== null"
                      class="cursor player-cursor"
                      :style="{ 
                        left: progress.cursor_position + 'px',
                        background: getCursorColor(userId)
                      }"
                    >
                  <span 
                        class="cursor-label"
                        :class="getLabelClassForWord(item.wordIndex)"
                      >{{ progress.username }}</span>
                    </span>
                  </template>

                  <span
                    v-for="(char, charIndex) in item.word"
                    :key="charIndex"
                    :class="['char', {
                      correct: getCharState(item.wordIndex, charIndex) === true,
                      incorrect: getCharState(item.wordIndex, charIndex) === false,
                      next: item.wordIndex === currentWordIndex && charIndex === getCurrentWordInputLength(item.wordIndex)
                    }]"
                  >
                    {{ char }}
                  </span>
                </div>
              </div>
            </div>
          </div>


          <!-- 隐藏输入框（英文模式使用） -->
          <input
            v-if="roomType !== 'chinese'"
            ref="inputField"
            v-model="currentInput"
            @input="handleInput"
            @keydown="handleKeydown"
            class="hidden-input"
            :disabled="!gameStarted"
          />

          <!-- 游戏控制 -->
          <div class="game-controls">
            <button @click="leaveRoom" class="btn-secondary">离开房间</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      connected: false,
      username: '',
      usernameInput: '',
      ws: null,
      
      // 房间和用户
      currentRoom: null,
      rooms: [],
      onlineUsers: [],
      roomUsers: [],
      isSolo: false,
      isOwner: false,
      ownerUsername: '',
      // 所有玩家的光标位置和进度
      allPlayersProgress: {},  // {user_id: {username, word_index, char_index, words_completed, cursor_position, cursor_line}}
      // 光标颜色列表
      cursorColors: ['#4caf50', '#ff9800', '#2196f3', '#9c27b0', '#f44336', '#00bcd4', '#ffeb3b', '#ff5722'],
      
      // 游戏状态
      gameStarted: false,
      words: [],
      currentWordIndex: 0,
      currentInput: '',
      wordsCompleted: 0,
      hasError: false,
      
      // 光标位置
      myCursorPosition: 0,
      myCursorLine: 0,
      opponentWordIndex: 0,
      opponentCursorPosition: null,
      opponentCursorLine: 0,
      opponentProgress: null,
      
      // 统计
      wpm: 0,
      timeLeft: 60,
      countdown: 0,
      
      // 计时器
      gameTimer: null,
      wpmTimer: null,
      startTime: null,
      
      // 三行显示相关
      wordsPerLine: 0,
      skippedWords: new Set(), // 记录被空格跳过的单词索引
      
      // 记录每个单词的输入状态：{ wordIndex: { input: string, charStates: [true/false/null] } }
      wordInputStates: {}, // 记录每个单词的输入和每个字符的状态
      chineseText: '',  // 中文文本
      roomType: 'english',  // 房间类型：'english' 或 'chinese'
      chineseCharStates: [], // 中文模式下的字符状态数组，true=正确，false=错误，null=未输入
      chineseCompletedLength: 0,  // 中文模式下已确认完成的字符数
      isConfirmingInput: false,  // 标志：正在确认输入，防止handleInput干扰
      isComposing: false  // 标记是否正在使用输入法输入拼音
    }
  },
  
  computed: {
    displayedWords() {
      // 中文模式不需要单词显示
      if (this.roomType === 'chinese') {
        return []
      }

      // 英文模式：一次性显示所有100个单词
      return this.words.map((word, index) => ({
        word,
        wordIndex: index
      }))
    },

    totalLength() {
      // 返回总长度（中文是字符数，英文是单词数）
      if (this.roomType === 'chinese') {
        return this.chineseText.length
      }
      return this.words.length
    }
  },
  
  watch: {
    // 监听已完成字符数的变化，实时更新光标位置
    chineseCompletedLength() {
      if (this.roomType === 'chinese' && this.gameStarted) {
        this.$nextTick(() => {
          this.updateMyCursorPosition()
        })
      }
    }
  },
  
  mounted() {
    this.connectWebSocket()
    this.initRooms()
  },
  
  beforeUnmount() {
    if (this.ws) {
      this.ws.close()
    }
    this.clearTimers()
  },
  
  methods: {
    connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.hostname}:9013/ws`
      
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        this.connected = true
        console.log('WebSocket 连接成功')
      }
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.handleWebSocketMessage(data)
      }
      
      this.ws.onclose = () => {
        this.connected = false
        console.log('WebSocket 连接关闭')
        // 尝试重连
        setTimeout(() => this.connectWebSocket(), 3000)
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error)
      }
    },
    
    handleWebSocketMessage(data) {
      switch (data.type) {
        case 'users_update':
          this.onlineUsers = data.users
          break
          
        case 'rooms_update':
          this.updateRooms(data.rooms)
          break
          
        case 'room_joined':
          this.currentRoom = data.room_id
          this.roomUsers = data.users
          this.isSolo = data.users.length === 1
          this.isOwner = data.is_owner || false
          this.ownerUsername = data.owner_username || ''
          break
          
        case 'room_user_joined':
        case 'room_user_left':
          this.roomUsers = data.users
          this.isSolo = data.users.length === 1
          if (data.owner_username) {
            this.ownerUsername = data.owner_username
          }
          break
          
        case 'countdown':
          this.countdown = data.seconds
          break
          
        case 'game_started':
          this.gameStarted = true
          this.roomType = data.room_type || 'english'
          if (this.roomType === 'chinese') {
            this.chineseText = data.text || ''
            this.words = []
            this.chineseCharStates = new Array(this.chineseText.length).fill(null)
            this.chineseCompletedLength = 0
            this.isConfirmingInput = false
            this.isComposing = false
            this.currentInput = ''
          } else {
            this.words = data.words || []
            this.chineseText = ''
          }
          this.isSolo = data.solo || false
          this.countdown = 0
          // 初始化所有玩家进度
          this.allPlayersProgress = {}
          // 使用后端发送的duration，如果没有则默认60秒
          const duration = data.duration || 60
          this.startGame(duration)
          break
          
        case 'opponent_progress':
          this.updateOpponentProgress(data)
          break
          
        case 'players_progress':
          this.updateAllPlayersProgress(data.all_progress)
          break
          
        case 'game_ended':
          this.endGame(data.results)
          break
          
        case 'room_left':
          this.currentRoom = null
          this.resetGame()
          break
      }
    },
    
    initRooms() {
      for (let i = 1; i <= 10; i++) {
        this.rooms.push({
          id: `room${i}`,
          users: [],
          game_started: false,
          type: i > 5 ? 'chinese' : 'english'  // room6-room10 为中文房间
        })
      }
    },
    
    updateRooms(roomsData) {
      roomsData.forEach(roomData => {
        const room = this.rooms.find(r => r.id === roomData.id)
        if (room) {
          room.users = roomData.users || []
          room.game_started = roomData.game_started || false
          room.type = roomData.room_type || room.type // 更新房间类型
        }
      })
    },
    
    joinLobby() {
      if (!this.usernameInput.trim()) {
        alert('请输入用户名')
        return
      }
      
      this.username = this.usernameInput.trim()
      this.sendMessage({
        type: 'join_lobby',
        username: this.username
      })
    },
    
    joinRoom(roomId) {
      if (this.currentRoom || !this.username) return
      // 移除人数限制检查
      
      this.sendMessage({
        type: 'join_room',
        room_id: roomId
      })
    },
    
    leaveRoom() {
      this.sendMessage({
        type: 'leave_room'
      })
    },
    
    startSoloPractice() {
      this.sendMessage({
        type: 'start_solo_practice'
      })
    },
    
    startGameAsOwner() {
      if (!this.isOwner) return
      this.sendMessage({
        type: 'start_game'
      })
    },
    
    getCursorColor(userId) {
      // 根据用户ID生成固定颜色
      // 首先尝试从roomUsers中找到用户索引
      let userIndex = this.roomUsers.findIndex(u => u.id === userId)
      
      // 如果找不到，尝试从allPlayersProgress中获取
      if (userIndex < 0) {
        const allUserIds = Object.keys(this.allPlayersProgress)
        userIndex = allUserIds.indexOf(userId)
      }
      
      if (userIndex >= 0) {
        return this.cursorColors[userIndex % this.cursorColors.length]
      }
      return this.cursorColors[0]
    },
    
    getLabelClass(cursorLine) {
      // 如果光标在顶部（前20%），标签显示在下方
      const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
      if (!wordsWrapper) return ''
      
      const container = wordsWrapper.querySelector('.chinese-container')
      if (!container) return ''
      
      const containerHeight = container.offsetHeight
      const threshold = containerHeight * 0.2
      
      if (cursorLine < threshold) {
        return 'label-below'
      }
      return ''
    },
    
    getLabelClassForWord(wordIndex) {
      // 对于英文模式，简单判断：如果单词在前20%，标签显示在下方
      const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
      if (!wordsWrapper) return ''
      
      const wordElements = wordsWrapper.querySelectorAll('.word')
      if (wordElements.length === 0) return ''
      
      const totalWords = wordElements.length
      const threshold = totalWords * 0.2
      
      if (wordIndex < threshold) {
        return 'label-below'
      }
      return ''
    },
    
    getLabelClassForGameCursor() {
      // 根据比赛文本光标的位置决定标签显示在上方还是下方
      const cursorLine = this.getGameCursorLine()
      const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
      if (!wordsWrapper) return 'label-above'
      
      const container = wordsWrapper.querySelector('.chinese-container')
      if (!container) return 'label-above'
      
      const containerHeight = container.offsetHeight
      const threshold = containerHeight * 0.2
      
      // 如果光标在容器上半部分（前20%），标签显示在下方；否则显示在上方
      if (cursorLine < threshold) {
        return 'label-below'
      } else {
        return 'label-above'
      }
    },
    
    getGameCursorPosition() {
      // 获取当前用户在比赛文本上的光标位置（已完成位置）
      if (this.roomType !== 'chinese') return 0
      
      const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
      if (!wordsWrapper) return 0
      
      const container = wordsWrapper.querySelector('.chinese-container')
      if (!container) return 0
      
      const containerRect = container.getBoundingClientRect()
      const charElements = wordsWrapper.querySelectorAll('.char')
      
      if (charElements.length === 0 || this.chineseCompletedLength === 0) {
        return 0
      }
      
      // 光标位置在已完成字符之后
      const cursorIndex = this.chineseCompletedLength
      
      if (cursorIndex >= charElements.length) {
        // 光标在最后一个字符之后
        const lastChar = charElements[charElements.length - 1]
        if (lastChar) {
          const charRect = lastChar.getBoundingClientRect()
          return charRect.right - containerRect.left
        }
        return 0
      } else {
        // 光标在当前字符之前
        const targetChar = charElements[cursorIndex]
        if (targetChar) {
          const charRect = targetChar.getBoundingClientRect()
          return charRect.left - containerRect.left
        }
        return 0
      }
    },
    
    getGameCursorLine() {
      // 获取当前用户在比赛文本上的光标行位置
      if (this.roomType !== 'chinese') return 0
      
      const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
      if (!wordsWrapper) return 0
      
      const container = wordsWrapper.querySelector('.chinese-container')
      if (!container) return 0
      
      const containerRect = container.getBoundingClientRect()
      const charElements = wordsWrapper.querySelectorAll('.char')
      
      if (charElements.length === 0 || this.chineseCompletedLength === 0) {
        return 0
      }
      
      const cursorIndex = Math.min(this.chineseCompletedLength, charElements.length - 1)
      const targetChar = charElements[cursorIndex]
      
      if (targetChar) {
        const charRect = targetChar.getBoundingClientRect()
        return charRect.top - containerRect.top
      }
      return 0
    },
    
    updateAllPlayersProgress(allProgress) {
      // 更新所有玩家的进度
      this.allPlayersProgress = {}
      for (const [userId, progress] of Object.entries(allProgress)) {
        this.allPlayersProgress[userId] = {
          username: progress.username,
          word_index: progress.word_index,
          char_index: progress.char_index,
          words_completed: progress.words_completed,
          cursor_position: progress.cursor_position,
          cursor_line: 0  // 英文模式不需要line
        }
      }
      
      // 更新光标位置
      this.$nextTick(() => {
        this.updateAllCursorsPosition()
      })
    },
    
    updateAllCursorsPosition() {
      const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
      if (!wordsWrapper) return
      
      if (this.roomType === 'chinese') {
        // 中文模式：更新所有玩家的光标位置
        const container = wordsWrapper.querySelector('.chinese-container')
        if (!container) return
        
        const containerRect = container.getBoundingClientRect()
        const charElements = wordsWrapper.querySelectorAll('.char')
        
        for (const userId in this.allPlayersProgress) {
          const progress = this.allPlayersProgress[userId]
          const cursorIndex = progress.char_index
          
          let targetChar = null
          let useCharRight = false
          
          if (cursorIndex === 0) {
            targetChar = charElements[0]
            useCharRight = false
          } else if (cursorIndex >= charElements.length) {
            targetChar = charElements[charElements.length - 1]
            useCharRight = true
          } else {
            targetChar = charElements[cursorIndex]
            useCharRight = false
          }
          
          if (targetChar) {
            const charRect = targetChar.getBoundingClientRect()
            if (useCharRight) {
              progress.cursor_position = charRect.right - containerRect.left
            } else {
              progress.cursor_position = charRect.left - containerRect.left
            }
            progress.cursor_line = charRect.top - containerRect.top
          }
        }
      } else {
        // 英文模式：更新所有玩家的光标位置
        const wordElements = wordsWrapper.querySelectorAll('.word')
        const charWidth = 18
        
        for (const userId in this.allPlayersProgress) {
          const progress = this.allPlayersProgress[userId]
          const opponentWordEl = wordElements[progress.word_index]
          if (!opponentWordEl) {
            progress.cursor_position = null
            continue
          }
          
          const charElements = opponentWordEl.querySelectorAll('.char')
          let position = 0
          
          for (let i = 0; i < Math.min(progress.char_index, charElements.length); i++) {
            const charEl = charElements[i]
            if (charEl) {
              const rect = charEl.getBoundingClientRect()
              position += rect.width || charWidth
            }
          }
          
          progress.cursor_position = position
        }
      }
    },
    
    startGame(duration = 60) {
      this.resetGameState()
      this.startTime = Date.now()
      this.timeLeft = duration
      this.focusInput()
      
      // 启动计时器
      this.gameTimer = setInterval(() => {
        this.timeLeft--
        if (this.timeLeft <= 0) {
          this.endGame({})
        }
      }, 1000)
      
      // 启动 WPM 计算
      this.wpmTimer = setInterval(() => {
        this.updateWPM()
      }, 1000)
    },
    
    calculateWordsPerLine() {
      // 计算每行能放多少单词
      this.$nextTick(() => {
        if (!this.$refs.wordsWrapper || this.words.length === 0) {
          this.wordsPerLine = 12 // 默认值
          return
        }
        
        const wrapper = this.$refs.wordsWrapper
        const wrapperWidth = wrapper.offsetWidth - 80 // 减去padding
        const testWord = this.words[0] || 'test'
        const avgCharWidth = 18 // 估算每个字符宽度（加粗后，28px字体）
        const avgWordWidth = testWord.length * avgCharWidth + 12 // 单词宽度 + margin
        
        this.wordsPerLine = Math.floor(wrapperWidth / avgWordWidth) || 12
        
        // 确保至少显示一些单词
        if (this.wordsPerLine < 8) {
          this.wordsPerLine = 8
        }
      })
    },
    
    handleInput() {
      if (!this.gameStarted) return

      if (this.roomType === 'chinese') {
        // 中文模式：输入框和比赛文本分离的逻辑
        // 如果正在确认输入，忽略本次输入事件（防止输入法干扰）
        if (this.isConfirmingInput) {
          return
        }
        
        // 如果正在输入拼音（isComposing 为 true），只更新光标位置，不处理
        if (this.isComposing) {
          // 实时更新光标位置跟随拼音，但不提交
          this.updateMyCursorPosition()
          return
        }

        // 如果不在输入拼音（说明是直接输入或者选词完毕），且输入框里有内容
        // 注意：compositionEnd 会处理大部分情况，但为了兼容直接粘贴或非IME输入，这里也处理
        if (this.currentInput && this.currentInput.length > 0) {
          this.handleChineseInput(this.currentInput)
        } else {
          // 输入框为空，只更新光标位置
        this.updateMyCursorPosition()
        this.sendProgress()
          this.updateMyProgressInAllPlayers()
        }
      } else {
        // 英文模式：按单词输入（原有逻辑）
        const currentWord = this.words[this.currentWordIndex]
        if (!currentWord) return

        // 记录当前单词的输入状态
        if (!this.wordInputStates[this.currentWordIndex]) {
          this.wordInputStates[this.currentWordIndex] = {
            input: '',
            charStates: []
          }
        }

        // 更新输入和字符状态
        const wordState = this.wordInputStates[this.currentWordIndex]
        const previousLength = wordState.input.length
        wordState.input = this.currentInput

        // 如果输入长度减少了（按了delete键），清除被删除位置及之后的所有状态
        if (this.currentInput.length < previousLength) {
          // 清除被删除位置之后的所有状态
          wordState.charStates = wordState.charStates.slice(0, this.currentInput.length)
        }

        // 更新每个字符的状态（只更新当前输入长度的部分）
        for (let i = 0; i < this.currentInput.length; i++) {
          if (i < currentWord.length) {
            wordState.charStates[i] = this.currentInput[i] === currentWord[i]
          }
        }

        // 检查是否有错误
        this.hasError = false
        for (let i = 0; i < this.currentInput.length; i++) {
          if (this.currentInput[i] !== currentWord[i]) {
            this.hasError = true
            break
          }
        }

        // 更新光标位置
        this.updateMyCursorPosition()

        // 发送进度（会触发所有玩家进度更新）
        this.sendProgress()
        
        // 更新自己的光标位置到 allPlayersProgress
        this.updateMyProgressInAllPlayers()
      }
    },
    
    updateMyProgressInAllPlayers() {
      // 找到当前用户的ID
      const currentUser = this.roomUsers.find(u => u.username === this.username)
      if (!currentUser) return
      
      // 更新自己的进度到 allPlayersProgress（用于本地即时显示）
      // 注意：后端会通过 players_progress 消息同步所有玩家的进度
      const userId = currentUser.id
      if (!this.allPlayersProgress[userId]) {
        this.allPlayersProgress[userId] = {
          username: this.username,
          word_index: this.roomType === 'chinese' ? 0 : this.currentWordIndex,
          char_index: this.roomType === 'chinese' ? (this.chineseCompletedLength + this.currentInput.length) : this.currentInput.length,
          words_completed: this.wordsCompleted,
          cursor_position: this.myCursorPosition,
          cursor_line: this.myCursorLine
        }
      } else {
        this.allPlayersProgress[userId].word_index = this.roomType === 'chinese' ? 0 : this.currentWordIndex
        this.allPlayersProgress[userId].char_index = this.roomType === 'chinese' ? (this.chineseCompletedLength + this.currentInput.length) : this.currentInput.length
        this.allPlayersProgress[userId].words_completed = this.wordsCompleted
        this.allPlayersProgress[userId].cursor_position = this.myCursorPosition
        this.allPlayersProgress[userId].cursor_line = this.myCursorLine
      }
    },
    
    handleKeydown(event) {
      if (!this.gameStarted) return

      if (this.roomType === 'chinese') {
        // 中文模式：删除键处理 - 回退比赛文本
        // 只有在输入框为空时才触发回退比赛文本的逻辑
        if (event.key === 'Backspace') {
          // 核心修改 1: 获取原生 DOM 的值，因为 v-model 在拼音输入时可能还是空的
          const rawValue = event.target.value
          
          // 核心修改 2: 增加 this.isComposing 判断
          // 如果正在输入拼音 (isComposing) 或者 输入框里原本就有文字 (rawValue.length > 0)
          // 此时按删除键应该只删除输入框里的东西，不应该回退比赛文本
          if (this.isComposing || rawValue.length > 0) {
            return  // 不阻止默认行为，让浏览器正常删除输入框里的拼音或文字
          }
          
          // --- 以下逻辑保持不变，只有当确实没在打字且输入框全空时，才回退比赛进度 ---
          
          // 输入框为空时，阻止默认行为并回退比赛文本
          event.preventDefault()
          
          // 删除键只对比赛文本有效
          // 如果已完成字符数 > 0，则回退比赛文本
          if (this.chineseCompletedLength > 0) {
            // 光标左移：减少已完成字符数
            this.chineseCompletedLength--
            
            // 重置被删除字符的状态（取消正确或错误标记）
            const deletedCharIndex = this.chineseCompletedLength
            if (deletedCharIndex < this.chineseCharStates.length) {
              this.chineseCharStates[deletedCharIndex] = null
            }
            
            // 更新已完成字符数（用于统计）
            this.wordsCompleted = this.chineseCompletedLength
            
            // 更新光标位置
            this.$nextTick(() => {
              this.updateMyCursorPosition()
              this.sendProgress()
              this.updateMyProgressInAllPlayers()
            })
          }
          return
        }
        
        // 中文模式下，不再需要空格或回车来确认了，因为选词就会自动确认
        // 但是，为了防止用户习惯性按空格导致页面滚动或产生不必要的字符，可以阻止默认行为
        if (event.key === ' ' || event.key === 'Enter') {
          // 如果不是在打拼音的过程中，阻止空格
          if (!this.isComposing) {
            event.preventDefault()
            // 如果输入框有内容，也可以手动触发处理（兼容非IME输入）
            if (this.currentInput && this.currentInput.length > 0) {
              this.handleChineseInput(this.currentInput)
            }
          }
        }
        return
      }

      // 英文模式：原有逻辑
      // 删除键处理：如果当前输入为空，回到上一个单词
      if (event.key === 'Backspace' && this.currentInput.length === 0 && this.currentWordIndex > 0) {
        event.preventDefault()
        this.goToPreviousWord()
        return
      }

      // 空格键处理
      if (event.key === ' ') {
        event.preventDefault()

        const currentWord = this.words[this.currentWordIndex]
        if (this.currentInput.trim() === currentWord) {
          // 正确完成单词
          this.completeWord()
        } else {
          // 跳过当前单词（即使打错了），但保留输入状态
          this.skipWord()
        }
      }
    },
    
    // 添加中文输入法处理方法
    handleCompositionStart() {
      this.isComposing = true
    },
    
    handleCompositionEnd(event) {
      this.isComposing = false
      // compositionEnd 结束后，通常会紧接着触发 input 事件
      // 但为了保险起见，我们在这里也手动触发一次处理逻辑
      this.$nextTick(() => {
        if (this.currentInput && this.currentInput.length > 0) {
          this.handleChineseInput(this.currentInput)
        }
      })
    },
    
    // 专门抽离一个处理中文输入的逻辑
    handleChineseInput(text) {
      if (!text || text.length === 0) return // 如果没有文字则不处理
      
      // 设置确认标志，防止handleInput干扰
      this.isConfirmingInput = true
      
      const inputToConfirm = text
      
      // 确认当前输入框的内容
      const startIndex = this.chineseCompletedLength
      const inputLength = inputToConfirm.length
      // 防止超出文本长度
      const remainingLength = this.chineseText.length - startIndex
      const processLength = Math.min(inputLength, remainingLength)
      
      // 1. 标记对错状态
      for (let i = 0; i < processLength; i++) {
        const charIndex = startIndex + i
        if (charIndex < this.chineseText.length) {
          const isCorrect = inputToConfirm[i] === this.chineseText[charIndex]
          this.chineseCharStates[charIndex] = isCorrect
        }
      }
      
      // 2. 更新进度
      this.chineseCompletedLength = Math.min(
        this.chineseCompletedLength + processLength,
        this.chineseText.length
      )
      this.wordsCompleted = this.chineseCompletedLength
      
      // 3. 核心：处理完立刻清空输入框
      this.currentInput = ''
      
      // 强制清空 DOM，防止输入法残留
      this.$nextTick(() => {
        if (this.$refs.chineseInputField) {
          this.$refs.chineseInputField.value = ''
          // 确保输入框被清空
          this.currentInput = ''
        }
        // 清除确认标志
        this.isConfirmingInput = false
        this.updateMyCursorPosition()
        this.sendProgress()
        this.updateMyProgressInAllPlayers()
      })
    },
    
    completeWord() {
      // 保存当前单词的完整输入状态
      if (this.wordInputStates[this.currentWordIndex]) {
        this.wordInputStates[this.currentWordIndex].input = this.currentInput
      }
      
      this.wordsCompleted++
      this.currentWordIndex++
      this.currentInput = ''
      this.hasError = false
      
      // 立即更新光标位置，避免跳转
      this.$nextTick(() => {
      this.updateMyCursorPosition()
      this.sendProgress()
        this.updateMyProgressInAllPlayers()
      })
    },
    
    skipWord() {
      // 按空格跳过当前单词，记录跳过的单词，但保留输入状态
      this.skippedWords.add(this.currentWordIndex)
      
      // 确保保存当前输入状态和字符状态（即使跳过了也要保留）
      if (!this.wordInputStates[this.currentWordIndex]) {
        this.wordInputStates[this.currentWordIndex] = {
          input: '',
          charStates: []
        }
      }
      
      const wordState = this.wordInputStates[this.currentWordIndex]
      wordState.input = this.currentInput
      
      // 更新字符状态
      const currentWord = this.words[this.currentWordIndex]
      for (let i = 0; i < this.currentInput.length; i++) {
        if (i < currentWord.length) {
          wordState.charStates[i] = this.currentInput[i] === currentWord[i]
        }
      }
      
      this.currentWordIndex++
      this.currentInput = ''
      this.hasError = false
      
      // 立即更新光标位置，避免跳转
      this.$nextTick(() => {
      this.updateMyCursorPosition()
      this.sendProgress()
        this.updateMyProgressInAllPlayers()
      })
    },
    
    goToPreviousWord() {
      // 回到上一个单词
      if (this.currentWordIndex > 0) {
        this.currentWordIndex--
        
        // 恢复上一个单词的输入状态
        const prevWordState = this.wordInputStates[this.currentWordIndex]
        if (prevWordState) {
          this.currentInput = prevWordState.input
        } else {
          this.currentInput = ''
        }
        
        // 如果上一个单词是被跳过的，从跳过列表中移除
        this.skippedWords.delete(this.currentWordIndex)
        
        this.updateMyCursorPosition()
        this.sendProgress()
        this.updateMyProgressInAllPlayers()
      }
    },
    
    updateMyCursorPosition() {
      // 使用双重 nextTick 确保 DOM 更新完成
      this.$nextTick(() => {
        this.$nextTick(() => {
          const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
          if (!wordsWrapper) {
            this.myCursorPosition = 0
            return
          }

          if (this.roomType === 'chinese') {
            // 中文模式：基于实际DOM元素位置计算光标位置
            const container = wordsWrapper.querySelector('.chinese-container')
            if (!container) {
              this.myCursorPosition = 0
              this.myCursorLine = 0
              return
            }

            const containerRect = container.getBoundingClientRect()
            const charElements = wordsWrapper.querySelectorAll('.char')
            
            if (charElements.length === 0) {
              // 如果没有字符，光标在开头
              this.myCursorPosition = 0
              this.myCursorLine = 0
              return
            }

            // 获取当前输入位置对应的字符元素
            // 光标位置 = 已完成字符数 + 输入框中的字符数
            const cursorIndex = this.chineseCompletedLength + this.currentInput.length
            
            let targetChar = null
            let useCharRight = false

            if (cursorIndex === 0) {
              // 光标在开头，使用第一个字符
              targetChar = charElements[0]
              useCharRight = false
            } else if (cursorIndex >= charElements.length) {
              // 光标在最后一个字符之后
              targetChar = charElements[charElements.length - 1]
              useCharRight = true
            } else {
              // 光标在当前输入位置的字符之前
              targetChar = charElements[cursorIndex]
              useCharRight = false
            }

            if (targetChar) {
              const charRect = targetChar.getBoundingClientRect()
              
              // 计算光标水平位置
              if (useCharRight) {
                this.myCursorPosition = charRect.right - containerRect.left
              } else {
                this.myCursorPosition = charRect.left - containerRect.left
              }

              // 计算光标垂直位置（相对于容器的top）
              this.myCursorLine = charRect.top - containerRect.top
            } else {
              this.myCursorPosition = 0
              this.myCursorLine = 0
            }
          } else {
            // 英文模式：原有逻辑
            const currentWordEl = wordsWrapper.querySelector(`.word[data-word-index="${this.currentWordIndex}"]`)

            if (!currentWordEl) {
              // 如果当前单词不在显示的三行中，光标位置设为0
              this.myCursorPosition = 0
              return
            }

            const charElements = currentWordEl.querySelectorAll('.char')
            let position = 0
            const charWidth = 18 // 估算字符宽度（加粗后）

            for (let i = 0; i < Math.min(this.currentInput.length, charElements.length); i++) {
              const charEl = charElements[i]
              if (charEl) {
                const rect = charEl.getBoundingClientRect()
                position += rect.width || charWidth
              }
            }

            this.myCursorPosition = position
          }
        })
      })
    },
    
    updateOpponentProgress(data) {
      // 保留兼容性，但主要使用 players_progress
      // 这个方法可能不再被调用，但保留以防万一
    },
    
    sendProgress() {
      if (!this.currentRoom || !this.gameStarted) return

      if (this.roomType === 'chinese') {
        // 中文模式：发送字符索引和完成字数
        this.sendMessage({
          type: 'player_progress',
          word_index: 0,  // 中文模式统一为0
          char_index: this.chineseCompletedLength + this.currentInput.length,
          words_completed: this.chineseCompletedLength,  // 已确认完成的字符数
          cursor_position: this.myCursorPosition
        })
      } else {
        // 英文模式：原有逻辑
        const charIndex = this.currentInput.length

        this.sendMessage({
          type: 'player_progress',
          word_index: this.currentWordIndex,
          char_index: charIndex,
          words_completed: this.wordsCompleted,
          cursor_position: this.myCursorPosition
        })
      }
    },
    
    updateWPM() {
      if (!this.startTime) return
      
      const elapsedMinutes = (Date.now() - this.startTime) / 1000 / 60
      if (elapsedMinutes === 0) return
      
      let correctChars = 0
      
      if (this.roomType === 'chinese') {
        // 中文模式：只计算正确的字符数
        for (let i = 0; i < this.chineseCompletedLength && i < this.chineseCharStates.length; i++) {
          if (this.chineseCharStates[i] === true) {
            correctChars++
          }
        }
      } else {
        // 英文模式：只计算正确的字符数
        for (let i = 0; i < this.currentWordIndex; i++) {
          const wordState = this.wordInputStates[i]
          if (wordState && wordState.charStates) {
            // 统计这个单词中正确的字符数
            for (let j = 0; j < wordState.charStates.length; j++) {
              if (wordState.charStates[j] === true) {
                correctChars++
              }
            }
          }
        }
      }
      
      // WPM = (正确字符数 / 5) / 分钟数
      this.wpm = Math.round(correctChars / 5 / elapsedMinutes) || 0
    },
    
    endGame(results) {
      this.gameStarted = false
      this.clearTimers()
      
      let message = `游戏结束！\n\n你的成绩：${this.wordsCompleted} 个单词，${this.wpm} WPM\n\n`
      
      if (!this.isSolo && results && Object.keys(results).length > 1) {
        message += '排名：\n'
        const resultEntries = Object.entries(results)
        resultEntries
          .sort((a, b) => b[1].words_completed - a[1].words_completed)
          .forEach(([userId, data], index) => {
            // 检查是否是当前用户（通过用户名匹配）
            const isMe = data.username === this.username
            message += `${index + 1}. ${data.username}: ${data.words_completed} 单词${isMe ? ' (你)' : ''}\n`
          })
      }
      
      setTimeout(() => {
        alert(message)
      }, 100)
    },
    
    resetGame() {
      this.gameStarted = false
      this.words = []
      this.chineseText = ''
      this.roomType = 'english'
      this.currentWordIndex = 0
      this.currentInput = ''
      this.wordsCompleted = 0
      this.hasError = false
      this.wpm = 0
      this.timeLeft = 60
      this.countdown = 0
      this.opponentProgress = null
      this.opponentWordIndex = 0
      this.opponentCursorPosition = null
      this.opponentCursorLine = 0
      this.myCursorPosition = 0
      this.myCursorLine = 0
      this.startTime = null
      this.wordsPerLine = 0
      this.skippedWords.clear()
      this.wordInputStates = {}
      this.chineseCharStates = []
      this.chineseCompletedLength = 0
      this.isConfirmingInput = false
      this.isComposing = false
      this.allPlayersProgress = {}
      this.isOwner = false
      this.ownerUsername = ''
      this.clearTimers()
    },
    
    resetGameState() {
      this.currentWordIndex = 0
      this.currentInput = ''
      this.wordsCompleted = 0
      this.hasError = false
      this.wpm = 0
      this.timeLeft = 60
      this.opponentProgress = null
      this.opponentWordIndex = 0
      this.opponentCursorPosition = null
      this.opponentCursorLine = 0
      this.myCursorPosition = 0
      this.myCursorLine = 0
      this.skippedWords.clear()
      this.wordInputStates = {}
      this.chineseCharStates = []
      this.chineseCompletedLength = 0
      this.isConfirmingInput = false
      this.isComposing = false
      this.allPlayersProgress = {}
    },
    
    clearTimers() {
      if (this.gameTimer) {
        clearInterval(this.gameTimer)
        this.gameTimer = null
      }
      if (this.wpmTimer) {
        clearInterval(this.wpmTimer)
        this.wpmTimer = null
      }
    },
    
    focusInput() {
      this.$nextTick(() => {
        // 中文模式使用中文输入框
        if (this.roomType === 'chinese' && this.$refs.chineseInputField) {
          this.$refs.chineseInputField.focus()
        } else if (this.$refs.inputField) {
          this.$refs.inputField.focus()
        }
      })
    },
    
    sendMessage(message) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(message))
      }
    },
    
    isSkipped(wordIndex) {
      return this.skippedWords.has(wordIndex)
    },
    
    getCharState(wordIndex, charIndex) {
      // 中文模式
      if (this.roomType === 'chinese') {
        // 如果字符已经确认完成，从chineseCharStates中获取状态
        if (charIndex < this.chineseCompletedLength) {
          return this.chineseCharStates[charIndex]
        }
        // 如果字符在输入框中，实时判断是否正确（但还未确认）
        const inputIndex = charIndex - this.chineseCompletedLength
        if (inputIndex >= 0 && inputIndex < this.currentInput.length) {
          // 实时显示输入状态，但不确认（只有按空格/回车才确认）
          return this.currentInput[inputIndex] === this.chineseText[charIndex] ? true : false
        }
        return null
      }

      // 英文模式：原有逻辑
      // 获取字符的状态：true=正确, false=错误, null=未输入
      const wordState = this.wordInputStates[wordIndex]
      if (!wordState || charIndex >= wordState.charStates.length) {
        // 如果是当前单词且正在输入
        if (wordIndex === this.currentWordIndex && charIndex < this.currentInput.length) {
          const currentWord = this.words[wordIndex]
          return this.currentInput[charIndex] === currentWord[charIndex]
        }
        return null
      }
      return wordState.charStates[charIndex] !== undefined ? wordState.charStates[charIndex] : null
    },
    
    getCurrentWordInputLength(wordIndex) {
      // 获取当前单词的输入长度（用于显示next状态）
      if (wordIndex === this.currentWordIndex) {
        return this.currentInput.length
      }
      const wordState = this.wordInputStates[wordIndex]
      return wordState ? wordState.input.length : 0
    }
  }
}
</script>

<style scoped>
* {
  box-sizing: border-box;
}

#app {
  min-height: 100vh;
  background: #000000;
  color: #e5e5e5;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.container {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 10px;
  max-width: 100vw;
  margin: 0;
  padding: 0;
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

/* 当没有用户名时，使用单列布局，让登录界面居中 */
.container:not(:has(.users-panel-left)) {
  grid-template-columns: 1fr;
  justify-items: center;
}

/* 左侧房间面板 */
/* 左侧在线用户面板 */
.users-panel-left {
  background: #2a2a2a;
  border-radius: 10px;
  padding: 12px;
  height: fit-content;
  position: sticky;
  top: 10px;
  width: 100%;
  max-width: 250px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #fff;
}

.users-list-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-item-left {
  background: #333;
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background 0.2s;
}

.user-item-left:hover {
  background: #3a3a3a;
}

.user-name-left {
  font-weight: 500;
  color: #fff;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

.user-status-left {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 500;
  flex-shrink: 0;
}

.user-status-left.online {
  background: #4caf50;
  color: #fff;
}

.user-status-left.in-room {
  background: #ff9800;
  color: #fff;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge.available {
  background: #4caf50;
  color: #fff;
}

.status-badge.full {
  background: #f44336;
  color: #fff;
}

.status-badge.active {
  background: #2196f3;
  color: #fff;
}

.status-badge.playing {
  background: #ff9800;
  color: #fff;
}

/* 主面板 */
.main-panel {
  background: #000000;
  border-radius: 0;
  padding: 10px;
  min-height: 700px;
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* 连接/登录界面 */
.connection-screen,
.login-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  width: 100%;
  flex: 1;
}

.login-content {
  text-align: center;
}

.app-title {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #4caf50, #2196f3);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-subtitle {
  font-size: 18px;
  color: #aaa;
  margin-bottom: 32px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 300px;
  margin: 0 auto;
}

.username-input {
  padding: 14px 18px;
  font-size: 16px;
  background: #333;
  border: 2px solid #444;
  border-radius: 8px;
  color: #fff;
  outline: none;
  transition: border-color 0.2s;
}

.username-input:focus {
  border-color: #4caf50;
}

/* 按钮 */
.btn-primary,
.btn-secondary {
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #4caf50;
  color: #fff;
}

.btn-primary:hover {
  background: #45a049;
  transform: translateY(-2px);
}

.btn-secondary {
  background: #444;
  color: #fff;
}

.btn-secondary:hover {
  background: #555;
}

/* 大厅界面 */
.lobby-screen {
  position: relative;
  min-height: 100vh;
}

.lobby-header {
  text-align: center;
  margin-bottom: 40px;
}

.lobby-header h2 {
  font-size: 32px;
  margin-bottom: 8px;
}

/* 房间列表 - 平铺卡片布局 */
.rooms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.room-card {
  background: #333;
  border: 2px solid transparent;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  min-height: 150px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.room-card:hover {
  background: #3a3a3a;
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.room-card.active {
  border-color: #4caf50;
  background: #2d4a2f;
}

.room-card.playing {
  border-color: #ff9800;
}

.room-card.chinese {
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
}

.room-card.chinese:hover {
  background: linear-gradient(135deg, #45a049 0%, #5cb85c 100%);
}

.room-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.room-card-name {
  font-weight: 600;
  color: #fff;
  font-size: 18px;
}

.room-card-status {
  background: #444;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: #fff;
}

.room-card-players {
  margin: 12px 0;
  font-size: 14px;
  flex-grow: 1;
}

.room-card-player {
  color: #aaa;
  margin-bottom: 6px;
}

.room-card-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #444;
}

/* 在线用户列表 - 小竖列 */
.users-panel-vertical {
  position: fixed;
  right: 20px;
  top: 20px;
  background: #2a2a2a;
  border-radius: 10px;
  padding: 15px;
  width: 200px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  z-index: 100;
}

.users-panel-vertical h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: #fff;
  text-align: center;
}

.users-list-vertical {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.user-item-vertical {
  background: #333;
  padding: 8px 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name-vertical {
  font-weight: 500;
  font-size: 13px;
  color: #fff;
}

.user-status-vertical {
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 500;
  align-self: flex-start;
}

.user-status-vertical.online {
  background: #4caf50;
  color: #fff;
}

.user-status-vertical.in-room {
  background: #ff9800;
  color: #fff;
}

/* 游戏界面 */
.game-screen {
  max-width: 100%;
  margin: 0;
  padding: 0;
  width: 100%;
}

.game-stats {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 30px;
}

.stat {
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #4caf50;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #aaa;
}

/* 倒计时 */
.countdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.countdown-number {
  font-size: 120px;
  font-weight: 700;
  color: #4caf50;
  animation: pulse 1s ease-in-out;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

/* 游戏提示 */
.game-prompt {
  text-align: center;
  padding: 60px 20px;
}

.prompt-content h3 {
  font-size: 28px;
  margin-bottom: 12px;
}

.prompt-content p {
  color: #aaa;
  margin-bottom: 24px;
}

/* 打字区域 */
.typing-area {
  background: #000000;
  border-radius: 0;
  padding: 20px;
  min-height: 600px;
  margin: 0;
  cursor: text;
  position: relative;
  width: 100%;
}

.words-wrapper {
  font-size: 28px;
  line-height: 1.8;
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  color: #666;
  overflow-y: auto;
  max-height: 600px;
  position: relative;
  min-height: 500px;
}

.words-lines {
  display: block;
  line-height: 1.8;
  transition: transform 0.2s ease-out;
  white-space: normal;
  word-wrap: break-word;
}

.word {
  position: relative;
  display: inline-block;
  margin-right: 12px;
  margin-bottom: 8px;
  padding: 4px 0;
  white-space: nowrap;
}

.word.current {
  /* 移除背景 */
}

.word.skipped {
  /* 跳过的单词保持默认颜色，不显示背景 */
}

.char {
  display: inline-block;
  transition: color 0.1s;
  font-weight: bold;
}

.char.correct {
  color: #4caf50;
}

.char.incorrect {
  color: #f44336;
  background: rgba(244, 67, 54, 0.2);
  text-decoration: underline;
}

.char.next {
  /* 移除所有样式，不显示任何提示 */
}

/* 光标 */
.cursor {
  position: absolute;
  top: 0;
  width: 6px;
  height: 42px;
  pointer-events: none;
  transition: left 0.1s ease-out, top 0.1s ease-out;
  border-radius: 2px;
  opacity: 1;
  z-index: 10;
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.5);
  /* 移除闪烁动画，保持常亮 */
  animation: none;
}

.player-cursor {
  position: absolute;
  z-index: 10;
  animation: none;
}

.my-game-cursor {
  position: absolute;
  z-index: 12;
  background: #4caf50;
  opacity: 1;
  animation: none;
}

.cursor-label {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.9);
  color: #fff;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
  pointer-events: none;
  font-weight: 500;
  z-index: 20;
  /* 确保标签在打字区域内可见 */
  /* 如果光标在顶部，标签显示在下方；如果在底部，标签显示在上方 */
}

/* 中文模式下的标签位置调整 */
.chinese-container .cursor-label {
  /* 默认显示在光标上方 */
  bottom: 100%;
  margin-bottom: 4px;
  /* 如果光标太靠上，标签会显示在下方 */
}

.chinese-container .cursor-label.label-below {
  bottom: auto;
  top: 100%;
  margin-top: 4px;
  margin-bottom: 0;
}

/* 英文模式下的标签位置调整 */
.words-wrapper .cursor-label {
  /* 默认显示在光标上方 */
  bottom: 100%;
  margin-bottom: 4px;
}

.words-wrapper .cursor-label.label-below {
  bottom: auto;
  top: 100%;
  margin-top: 4px;
  margin-bottom: 0;
}

/* 中文文本样式 */
.chinese-text {
  font-family: 'Microsoft YaHei', 'SimHei', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  line-height: 2;
  font-size: 24px;
}

.chinese-container {
  position: relative;
  padding: 20px;
  background: #000000;
  border-radius: 0;
  min-height: 500px;
}

.chinese-text-content {
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 2;
  min-height: 450px;
}

/* 中文模式输入框 */
.chinese-input-box {
  position: absolute;
  z-index: 15;
  pointer-events: none;
}

.chinese-input {
  background: transparent !important;
  border: none !important;
  border-radius: 0;
  padding: 0;
  font-size: 16px;
  font-family: 'Microsoft YaHei', 'SimHei', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  color: #4caf50 !important;
  outline: none !important;
  min-width: 1px;
  width: auto;
  pointer-events: auto;
  box-shadow: none !important;
  transition: none;
  line-height: 1.8;
  caret-color: #4caf50;
}

.chinese-input:focus {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}

.chinese-input:disabled {
  opacity: 0.5;
  cursor: text;
}

/* 所有玩家进度 */
.players-progress {
  background: #333;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.player-progress-item {
  margin-bottom: 16px;
}

.player-progress-item:last-child {
  margin-bottom: 0;
}

.player-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.player-name {
  font-weight: 600;
  font-size: 14px;
}

.player-words {
  color: #aaa;
  font-size: 12px;
}

.progress-bar {
  height: 6px;
  background: #444;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s;
}

/* 游戏提示 */
.owner-hint {
  color: #4caf50;
  font-weight: 500;
  margin: 8px 0;
}

.waiting-hint {
  color: #aaa;
  margin: 8px 0;
}

/* 游戏控制 */
.game-controls {
  text-align: center;
}

.hidden-input {
  position: absolute;
  left: -9999px;
  opacity: 0;
  pointer-events: none;
}

.loading {
  font-size: 20px;
  color: #aaa;
}
</style>
