-- 导入必要的模块
require("recipe")

local SEE_DIST = 21
local SEE_RANGE_HELPER = false
local PERCEPTION_UPDATE_INTERVAL = 1
local DSTACTION_INTERVAL = 1.5
local SPEAKACTION_INTERVAL = 5
local NUM_SEGS = 16

local PATHFINDACTION_INTERVAL = 3
local MINDIST = 2


ActionManager = require("components/actionmanager")




-- A user-friendly function to print any table, including nested ones
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

local function GetStatus(inst)
    local status = {}
	status.Health = tostring(math.floor(inst.components.health.currenthealth)) .. " / " .. tostring(math.floor(inst.components.health.maxhealth))
	status.Hunger = tostring(math.floor(inst.components.hunger.current)) .. " / " .. tostring(math.floor(inst.components.hunger.max))
	status.Sanity = tostring(math.floor(inst.components.sanity.current)) .. " / " .. tostring(math.floor(inst.components.sanity.max))
	status.Temperature = tostring(math.floor(inst:GetTemperature()))
	status.Moisture = tostring(math.floor(inst:GetMoisture()))
	return status
end


local function AddSeeRangeHelper(inst)
    if SEE_RANGE_HELPER and inst.seerangehelper == nil then
        inst.seerangehelper = CreateEntity()

        --[[Non-networked entity]]
        inst.seerangehelper.entity:SetCanSleep(false)
        inst.seerangehelper.persists = false

        inst.seerangehelper.entity:AddTransform()
        inst.seerangehelper.entity:AddAnimState()

        inst.seerangehelper:AddTag("CLASSIFIED")
        inst.seerangehelper:AddTag("NOCLICK")
        inst.seerangehelper:AddTag("placer")

        inst.seerangehelper.Transform:SetScale(SEE_DIST/11, SEE_DIST/11, SEE_DIST/11)

        inst.seerangehelper.AnimState:SetBank("firefighter_placement")
        inst.seerangehelper.AnimState:SetBuild("firefighter_placement")
        inst.seerangehelper.AnimState:PlayAnimation("idle")
        inst.seerangehelper.AnimState:SetLightOverride(1)
        inst.seerangehelper.AnimState:SetOrientation(ANIM_ORIENTATION.OnGround)
        inst.seerangehelper.AnimState:SetLayer(LAYER_BACKGROUND)
        inst.seerangehelper.AnimState:SetSortOrder(1)
        inst.seerangehelper.AnimState:SetAddColour(0, .2, .5, 0)

        inst.seerangehelper.entity:SetParent(inst.entity)
    end
end

local function Entity(inst, v)
	local d = {}

	d.GUID = v.GUID
	d.Prefab = v.prefab
	d.Quantity = v.components.stackable ~= nil and v.components.stackable:StackSize() or 1

	d.Collectable = v:HasTag("pickable") -- PICK
	d.Cooker = v:HasTag("cooker")
	d.Cookable = v:HasTag("cookable")
	d.Edible = inst.components.eater:CanEat(v)
	d.Equippable = v:HasTag("_equippable")
	d.Fuel = v:HasTag("BURNABLE_fuel")
	d.Fueled = v:HasTag("BURNABLE_fueled")
	d.Grower = v:HasTag("grower") 
	d.Harvestable = v:HasTag("readyforharvest") or (v.components.stewer and v.components.stewer:IsDone())
	d.Pickable = v.components.inventoryitem and v.components.inventoryitem.canbepickedup and not v:HasTag("heavy") -- PICKUP
	d.Stewer= v:HasTag("stewer")

	d.Choppable = v:HasTag("CHOP_workable")
	d.Diggable = v:HasTag("DIG_workable")
	d.Hammerable = v:HasTag("HAMMER_workable")
	d.Mineable = v:HasTag("MINE_workable")

	d.X, d.Y, d.Z = v.Transform:GetWorldPosition()
	return d
end


local function GetDistanceBetweenPoints(pos1, pos2)
    local dx = pos1.x - pos2.x
    local dz = pos1.z - pos2.z
    return math.sqrt(dx * dx + dz * dz)
end


