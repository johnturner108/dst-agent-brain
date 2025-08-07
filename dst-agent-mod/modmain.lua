-- Debug Helpers
GLOBAL.CHEATS_ENABLED = true
GLOBAL.require 'debugkeys'
GLOBAL.require 'debughelpers'

-- 显式声明全局变量以避免严格模式错误
GLOBAL.c_auto = nil
GLOBAL.c_deauto = nil
GLOBAL.c_behaviour = nil
GLOBAL.c_perception = nil

local ArtificalWalterEnabled = false -- 跟踪 AI 状态的变量


PrintTable = function(tableCheck, cue)
	if type(tableCheck) == "table" then
		print("---" .. cue .."---")
		for key, value in pairs(tableCheck) do
			if type(value) == "table" then
				print(key .. ": " .. tostring(value))
			else
				print(key .. ": " .. tostring(value))
			end
		end
		print("------------------------------------")
	else
		print("Is not a table, or is nil/empty: ")
	end
end

-- 重写Networking_Say函数来捕获聊天消息
local original_Networking_Say = GLOBAL.Networking_Say
GLOBAL.Networking_Say = function(guid, userid, name, prefab, message, colour, whisper, isemote, user_vanity)
    -- 调用原始函数
    if original_Networking_Say then
        original_Networking_Say(guid, userid, name, prefab, message, colour, whisper, isemote, user_vanity)
    end
    
    -- 如果不是表情消息且有实际内容，则发送到8001端口
    if not isemote and message and message:utf8len() > 0 then
        local message_data = {
            player_name = name or "Unknown",
            message = message,
            whisper = whisper or false,
            user_id = userid or "",
            prefab = prefab or "wilson"
        }
        PrintTable(message_data, "message_data")
        -- 发送到8001端口
		print("send chat message to server")
        SendChatMessageToServer(message_data)
    end
end

function SendChatMessageToServer(message_data)
    message_data.command = message_data.message
	GLOBAL.TheSim:QueryServer(
        "http://localhost:8081" .. "/" .. tostring(1234) .. "/command",
        function(result, isSuccessful, http_code)
            print("result", result)
            print("isSuccessful", isSuccessful)
            print("http_code", http_code)
        end,
        "POST",
        GLOBAL.json.encode(message_data))
end

-- --- FindPortal 函数 (保留，因为它被下面的 AddSimPostInit 使用) ---
local function FindPortal()
	local ents = GLOBAL.TheSim:FindEntities(0, 0, 0, 10000, {"antlion_sinkhole_blocker"})
    for i, v in ipairs(ents) do
        if v.entity:IsVisible() and v.prefab == "multiplayer_portal" then
            return v
        end
    end
end
-- --- End of FindPortal ---

-- 开启玩家 AI 的函数
local function SetSelfAI()
    local AgentBrain_class = GLOBAL.require "brains/agentbrain"

    -- 将一个匿名函数传递给 SetBrain。
    -- 这个函数在被调用时，会创建 AgentBrain 的新实例。
    GLOBAL.ThePlayer:SetBrain(function(inst)
        -- 在这里，你可以访问 GLOBAL
        return AgentBrain_class(inst, GLOBAL)
    end)

    GLOBAL.ThePlayer:RestartBrain()
    ArtificalWalterEnabled = true
    print("玩家 AI 已启用！")
    GLOBAL.ThePlayer:PushEvent("ms_sendmodmessage", { modname = "AI_TOGGLE", message = "AI Enabled!" })
end


-- 关闭玩家 AI 的函数（恢复正常控制）
local function SetSelfNormal()
    local brain = GLOBAL.require "brains/wilsonbrain"
    GLOBAL.ThePlayer:SetBrain(brain)
    GLOBAL.ThePlayer:RestartBrain()
    ArtificalWalterEnabled = false
    -- 可选：在控制台打印消息以确认
    print("玩家 AI 已禁用！")
    GLOBAL.ThePlayer:PushEvent("ms_sendmodmessage", { modname = "AI_TOGGLE", message = "AI Disabled!" })
