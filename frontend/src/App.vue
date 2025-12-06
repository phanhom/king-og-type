<template>
  <div id="app">
    <div class="container">
      <!-- 左侧：10个固定房间 -->
      <div class="rooms-panel" v-if="connected && username">
        <h2 class="panel-title">房间列表</h2>
        <div class="rooms-list">
          <div 
            v-for="room in rooms" 
            :key="room.id"
            :class="['room-item', {
              active: currentRoom === room.id,
              full: room.users.length >= 2,
              playing: room.game_started,
              chinese: room.type === 'chinese'
            }]"
            @click="joinRoom(room.id)"
          >
              <div class="room-header">
                <span class="room-name">
                  {{ room.id.replace('room', '房间 ') }}
                  <span v-if="room.type === 'chinese'" class="room-type-badge">中文</span>
                </span>
                <span class="room-status">{{ room.users.length }}/2</span>
              </div>
            <div class="room-players" v-if="room.users.length > 0">
              <div 
                v-for="user in room.users" 
                :key="user.id"
                class="player-name"
              >
                {{ user.username }}
              </div>
            </div>
            <div class="room-footer">
              <span v-if="room.game_started" class="status-badge playing">游戏中</span>
              <span v-else-if="room.users.length >= 2" class="status-badge full">已满</span>
              <span v-else-if="currentRoom === room.id" class="status-badge active">当前房间</span>
              <span v-else class="status-badge available">可加入</span>
            </div>
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
            <p>选择左侧房间开始游戏</p>
          </div>
          
          <!-- 在线用户列表 -->
          <div class="users-panel">
            <h3>在线用户 ({{ onlineUsers.length }})</h3>
            <div class="users-list">
              <div 
                v-for="user in onlineUsers" 
                :key="user.id"
                class="user-item"
              >
                <span class="user-name">{{ user.username }}</span>
                <span v-if="user.room_id" class="user-status in-room">房间中</span>
                <span v-else class="user-status online">在线</span>
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
              <div class="stat-value">{{ wpm }}</div>
              <div class="stat-label">WPM</div>
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
              <h3 v-if="isSolo">练习模式</h3>
              <h3 v-else>等待对手...</h3>
              <p v-if="isSolo">随时可以开始打字</p>
              <p v-else>房间人数: {{ roomUsers.length }}/2，5秒后自动开始</p>
              <button v-if="isSolo" @click="startSoloPractice" class="btn-primary">开始练习</button>
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
                <!-- 我的光标 -->
                <span
                  v-if="gameStarted"
                  class="cursor my-cursor"
                  :style="{
                    left: myCursorPosition + 'px',
                    top: myCursorLine + 'px'
                  }"
                ></span>

                <!-- 对手光标 -->
                <span
                  v-if="opponentCursorPosition !== null && !isSolo"
                  class="cursor opponent-cursor"
                  :style="{
                    left: opponentCursorPosition + 'px',
                    top: opponentCursorLine + 'px'
                  }"
                ></span>

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
                  <!-- 我的光标 -->
                  <span 
                    v-if="item.wordIndex === currentWordIndex && gameStarted"
                    class="cursor my-cursor"
                    :style="{ left: myCursorPosition + 'px' }"
                  ></span>
                  
                  <!-- 对手光标 -->
                  <span 
                    v-if="item.wordIndex === opponentWordIndex && opponentCursorPosition !== null && !isSolo"
                    class="cursor opponent-cursor"
                    :style="{ left: opponentCursorPosition + 'px' }"
                  ></span>

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

          <!-- 对手进度 -->
          <div v-if="!isSolo && opponentProgress" class="opponent-progress">
            <div class="opponent-info">
              <span class="opponent-name">{{ opponentProgress.username }}</span>
              <span class="opponent-words">{{ opponentProgress.words_completed }} {{ roomType === 'chinese' ? '字' : '单词' }}</span>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: (opponentProgress.words_completed / totalLength) * 100 + '%' }"
              ></div>
            </div>
          </div>

          <!-- 隐藏输入框 -->
          <input
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
      chineseCharStates: [] // 中文模式下的字符状态数组
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
          this.isSolo = data.is_solo
          break
          
        case 'room_user_joined':
        case 'room_user_left':
          this.roomUsers = data.users
          this.isSolo = data.users.length === 1
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
          } else {
            this.words = data.words || []
            this.chineseText = ''
          }
          this.isSolo = data.solo || false
          this.countdown = 0
          // 使用后端发送的duration，如果没有则默认60秒
          const duration = data.duration || 60
          this.startGame(duration)
          break
          
        case 'opponent_progress':
          this.updateOpponentProgress(data)
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
      if (this.rooms.find(r => r.id === roomId)?.users.length >= 2) return
      
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
        // 中文模式：按字符输入
        const previousLength = this.currentInput.length

        // 更新字符状态
        for (let i = 0; i < this.currentInput.length && i < this.chineseText.length; i++) {
          this.chineseCharStates[i] = this.currentInput[i] === this.chineseText[i]
        }

        // 如果输入长度减少，清除之后的状态
        if (this.currentInput.length < previousLength) {
          this.chineseCharStates = this.chineseCharStates.slice(0, this.currentInput.length)
        }

        // 更新字符完成数
        this.wordsCompleted = this.currentInput.length

        // 检查是否有错误
        this.hasError = false
        for (let i = 0; i < this.currentInput.length; i++) {
          if (this.currentInput[i] !== this.chineseText[i]) {
            this.hasError = true
            break
          }
        }

        // 更新光标位置
        this.updateMyCursorPosition()

        // 发送进度
        this.sendProgress()
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

        // 发送进度
        this.sendProgress()
      }
    },
    
    handleKeydown(event) {
      if (!this.gameStarted) return

      if (this.roomType === 'chinese') {
        // 中文模式：不需要空格键，直接按字符输入
        // Backspace 已经在 handleInput 中处理
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
    
    completeWord() {
      // 保存当前单词的完整输入状态
      if (this.wordInputStates[this.currentWordIndex]) {
        this.wordInputStates[this.currentWordIndex].input = this.currentInput
      }
      
      this.wordsCompleted++
      this.currentWordIndex++
      this.currentInput = ''
      this.hasError = false
      this.updateMyCursorPosition()
      this.sendProgress()
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
      this.updateMyCursorPosition()
      this.sendProgress()
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
            const cursorIndex = this.currentInput.length
            
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
      this.opponentProgress = {
        username: data.username,
        words_completed: data.words_completed,
        word_index: data.word_index,
        char_index: data.char_index
      }
      
      this.opponentWordIndex = data.word_index
      
      // 计算对手光标位置
      this.$nextTick(() => {
        const wordsWrapper = this.$refs.typingArea?.querySelector('.words-wrapper')
        if (!wordsWrapper) {
          this.opponentCursorPosition = null
          this.opponentCursorLine = 0
          return
        }

        if (this.roomType === 'chinese') {
          // 中文模式：基于实际DOM元素位置计算对手光标位置
          const container = wordsWrapper.querySelector('.chinese-container')
          if (!container) {
            this.opponentCursorPosition = null
            this.opponentCursorLine = 0
            return
          }

          const containerRect = container.getBoundingClientRect()
          const charElements = wordsWrapper.querySelectorAll('.char')

          if (charElements.length === 0) {
            this.opponentCursorPosition = null
            this.opponentCursorLine = 0
            return
          }

          const cursorIndex = data.char_index

          let targetChar = null
          let useCharRight = false

          if (cursorIndex === 0) {
            // 光标在开头
            targetChar = charElements[0]
            useCharRight = false
          } else if (cursorIndex >= charElements.length) {
            // 光标在最后一个字符之后
            targetChar = charElements[charElements.length - 1]
            useCharRight = true
          } else {
            // 光标在指定位置的字符之前
            targetChar = charElements[cursorIndex]
            useCharRight = false
          }

          if (targetChar) {
            const charRect = targetChar.getBoundingClientRect()

            // 计算光标水平位置
            if (useCharRight) {
              this.opponentCursorPosition = charRect.right - containerRect.left
            } else {
              this.opponentCursorPosition = charRect.left - containerRect.left
            }

            // 计算光标垂直位置（相对于容器的top）
            this.opponentCursorLine = charRect.top - containerRect.top
          } else {
            this.opponentCursorPosition = null
            this.opponentCursorLine = 0
          }
        } else {
          // 英文模式：原有逻辑
          const wordElements = wordsWrapper.querySelectorAll('.word')
          const opponentWordEl = wordElements[data.word_index]
          if (!opponentWordEl) {
            this.opponentCursorPosition = null
            return
          }

          const charElements = opponentWordEl.querySelectorAll('.char')
          let position = 0
          const charWidth = 14

          for (let i = 0; i < Math.min(data.char_index, charElements.length); i++) {
            const charEl = charElements[i]
            if (charEl) {
              const rect = charEl.getBoundingClientRect()
              position += rect.width || charWidth
            }
          }

          this.opponentCursorPosition = position
        }
      })
    },
    
    sendProgress() {
      if (!this.currentRoom || !this.gameStarted) return

      if (this.roomType === 'chinese') {
        // 中文模式：发送字符索引和完成字数
        this.sendMessage({
          type: 'player_progress',
          word_index: 0,  // 中文模式统一为0
          char_index: this.currentInput.length,
          words_completed: this.currentInput.length,  // 完成的字符数
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
      
      // 计算总字符数（包括空格）
      const totalChars = this.wordsCompleted * 5 // 平均每个单词5个字符
      this.wpm = Math.round(totalChars / 5 / elapsedMinutes) || 0
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
        if (this.$refs.inputField) {
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
        if (charIndex < this.chineseCharStates.length) {
          return this.chineseCharStates[charIndex]
        }
        // 如果是当前正在输入的字符
        if (charIndex < this.currentInput.length) {
          return this.currentInput[charIndex] === this.chineseText[charIndex]
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
  grid-template-columns: 400px 1fr;
  gap: 10px;
  max-width: 100%;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}

/* 左侧房间面板 */
.rooms-panel {
  background: #2a2a2a;
  border-radius: 10px;
  padding: 15px;
  height: fit-content;
  position: sticky;
  top: 10px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #fff;
}

.rooms-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.room-item {
  background: #333;
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.room-item:hover {
  background: #3a3a3a;
  transform: translateY(-2px);
}

.room-item.active {
  border-color: #4caf50;
  background: #2d4a2f;
}

.room-item.full {
  opacity: 0.6;
  cursor: not-allowed;
}

.room-item.playing {
  border-color: #ff9800;
}

.room-item.chinese {
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
}

.room-item.chinese:hover {
  background: linear-gradient(135deg, #45a049 0%, #5cb85c 100%);
}

.room-type-badge {
  display: inline-block;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  margin-left: 4px;
  font-weight: 500;
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.room-name {
  font-weight: 600;
  color: #fff;
}

.room-status {
  background: #444;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.room-players {
  margin: 8px 0;
  font-size: 13px;
}

.player-name {
  color: #aaa;
  margin-bottom: 4px;
}

.room-footer {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #444;
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
}

/* 连接/登录界面 */
.connection-screen,
.login-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
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
  text-align: center;
}

.lobby-header {
  margin-bottom: 40px;
}

.lobby-header h2 {
  font-size: 32px;
  margin-bottom: 8px;
}

.users-panel {
  max-width: 300px;
  margin: 0 auto;
  text-align: left;
}

.users-panel h3 {
  margin-bottom: 16px;
  color: #fff;
}

.users-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-item {
  background: #333;
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-name {
  font-weight: 500;
}

.user-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.user-status.online {
  background: #4caf50;
  color: #fff;
}

.user-status.in-room {
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
}

.my-cursor {
  background: #4caf50;
  z-index: 10;
  box-shadow: 0 0 4px rgba(76, 175, 80, 0.5);
}

.opponent-cursor {
  background: #ff9800;
  z-index: 5;
  box-shadow: 0 0 4px rgba(255, 152, 0, 0.5);
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

/* 对手进度 */
.opponent-progress {
  background: #333;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.opponent-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.opponent-name {
  font-weight: 600;
  color: #ff9800;
}

.opponent-words {
  color: #aaa;
  font-size: 14px;
}

.progress-bar {
  height: 6px;
  background: #444;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #ff9800;
  transition: width 0.3s;
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