local AgentBrain = Class(Brain, function(self, inst, global_vars, server)
    Brain._ctor(self, inst)
    self.inst = inst
	self.GLOBAL = global_vars
    ------------------------------
    ---- Agent Communication ----
    ------------------------------
    self.AgentServer = server or "http://localhost:8081"
	
    ------------------------------
    -- HTTP Callbacks Functions --
    ------------------------------
	self.OnPerceptions = function() self:Perceptions() end
    self.PerceptionsCallback = function(result, isSuccessful , http_code)
        -- Intentionally left blank
    end

	self.OnEventCallback = function(result, isSuccessful , http_code)
		-- Intentionally left blank
	end

	self.OnPATHFINDActionDecide = function() self:CheckArrive() end


	self.OnDSTActionDecide = function() self:DecideAction("Behaviour") end
	self.OnSpeakActionDecide = function() self:DecideDialog("Dialog") end
    self.DecideCallback = function(result, isSuccessful, http_code)
        if isSuccessful then
			local action = result and (result ~= "") and json.decode(result)

			-- PrintTable(action, "action")
			print("self.CurrentAction", self.CurrentAction)

			if action and action.Type then
				if action.Type == "Action" and action.Action ~= "STOP" then
					-- 使用统一的动作管理器
					self.actionManager:AddAction(action)
				elseif action.Type == "Action" and action.Action == "STOP" then
					self:OnStop()
				elseif action.Type == "Speak" then
					print(action.Utterance)
					if action.Utterance ~= "" then self.inst.components.talker:Say(action.Utterance) end
				end
			end
		end
    end

	self.OnStop = function()
		print("action stop")
		-- Stop any current buffered action
		self.CurrentAction = nil
		self.inst.bufferedaction = nil
		self.inst.components.locomotor:Stop()
		print("self.inst.components.locomotor.keepexploring to false")
		self.inst.components.locomotor.keepexploring = false
		self.actionManager:ClearAll()
		if self.bt then	self.bt:Reset()	end
		-- 关闭目的地检查任务
		if self.inst.components.locomotor and self.inst.components.locomotor.destinationCheckTask then
			self.inst.components.locomotor.destinationCheckTask:Cancel()
			self.inst.components.locomotor.destinationCheckTask = nil
		end
	end
	------------------------------
    -- Event Listener Functions --
    ------------------------------
	
	self.OnFailedMy = function(inst, data)
		PrintTable(data, "action failed - data")
		PrintTable(data.action, "action failed - action")
		if type(data.action.action) == "table" then
			print("action is a table")
			for k, v in pairs(data.action.action) do
				print(k, v)
			end
		end
		local action = {}
		action.Action = data.action.action.id
		action.Target = ""
		action.Type = "Action"
		action.Subject = "Walter"
		action.WFN = data.action.action.id
		self.actionManager:OnActionFailed(action, "has already been " .. action.Action .. "ed" )
	end

	self.OnToolBrokeMy = function(inst, data)
		-- PrintTable(data, "action failed - data")
		-- 延迟0.1秒后获取物品
		self.inst:DoTaskInTime(0.5, function()
			local item = self.inst.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
			-- print(item)
			if item then
				local action = {}
			else
				local action = {}
				action.Action = ""
				action.Target = ""
				action.Type = "Action"
				action.Subject = "Walter"
				action.WFN = "toolbroke"
				self.actionManager:OnActionFailed(action, "" )
			end
		end)
	end

	self.OnInventoryFullMy = function(inst, data)
		print("inventory full")

		local dropped_item = self.inst.components.inventory:DropActiveItem()
		self.actionManager:ClearAll()

		local action = {}
		action.Action = ""
		action.Target = ""
		action.Type = "Action"
		action.Subject = "Walter"
		action.WFN = "inventoryfull"
		self.actionManager:OnActionFailed(action, "inventory full, item dropped" )
	end

	------------------------------
    ------ Watch World State -----
    ------------------------------

	self.OnClockTick = function (inst, data)
		if self.time ~= nil then
			local prevseg = math.floor(self.time * NUM_SEGS)
			local nextseg = math.floor(data.time * NUM_SEGS)
			if prevseg ~= nextseg then
				self:OnPropertyChangedEvent("World(CurrentSegment)", nextseg)
			end
		else
			-- The first time we need to tell Agent what is the current segment
			-- self:OnPropertyChangedEvent("World(CurrentSegment)", math.floor(data.time * NUM_SEGS))
		end
		
		-- 检查是否接近夜晚
		local current_seg = math.floor(data.time * NUM_SEGS)
		local clock_segs = TheWorld.net.components.clock:OnSave().segs
		local day_segs = clock_segs.day or 8  -- 默认白天8个时间段
		local dusk_segs = clock_segs.dusk or 6  -- 默认黄昏6个时间段
		local night_start_seg = day_segs + dusk_segs  -- 夜晚开始的时间段
		
		if current_seg >= night_start_seg - 1 then
			if not self._entered_dark_today then
				print("Entering dark")
				self:OnPropertyChangedEvent("EnteringNight", "True")
				self.OnStop()
				self._entered_dark_today = true
			end
		elseif current_seg == 0 then
			-- 新的一天，重置标志
			self._entered_dark_today = false
		end


	end
	self.OnClockSegsChanged = function(inst, data) 
		self:OnPropertyChangedEvent("World(PhaseLenght, day)", data.day) 
		self:OnPropertyChangedEvent("World(PhaseLenght, dusk)", data.dusk) 
		self:OnPropertyChangedEvent("World(PhaseLenght, night)", data.night) 
	end
	self.OnEnterDark = function(inst, data) self:OnPropertyChangedEvent("InLight(Walter)", "False") end
	self.OnEnterLight = function(inst, data) self:OnPropertyChangedEvent("InLight(Walter)", "True") end
	self.OnCycles = function(inst, cycles) if cycles ~= nil then self:OnPropertyChangedEvent("World(Cycle)", cycles + 1) end end
	self.OnPhase = function(inst, phase) self:OnPropertyChangedEvent("World(Phase)", phase) end
	self.OnMoonPhase = function(inst, moonphase) self:OnPropertyChangedEvent("World(MoonPhase)", moonphase) end
	self.OnSeason = function(inst, season) self:OnPropertyChangedEvent("World(Season)", season) end
	self.OnSeasonProgress = function(inst, seasonprogress) self:OnPropertyChangedEvent("World(SeasonProgress)", seasonprogress) end
	self.OnElapsedDaysInSeason = function(inst, elapseddaysinseason) self:OnPropertyChangedEvent("World(ElapsedDaysInSeason)", elapseddaysinseason) end
	self.OnRemainingDaysInSeason = function(inst, remainingdaysinseason) self:OnPropertyChangedEvent("World(RemainingDaysInSeason)", remainingdaysinseason) end
	self.OnSpringLength = function(inst, springlength) self:OnPropertyChangedEvent("World(SpringLength)", springlength) end
	self.OnSummerLength = function(inst, summerlength) self:OnPropertyChangedEvent("World(SummerLength)", summerlength) end
	self.OnAutumnLength = function(inst, autumnlength) self:OnPropertyChangedEvent("World(AutumnLenght)", autumnlength) end
	self.OnWinterLength = function(inst, winterlength) self:OnPropertyChangedEvent("World(WinterLenght)", winterlength) end
	self.OnIsSnowing = function(inst, issnowing) self:OnPropertyChangedEvent("World(IsSnowing)", issnowing) end
	self.OnIsRaining = function(inst, israining) self:OnPropertyChangedEvent("World(IsRaining)", israining) end


    

end)