end

-- --- 原有的 MakeClickableBrain 函数已不再需要，因为它处理的是 UI 点击逻辑 ---
-- AddClassPostConstruct("widgets/sanitybadge", MakeClickableBrain) 这一行也应移除或注释掉

AddSimPostInit(function ()
    if GLOBAL.TheWorld.ismastersim then
		print("AddSimPostInit")
        -- 定义 c_auto 命令来启用 AI
        GLOBAL.c_auto = function()
            SetSelfAI()
        end

        -- 定义 c_deauto 命令来禁用 AI
        GLOBAL.c_deauto = function()
            SetSelfNormal()
        end

        GLOBAL.c_behaviour = function()
            if GLOBAL.ThePlayer and GLOBAL.ThePlayer.brain then
                -- Check if the current brain is your AgentBrain
                -- You might need a more robust way to check if it's *your* brain type
                -- (e.g., checking for a specific property or function on the brain)
                -- For simplicity, we'll assume if it has OnDSTActionDecide, it's ours.
                if GLOBAL.ThePlayer.brain.OnDSTActionDecide then
                    GLOBAL.ThePlayer.brain:OnDSTActionDecide()
                    print("手动触发 AI 行为决策！")
                else
                    print("错误：玩家没有安装 Agent AI 脑或脑类型不匹配！")
                end
            else
                print("错误：无法找到玩家或玩家没有脑！")
            end
        end

        GLOBAL.c_perception = function()
            if GLOBAL.ThePlayer and GLOBAL.ThePlayer.brain then
                -- Check if the current brain is your AgentBrain
                -- You might need a more robust way to check if it's *your* brain type
                -- (e.g., checking for a specific property or function on the brain)
                -- For simplicity, we'll assume if it has OnDSTActionDecide, it's ours.
                if GLOBAL.ThePlayer.brain.OnPerceptions then
                    GLOBAL.ThePlayer.brain:OnPerceptions()
                    print("手动触发 AI 感知！")
                else
                    print("错误：玩家没有安装 Agent AI 脑或脑类型不匹配！")
                end
            else
                print("错误：无法找到玩家或玩家没有脑！")
            end
        end

    end
end)


















local ARRIVE_STEP = .15 -- Original value inaccessible

-- 获取所有可用位置的函数
local function GetAllAvailablePositions()
    if not GLOBAL.TheWorld or not GLOBAL.TheWorld.Map then
        print("TheWorld或Map还未初始化")
        return {}
    end
    
    local map_width, map_height = GLOBAL.TheWorld.Map:GetSize()
    print("map_width", map_width)
    print("map_height", map_height)
    local positions = {}

    local step = 50
    
    -- 计算地图的实际坐标范围
    -- 地图坐标从 -(map_width/2) 到 (map_width/2)
    local min_x = -(map_width / 2) * GLOBAL.TILE_SCALE
    local max_x = (map_width / 2) * GLOBAL.TILE_SCALE
    local min_z = -(map_height / 2) * GLOBAL.TILE_SCALE
    local max_z = (map_height / 2) * GLOBAL.TILE_SCALE
    
    print("地图坐标范围: X(", min_x, "到", max_x, ") Z(", min_z, "到", max_z, ")")

    for x = min_x, max_x, step do
        for z = min_z, max_z, step do
            if GLOBAL.TheWorld.Map:IsPassableAtPoint(x, 0, z, false) then
                table.insert(positions, { x = x, z = z })
            end
        end
    end

    return positions
end

-- 判断位置是否已被探索
local function IsPositionExplored(x, z)
    if not GLOBAL.TheWorld or not GLOBAL.TheWorld.Map then
        return true -- 如果地图未加载，假设已探索以避免错误
    end
    -- return GLOBAL.TheWorld.Map:IsExplored(x, z)
    local tx, ty = GLOBAL.TheWorld.Map:GetTileXYAtPoint(x, 0, z)
    return GLOBAL.ThePlayer.player_classified.MapExplorer:IsTileSeeable(tx, ty)
end

-- 获取最近的未探索位置
local function GetNearestUnexploredPosition(player_pos, all_positions)
    local nearest_pos = nil
    local min_distance = math.huge
    
    for _, pos in ipairs(all_positions) do
        if not IsPositionExplored(pos.x, pos.z) then
            if pos then
              local map_icon = GLOBAL.SpawnPrefab("globalmapicon")
              map_icon.Transform:SetPosition(pos.x, 0, pos.z)
              map_icon.MiniMapEntity:SetIcon("target.png") -- 使用您想要的图标
              map_icon.MiniMapEntity:SetPriority(15)
              map_icon.MiniMapEntity:SetDrawOverFogOfWar(true)
              
              -- 可选：设置标记的显示名称
              if map_icon._target_displayname then
                  map_icon._target_displayname:set("目标位置")
              end
            end
            local distance = math.sqrt((player_pos.x - pos.x)^2 + (player_pos.z - pos.z)^2)
            if distance < min_distance then
                min_distance = distance
                nearest_pos = pos
            end
        end
    end



    return nearest_pos, min_distance
end

AddComponentPostInit("locomotor", function(self)

  -- Cleans up the locomotor if necessary
  local CleanupLocomotorNow = function()
    -- 清理目标位置检查任务
    if self.destinationCheckTask then
      self.destinationCheckTask:Cancel()
      self.destinationCheckTask = nil
    end
    self:Stop()
    GLOBAL.ThePlayer:EnableMovementPrediction(false)
  end

  -- Cleans up the locomotor if necessary
  local CleanupLocomotorLater = function(self)
    -- Cleanup later to avoid rubber-banding
    self.trailblazerCleanupLater = true
    -- Do not clean up now
    self.trailblazerCleanupClear = nil

    -- Cleanup, but only if the locomotor is not pathfinding
    killTask = function()
      if self.dest == nil then
        if self.trailblazerCleanupLater == true then
          CleanupLocomotorNow()
        end
      else
        GLOBAL.ThePlayer:DoTaskInTime(1.5, killTask)
      end
    end

    GLOBAL.ThePlayer:DoTaskInTime(1.5, killTask)
  end

  -- Clear Override
  local _Clear = self.Clear
  self.Clear = function(self)    
    
    if self.trailblazerCleanupClear then
      CleanupLocomotorLater(self)
    else
      _Clear(self)
    end
  end

  -- PreviewAction Override
  local _PreviewAction = self.PreviewAction
  self.PreviewAction = function(self, bufferedaction, run, try_instant)
    if bufferedaction == nil then
      return false
    end
    if bufferedaction.action == GLOBAL.ACTIONS.EXPLORE then
      self.throttle = 1
      _Clear(self)
      self:Explorer(bufferedaction.pos, bufferedaction, run)
    else
      return _PreviewAction(self, bufferedaction, run, try_instant) 
    end
  end
      
  -- PushAction Override
  local _PushAction = self.PushAction
  self.PushAction = function(self, bufferedaction, run, try_instant)
    if bufferedaction == nil then
      return
    end
    if bufferedaction.action == GLOBAL.ACTIONS.EXPLORE then
  
      self.throttle = 1
      local success, reason = bufferedaction:TestForStart()
      if not success then
        self.inst:PushEvent("actionfailed", { action = bufferedaction, reason = reason })
        return
      end
      _Clear(self)
      self:Explorer(bufferedaction.pos, bufferedaction, run)
      if self.inst.components.playercontroller ~= nil then
       self.inst.components.playercontroller:OnRemoteBufferedAction()
      end
    else
      return _PushAction(self, bufferedaction, run, try_instant) 
    end
  end
  	
  -- Navigate to entity (Fix speedmult)
  local _GoToEntity = self.GoToEntity
  self.GoToEntity = function(self, inst, bufferedaction, run)
  	self.arrive_step_dist = ARRIVE_STEP
  	_GoToEntity(self, inst, bufferedaction, run)
  end
  	
  -- Navigate to point (Fix speedmult)
  local _GoToPoint = self.GoToPoint
  self.GoToPoint = function(self, pt, bufferedaction, run, overridedest)
  	self.arrive_step_dist = ARRIVE_STEP
  	_GoToPoint(self, pt, bufferedaction, run, overridedest)
  end
     
  -- Concurrent processing
  local trailblazer = GLOBAL.require("components/explorer")
  local trailblazerProcess = function(self, dest, run)
  	
    -- Path is not nil, process!
    if self.trailblazePath ~= nil then
      print("trailblazerProcess: 处理路径中...")
      -- If path is finished
      local pathCompleted = trailblazer.processPath(self.trailblazePath, 1000)
      print("trailblazerProcess: processPath 返回:", tostring(pathCompleted))
      if pathCompleted then
        print("trailblazerProcess: 路径处理完成")
        -- If pathfinding was successful
        print("trailblazerProcess: 检查路径步骤...")
        if self.trailblazePath.nativePath.steps ~= nil then
          print("trailblazerProcess: 路径步骤数量:", #self.trailblazePath.nativePath.steps)
  				
          -- Populate pathfinding variables
  		    self.dest = dest
  		    self.throttle = 1
  
  			  self.arrive_step_dist = ARRIVE_STEP * self:GetSpeedMultiplier()
  			  self.wantstorun = run
  
  			  self.path = {}
  			  self.path.steps = self.trailblazePath.nativePath.steps
  			  self.path.currentstep = 2
  			  self.path.handle = nil
  				
  			  self.wantstomoveforward = true

          print("trailblazerCleanup状态:", tostring(self.trailblazerCleanup))
          -- Register deferred cleanup if necessary
          if self.trailblazerCleanup == true then
            print("创建目标位置检查任务...")

            -- 创建目标位置检查任务
            self.destinationCheckTask = self.inst:DoPeriodicTask(0.2, function()
              -- print("destinationCheckTask")
              -- 检查是否还在移动中
              if not self.dest then
                return
              end
              
              -- 获取目标位置和当前位置
              local destpos_x, destpos_y, destpos_z = self.dest:GetPoint()
              local mypos_x, mypos_y, mypos_z = self.inst.Transform:GetWorldPosition()
              
              -- 计算距离
              local dsq = (destpos_x - mypos_x) * (destpos_x - mypos_x) + (destpos_z - mypos_z) * (destpos_z - mypos_z)
              -- print("dsq")
              -- print(dsq)
              local arrive_threshold = 6 -- 到达阈值，可以根据需要调整
              
              -- 检查是否到达目标位置
              if dsq <= arrive_threshold * arrive_threshold then
                -- print("到达目标位置，距离: " .. math.sqrt(dsq))
                
                -- 停止检查任务
                if self.destinationCheckTask then
                  self.destinationCheckTask:Cancel()
                  self.destinationCheckTask = nil
                end
                
                -- 执行到达目标的逻辑
                if true then
                  print("到达目标位置，继续寻找下一个未探索区域...")
                  
                  local savedBufferedAction = self.autoExploreBufferedAction
                  local savedRun = self.autoExploreRun
                  
                  -- 延迟一点时间再继续，确保当前路径完全清理
                  self.inst:DoTaskInTime(0.5, function()
                    
                    if self.keepexploring then
                      print("调用 Explorer 继续探索...")
                      self.autoExploreBufferedAction = savedBufferedAction
                      self.autoExploreRun = savedRun
                      self:Explorer(nil, savedBufferedAction, savedRun)
                    else
                      print("原始状态为false，不继续探索")
                    end
                  end)
                else
                  CleanupLocomotorLater(self)
                end
              end
            end)

            -- Cleanup if the path gets cleared (user strays)
            self.trailblazerCleanupClear = true

            -- Cleanup scheduled, do not cleanup now
            self.trailblazerCleanup = nil
          end

  		    self:StartUpdatingInternal()

        -- If pathfinding was unsuccessful
        else
          print("trailblazerProcess: 路径查找失败 - 没有找到有效路径")
          print("trailblazerProcess: nativePath 内容:", tostring(self.trailblazePath.nativePath))
          if self.trailblazePath.nativePath and self.trailblazePath.nativePath.steps then
            print("trailblazerProcess: steps 数量:", #self.trailblazePath.nativePath.steps)
          else
            print("trailblazerProcess: steps 字段不存在或为空")
          end
          -- 清理目标位置检查任务
          if self.destinationCheckTask then
            self.destinationCheckTask:Cancel()
            self.destinationCheckTask = nil
          end
  			  self:Stop()
  		  end
  			self.trailblazePath = nil
      end
    end

    -- Path is no longer wanted (or may be complete)  		
  	if self.trailblazePath == nil then
      print("trailblazerProcess: 路径为空，清理任务")
      self.trailblazeTask:Cancel()
  		self.trailblazeTask = nil

      if self.trailblazerCleanup then
        CleanupLocomotorNow()
      end
  	end
  end
  	
  -- 探索地图功能
  self.Explorer = function(self, pt, bufferedaction, run, disablePM)
    self.keepexploring = true
    print("开始 Explorer 函数...")
    if self.trailblazeTask ~= nil then
      print("取消之前的任务...")
      self.trailblazeTask:Cancel()
      self.trailblazeTask = nil
    end
    
    -- 检查游戏世界是否已加载
    if not GLOBAL.TheWorld or not GLOBAL.TheWorld.Map then
      print("游戏世界还未完全加载，请稍后再试")
      -- 清理目标位置检查任务
      if self.destinationCheckTask then
        self.destinationCheckTask:Cancel()
        self.destinationCheckTask = nil
      end
      self:Stop()
      return
    end
    
    local p0 = GLOBAL.Vector3(self.inst.Transform:GetWorldPosition())
    print("玩家当前位置:", p0.x, p0.z)
    
    -- 获取所有可用位置
    local all_positions = GetAllAvailablePositions()
    print("找到", #all_positions, "个可用位置")
    
    -- 获取最近的未探索位置
    local target_pos, distance = GetNearestUnexploredPosition(p0, all_positions)
    
    if target_pos then
      print("找到最近的未探索位置:", target_pos.x, target_pos.z, "距离:", distance)
      
      local p1 = GLOBAL.Vector3(target_pos.x, 0, target_pos.z)
      local dest = {}
      if GLOBAL.CurrentRelease.GreaterOrEqualTo( GLOBAL.ReleaseID.R08_ROT_TURNOFTIDES ) then
        dest = GLOBAL.Dest(p1, nil, bufferedaction)
      else
        dest = GLOBAL.Dest(nil, p1)
      end
      
      self.trailblazePath = trailblazer.requestPath(p0, p1, self.pathcaps)
      self.trailblazeTask = self.inst:DoPeriodicTask(0, function() trailblazerProcess(self, dest, run) end)
      
      -- 设置清理标志，确保目标检查任务能被创建
      self.trailblazerCleanup = true
      print("设置 trailblazerCleanup = true")
      
      self.autoExploreBufferedAction = bufferedaction
      self.autoExploreRun = run
    else
      print("没有找到未探索的区域！地图已完全探索。")
      print("停止自动探索模式")
      -- 清理目标位置检查任务
      if self.destinationCheckTask then
        self.destinationCheckTask:Cancel()
        self.destinationCheckTask = nil
      end
      self:Stop()
    end
  end
end)

-- 注册探索地图动作 (自动寻找并前往最近的未探索区域)
AddAction("EXPLORE", "探索地图", function(act) end)