function AgentBrain:Perceptions()
    local data = {}

	-- Vision
	local x, y, z = self.inst.Transform:GetWorldPosition()
    local TAGS = nil
    local EXCLUDE_TAGS = {"INLIMBO", "NOCLICK", "CLASSIFIED", "FX"}
    local ONE_OF_TAGS = nil
    local ents = TheSim:FindEntities(x, y, z, SEE_DIST, TAGS, EXCLUDE_TAGS, ONE_OF_TAGS)
	
    
    -- Go over all the objects that the agent can see and take what information we need
    local vision = {}
	local j = 1
    for i, v in pairs(ents) do
		if v.GUID ~= self.inst.GUID then
			vision[j] = Entity(self.inst, v)
			j = j+1
		end
    end
    data.Vision = vision

	-- Inventory
	local equipslots = {}
    local itemslots = {}
	local backpack = {}
 
    -- Go over all items in the inventory and take what information we need
    for k, v in pairs(self.inst.components.inventory.itemslots) do
        itemslots[k] = Entity(self.inst, v)
    end

    -- Go over equipped items and put them in an array
    -- I chose to use an array not to limit which equip slots the agent has.
    -- This way I do not need to change any code, should any new slot appear.
    local i = 1
    for k, v in pairs(self.inst.components.inventory.equipslots) do
        equipslots[i] = Entity(self.inst, v)
        i = i + 1
        
        -- 检查equipslots里有没有属于container的物品，有的话就获取container的所有物品加入到equipslots中
        if v and v.components and v.components.container then
            local container_items = v.components.container:GetAllItems()
            for _, container_item in pairs(container_items) do
                table.insert(backpack, Entity(self.inst, container_item))
            end
        end
    end
    data.EquipSlots, data.ItemSlots = equipslots, itemslots
	data.Backpack = backpack

    data.Health = tostring(math.floor(self.inst.components.health.currenthealth)) .. " / " .. tostring(math.floor(self.inst.components.health.maxhealth))
    data.Hunger = tostring(math.floor(self.inst.components.hunger.current)) .. " / " .. tostring(math.floor(self.inst.components.hunger.max))
    data.Sanity = tostring(math.floor(self.inst.components.sanity.current)) .. " / " .. tostring(math.floor(self.inst.components.sanity.max))
    data.Temperature = tostring(math.floor(self.inst:GetTemperature()))
    data.IsFreezing = self.inst:IsFreezing()
    data.IsOverHeating = self.inst:IsOverheating()
    data.Moisture = tostring(math.floor(self.inst:GetMoisture()))
	if (self.CurrentAction ~= nil and self.CurrentAction.Type == "Action" and self.CurrentAction.Action == "WANDER") or 
		(self.CurrentAction == nil) then 
		data.IsBusy = false
	else
		data.IsBusy = true
	end
	local x, y, z = self.inst.Transform:GetWorldPosition()
	data.PosX = string.format("%.1f", x)
	data.PosY = string.format("%.1f", y)
	data.PosZ = string.format("%.1f", z)

    TheSim:QueryServer(
        self.AgentServer .. "/" .. tostring(self.inst.GUID) .. "/perceptions",
        self.PerceptionsCallback,
        "POST",
		json.encode_compliant(data))
end

function AgentBrain:CheckArrive()
	if self.CurrentAction and self.CurrentAction.Type == "Action" and self.CurrentAction.Action == "PATHFIND" then
		local current_pos = self.inst.Transform:GetWorldPosition()
		local x, y, z = self.inst.Transform:GetWorldPosition()
		current_pos = self.GLOBAL.Vector3(
			x,
			0,
			z
		)
		local target_pos = self.GLOBAL.Vector3(
			tonumber(self.CurrentAction.PosX),
			0,
			tonumber(self.CurrentAction.PosZ)
		)
		print(current_pos)
		print(target_pos)
		if self.last_pos_for_stuck_check then
			print("distance")
			print(GetDistanceBetweenPoints(current_pos, self.last_pos_for_stuck_check))
		end
		if GetDistanceBetweenPoints(current_pos, target_pos) < MINDIST then
			print("Pathfind action succeeded: Character reached the target.")
			self.actionManager:OnActionCompleted(self.CurrentAction)
			if self.bt then
				print("reset bt")
                self.bt:Reset()
            end
			return
		elseif self.last_pos_for_stuck_check and GetDistanceBetweenPoints(current_pos, self.last_pos_for_stuck_check) < MINDIST then
			print("Pathfind action failed: Character stuck.")
			self.actionManager:OnActionFailed(self.CurrentAction, "PATHFIND_STUCK")
			if self.bt then
                self.bt:Reset()
            end
		end
		self.last_pos_for_stuck_check = current_pos
	end
end

function AgentBrain:DecideAction()
	print("self.actionManager.totalActions")
	print(self.actionManager.totalActions)
	if self.actionManager.totalActions <= 1 then
		TheSim:QueryServer(
			self.AgentServer .. "/" .. tostring(self.inst.GUID) .. "/decide/Behaviour",
			self.DecideCallback,
			"GET")
	end
end

function AgentBrain:DecideDialog()
    TheSim:QueryServer(
        self.AgentServer .. "/" .. tostring(self.inst.GUID) .. "/decide/Dialog",
        self.DecideCallback,
        "GET")
end

function AgentBrain:OnActionCompletedEvent(name, value)
	local d = {}
	d.Type= "Action-End"
	d.Name = name
	d.Value = value
	d.Subject = "Walter"
	d.Info = json.encode(GetStatus(self.inst))
	TheSim:QueryServer(
        self.AgentServer .. "/" .. tostring(self.inst.GUID) .. "/events",
        self.OnEventCallback,
        "POST",
        json.encode(d))
end

function AgentBrain:OnActionFailedEvent(name, value, info)
	local d = {}
	info = info or ""
	d.Type= "Action-Failed"
	d.Name = name
	d.Value = value
	d.Subject = "Walter"
	d.Info = info
	TheSim:QueryServer(
        self.AgentServer .. "/" .. tostring(self.inst.GUID) .. "/events",
        self.OnEventCallback,
        "POST",
        json.encode(d))
end

function AgentBrain:OnPropertyChangedEvent(name, value)
	local d = {}
	d.Type= "Property-Change"
	d.Name = name
	d.Value = value
	d.Subject = "Walter"
	TheSim:QueryServer(
        self.AgentServer .. "/" .. tostring(self.inst.GUID) .. "/events",
        self.OnEventCallback,
        "POST",
        json.encode(d))
end













function AgentBrain:OnStart()
	print("AgentBrain:OnStart")
	self.inst.entity:SetCanSleep(false)
    -----------------------
    ----- Deliberator -----
    -----------------------
	if self.inst.components.locomotor and self.inst.components.locomotor.destinationCheckTask then
		self.inst.components.locomotor.destinationCheckTask:Cancel()
		self.inst.components.locomotor.destinationCheckTask = nil
	end

	-- 用于寻路失败判断的变量
	self.last_pos_for_stuck_check = nil


	self.CurrentAction = nil
    self.ActionStartTime = nil
    self.MinActionDuration = 1.0
    
    ----- Range Helper ----
    AddSeeRangeHelper(self.inst)


    ----- Perceptions -----
    if self.PerceptionsTask ~= nil then self.PerceptionsTask:Cancel() end
    self.PerceptionsTask = self.inst:DoPeriodicTask(PERCEPTION_UPDATE_INTERVAL, self.OnPerceptions, 0)


    -------- Decide -------
	if self.DSTActionTask ~= nil then self.DSTActionTask:Cancel() end
    self.DSTActionTask = self.inst:DoPeriodicTask(DSTACTION_INTERVAL, self.OnDSTActionDecide, 0)

	if self.PATHFINDActionTask ~= nil then self.PATHFINDActionTask:Cancel() end
    self.PATHFINDActionTask = self.inst:DoPeriodicTask(PATHFINDACTION_INTERVAL, self.OnPATHFINDActionDecide, 0)
	
	if self.SpeakActionTask ~= nil then self.SpeakActionTask:Cancel() end
	self.SpeakActionTask = self.inst:DoPeriodicTask(SPEAKACTION_INTERVAL, self.OnSpeakActionDecide, 0)
	
    ------------------------------
    -- Action Queue Management --
    ------------------------------
    -- 确保有 actionqueuer 组件
    if not self.inst.components.actionqueuer then
        print("[AgentBrain] Adding ActionQueuer component")
        self.inst:AddComponent("actionqueuer")
    end
    
    -- 设置 actionqueuer 的自动收集功能
    self.inst.components.actionqueuer.auto_collect = true
    print("[AgentBrain] ActionQueuer auto_collect enabled")
	
    self.actionManager = ActionManager(self)  -- 统一动作管理器
    self.ActionStartTime = nil  -- 动作开始时间
    self.MinActionDuration = 0.1  -- 最小动作持续时间（秒）
    -----------------------
    --- Event Listeners ---
    -----------------------
	self.inst:ListenForEvent("actionfailed", self.OnFailedMy)
	self.inst:ListenForEvent("toolbroke", self.OnToolBrokeMy)
	self.inst:ListenForEvent("inventoryfull", self.OnInventoryFullMy)


    ---- World Watchers ---
	self.inst:ListenForEvent("enterdark", self.OnEnterDark)
	self.inst:ListenForEvent("enterlight", self.OnEnterLight)
	self.inst:ListenForEvent("clocksegschanged", self.OnClockSegsChanged, TheWorld)
	self.inst:ListenForEvent("clocktick", self.OnClockTick, TheWorld)
	self.inst:WatchWorldState("cycles", self.OnCycles)
	self.inst:WatchWorldState("phase", self.OnPhase)
	self.inst:WatchWorldState("moonphase", self.OnMoonPhase)
	self.inst:WatchWorldState("season", self.OnSeason)
	self.inst:WatchWorldState("seasonprogress", self.OnSeasonProgress)
	self.inst:WatchWorldState("elapseddaysinseason", self.OnElapsedDaysInSeason)
	self.inst:WatchWorldState("remainingdaysinseason", self.OnRemainingDaysInSeason)
	self.inst:WatchWorldState("springlength", self.OnSpringLenght)
	self.inst:WatchWorldState("summerlength", self.OnSummerLength)	
	self.inst:WatchWorldState("autumnlength", self.OnAutumnLenght)
	self.inst:WatchWorldState("winterlength", self.OnWinterLenght)
	self.inst:WatchWorldState("issnowing", self.OnIsSnowing)
	self.inst:WatchWorldState("israining", self.OnIsRaining)

	-- Registered listeners to tell Agent about changes, now let's tell Agent the initial values
	self.OnClockSegsChanged(self.inst, TheWorld.net.components.clock:OnSave().segs)
		if self.inst.LightWatcher:IsInLight() then
			self.OnEnterLight(self.inst, nil)
		else
			self.OnEnterDark(self.inst, nil)
	end
	self.OnCycles(self.inst, TheWorld.state.cycles)
	self.OnPhase(self.inst, TheWorld.state.phase)
	self.OnMoonPhase(self.inst, TheWorld.state.moonphase)
	self.OnSeason(self.inst, TheWorld.state.season)
	self.OnSeasonProgress(self.inst, TheWorld.state.seasonprogress)
	self.OnElapsedDaysInSeason(self.inst, TheWorld.state.elapseddaysinseason)
	self.OnRemainingDaysInSeason(self.inst, TheWorld.state.remainingdaysinseason)
	self.OnSpringLength(self.inst, TheWorld.state.springlength)
	self.OnSummerLength(self.inst, TheWorld.state.summerlength)
	self.OnAutumnLength(self.inst, TheWorld.state.autumnlength)
	self.OnWinterLength(self.inst, TheWorld.state.winterlength)
	self.OnIsSnowing(self.inst, TheWorld.state.issnowing)
	self.OnIsRaining(self.inst, TheWorld.state.israining)

    -----------------------
    -------- Brain --------
    -----------------------
	-- BufferedAction(doer, target, action, invobject, pos, recipe, distance, forced, rotation)
    local root = 
        PriorityNode(
        {
            IfNode(function() return (self.CurrentAction ~= nil and self.CurrentAction.Type == "Action" and self.CurrentAction.Action ~= "WANDER" and self.CurrentAction.Action ~= "PATHFIND" and self.CurrentAction.Action ~= "EXPLORE") end, "IfAction",
                DoAction(self.inst, 
					-- BufferedAction(Doer, Target, Action, InvObject, Pos, Recipe)
					function() 
						print("do action")
						print(self.CurrentAction.Action)
						print("Ents[tonumber(self.CurrentAction.Target)]")
						print(Ents[tonumber(self.CurrentAction.Target)])
						local b = BufferedAction(
							self.inst,
							Ents[tonumber(self.CurrentAction.Target)],
							ACTIONS[self.CurrentAction.Action],
							Ents[tonumber(self.CurrentAction.InvObject)],
							(self.CurrentAction.PosX ~= "-" and Vector3(tonumber(self.CurrentAction.PosX), tonumber(self.CurrentAction.PosY), tonumber(self.CurrentAction.PosZ)) or nil),
							(self.CurrentAction.Recipe ~= "-") and self.CurrentAction.Recipe or nil)
						
						-- 如果是DROP动作，设置为丢掉全部物品
						if self.CurrentAction.Action == "DROP" then
							b.options.wholestack = true
						end

						b:AddFailAction(function() 
							print("action failed")
							if self.CurrentAction then
								self.actionManager:OnActionFailed(self.CurrentAction, "target does not exist")
							end
						end)

						b:AddSuccessAction(function() 
							print("action completed")
							if self.CurrentAction then
								self.actionManager:OnActionCompleted(self.CurrentAction)
							end
						end)
						return b
					end, 
					"DoAction", 
					true)
				-- Close DoAction
			),
			IfNode(function() 
				return (self.CurrentAction ~= nil 
					and self.CurrentAction.Type == "Action" 
					and self.CurrentAction.Action == "EXPLORE") 
			end, "IfExplore",
				DoAction(self.inst, 
					function()
						print("do action")
						print(self.CurrentAction.Action)
						-- 创建 TRAILBLAZE 动作
						if self.GLOBAL.ACTIONS.EXPLORE then
							local b = self.GLOBAL.BufferedAction(
								self.inst,
								nil,
								self.GLOBAL.ACTIONS.EXPLORE,
								nil,
								self.GLOBAL.Vector3(
									tonumber(self.CurrentAction.PosX), 
									0, 
									tonumber(self.CurrentAction.PosZ)
								)
							)

							return b
						end
					end, 
					"DoExploreAction", 
					true)
			),
			IfNode(function() 
				return (self.CurrentAction ~= nil 
					and self.CurrentAction.Type == "Action" 
					and self.CurrentAction.Action == "PATHFIND") 
			end, "IfPathfind",
				DoAction(self.inst, 
					function()
						print("do action")
						print(self.CurrentAction.Action)
						-- 创建 TRAILBLAZE 动作
						if self.GLOBAL.ACTIONS.TRAILBLAZE then
							local b = self.GLOBAL.BufferedAction(
								self.inst,
								nil,
								self.GLOBAL.ACTIONS.TRAILBLAZE,
								nil,
								self.GLOBAL.Vector3(
									tonumber(self.CurrentAction.PosX), 
									0, 
									tonumber(self.CurrentAction.PosZ)
								)
							)

							return b
						end
					end, 
					"DoPathfindAction", 
					true)
			),
			WhileNode(function() return (self.CurrentAction ~= nil and self.CurrentAction.Type == "Action" and self.CurrentAction.Action == "WANDER") end, "Wander",
				Wander(self.inst, nil, nil, { minwalktime = 5, randwalktime = 1, minwaittime = 1,	randwaittime = 1})
			)
        }, 1)
	print("bt created")
    self.bt = BT(self.inst, root)
end

function AgentBrain:OnStop()
    -----------------------
    ----- Range Helper ----
    -----------------------
    if SEE_RANGE_HELPER then
        self.inst.seerangehelper:Remove()
        self.inst.seerangehelper = nil
    end
    -----------------------
    ----- Perceptions -----
    -----------------------
    if self.PerceptionsTask ~= nil then
        self.PerceptionsTask:Cancel()
        self.PerceptionsTask = nil
    end
    -----------------------
    -------- Decide -------
    -----------------------
	if self.DSTActionTask ~= nil then
        self.DSTActionTask:Cancel()
		self.DSTActionTask= nil
    end

	if self.PATHFINDActionTask ~= nil then
        self.PATHFINDActionTask:Cancel()
		self.PATHFINDActionTask= nil
    end
	
	if self.SpeakActionTask ~= nil then
		self.SpeakActionTask:Cancel()
		self.SpeakActionTask = nil
	end
	


    -----------------------
    -- Action Queue Clean --
    -----------------------
    self.actionManager:ClearAll()
    self.CurrentAction = nil
    self.ActionStartTime = nil
    


    -----------------------
    --- Event Listeners ---
    -----------------------



	-----------------------
    ---- World Watchers ---
    -----------------------
	self.inst:RemoveEventCallback("enterdark", self.OnEnterDark)
	self.inst:RemoveEventCallback("enterlight", self.OnEnterLight)
	self.inst:RemoveEventCallback("clocksegschanged", self.OnClockSegsChanged, TheWorld)
	self.inst:RemoveEventCallback("clocktick", self.OnClockTick, TheWorld)
	self.inst:StopWatchingWorldState("cycles", self.OnCycles)
	self.inst:StopWatchingWorldState("phase", self.OnPhase)
	self.inst:StopWatchingWorldState("moonphase", self.OnMoonPhase)
	self.inst:StopWatchingWorldState("season", self.OnSeason)
	self.inst:StopWatchingWorldState("seasonprogress", self.OnSeasonProgress)
	self.inst:StopWatchingWorldState("elapseddaysinseason", self.OnElapsedDaysInSeason)
	self.inst:StopWatchingWorldState("remainingdaysinseason", self.OnRemainingDaysInSeason)
	self.inst:StopWatchingWorldState("springlength", self.OnSpringLenght)
	self.inst:StopWatchingWorldState("summerlength", self.OnSummerLength)	
	self.inst:StopWatchingWorldState("autumnlength", self.OnAutumnLenght)
	self.inst:StopWatchingWorldState("winterlength", self.OnWinterLenght)
	self.inst:StopWatchingWorldState("issnowing", self.OnIsSnowing)
	self.inst:StopWatchingWorldState("israining", self.OnIsRaining)

	self.inst.entity:SetCanSleep(true)
end

return AgentBrain