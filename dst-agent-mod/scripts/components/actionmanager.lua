-- 统一动作管理器类
local ActionManager = Class(function(self, brain)
    self.brain = brain
    self.actionQueue = {}  -- 统一动作队列
    self.totalActions = 0  -- 总动作数量
    -----------------------
    -- ActionQueuer Init --
    -----------------------

end)


function ActionManager:AddAction(action)
    if not action or action.Type ~= "Action" then
        return
    end
    
    self.totalActions = self.totalActions + 1
    print("Action added to manager: " .. action.Action .. " -> " .. action.Target .. " (Total: " .. self.totalActions .. ")")
    
    table.insert(self.actionQueue, action)
    
    if self:CanProcessNextAction() then
        self:ProcessNextAction()
    else
        self:ScheduleNextActionCheck()
    end
end

function ActionManager:ProcessNextAction()
    if #self.actionQueue > 0 and not self.brain.CurrentAction then
        local nextAction = table.remove(self.actionQueue, 1)
        self.totalActions = self.totalActions - 1
        
        print("Processing action: " .. nextAction.Action .. " -> " .. nextAction.Target)
        
        -- 检查BUILD动作的材料
        if nextAction.Action == "BUILD" and nextAction.Recipe and nextAction.Recipe ~= "-" then
            local recipe = GetValidRecipe(nextAction.Recipe)
            if not recipe then
                print("BUILD action failed: recipe not found " .. nextAction.Recipe)
                self:OnActionFailed(nextAction, "RECIPE_NOT_FOUND")
                return
            elseif not self.brain.inst.components.builder:HasIngredients(recipe) then
                print("BUILD action failed: insufficient ingredients")
                self:OnActionFailed(nextAction, "INSUFFICIENT_INGREDIENTS")
                return
            end
        end
        
        -- 检查工作动作目标是否存在
        if self:IsWorkAction(nextAction.Action) or nextAction.Action == "EAT" and Ents[tonumber(nextAction.Target)] == nil then
            self:OnActionFailed(nextAction, "TARGET_NOT_FOUND")
            return
        end


        
        -- 检查工作动作是否有合适的工具
        if nextAction.Action == "CHOP" then
            if not self:HasToolForAction(ACTIONS.CHOP) then
                print("CHOP action failed: no suitable tool available")
                self:OnActionFailed(nextAction, "NO_CHOP_TOOL")
                return
            end
        elseif nextAction.Action == "MINE" then
            if not self:HasToolForAction(ACTIONS.MINE) then
                print("MINE action failed: no suitable tool available")
                self:OnActionFailed(nextAction, "NO_MINE_TOOL")
                return
            end
        elseif nextAction.Action == "HAMMER" then
            if not self:HasToolForAction(ACTIONS.HAMMER) then
                print("HAMMER action failed: no suitable tool available")
                self:OnActionFailed(nextAction, "NO_HAMMER_TOOL")
                return
            end
        elseif nextAction.Action == "DIG" then
            if not self:HasToolForAction(ACTIONS.DIG) then
                print("DIG action failed: no suitable tool available")
                self:OnActionFailed(nextAction, "NO_DIG_TOOL")
                return
            end
        end
        
        -- 判断动作类型并处理
        if self:IsWorkAction(nextAction.Action) then
            self:ProcessWorkAction(nextAction)
        else
            self:ProcessRegularAction(nextAction)
        end
    end
end

function ActionManager:ProcessWorkAction(action)
    local target = Ents[tonumber(action.Target)]
    if not target or not target:IsValid() then
        print("Work action target not found: " .. action.Action .. " -> " .. action.Target)
        self:OnActionFailed(action, "TARGET_NOT_FOUND")
        return
    end
    
    print("Processing work action: " .. action.Action .. " -> " .. target.prefab)
    
    -- 检查actionqueuer是否正在执行
    if self.brain.inst.components.actionqueuer.action_thread then
        print("ActionQueuer is busy, adding target to selection")
        self.brain.inst.components.actionqueuer:SelectEntity(target, false)
        return
    end
    
    -- actionqueuer空闲，开始新的执行
    self.brain.inst.components.actionqueuer:ClearSelectedEntities()
    self.brain.inst.components.actionqueuer:SelectEntity(target, false)
    
    -- 设置完成回调
    local originalClearActionThread = self.brain.inst.components.actionqueuer.ClearActionThread
    local hasNotified = false
    local actionManager = self  -- 保存ActionManager的引用
    
    self.brain.inst.components.actionqueuer.ClearActionThread = function(actionqueuer)
        
        originalClearActionThread(actionqueuer)
        
        if not hasNotified then
            hasNotified = true
            print("ActionQueuer work action completed: " .. action.Action)
            actionManager:OnActionCompleted(action)
        end
    end
    
    -- 开始执行
    self.brain.inst.components.actionqueuer:ApplyToSelection()
end

function ActionManager:ProcessRegularAction(action)
    print("Processing regular action: " .. action.Action .. " -> " .. action.Target)
    
    -- 设置当前动作
    self.brain.CurrentAction = action
    self.brain.ActionStartTime = GetTime()
end

function ActionManager:OnActionCompleted(action)
    print("Action completed: " .. action.Action .. " (Total remaining: " .. self.totalActions .. ")")
    
    -- 清理当前动作状态
    if self.brain.CurrentAction == action then
        self.brain.CurrentAction = nil
        self.brain.ActionStartTime = nil
    end
    
    -- 通知Agent
    print("Post OnActionCompletedEvent: " .. action.WFN .. " -> " .. action.Target)
    self.brain:OnActionCompletedEvent(action.WFN, action.Target)
    
    -- 检查下一个动作
    self:ScheduleNextActionCheck()
end

function ActionManager:OnActionFailed(action, reason)
    -- 清理当前动作状态
    self.brain.CurrentAction = nil
    self.brain.ActionStartTime = nil
    if action then
        print("Action failed: " .. action.WFN .. " - " .. (reason or "unknown") .. " (Total remaining: " .. self.totalActions .. ")")
        self.brain:OnActionFailedEvent(action.WFN, action.Target, reason)
    end

    
    -- 检查下一个动作
    self:ScheduleNextActionCheck()
end

function ActionManager:ScheduleNextActionCheck()
    if self.totalActions > 0 then
        local actionManager = self  -- 保存ActionManager的引用
        self.brain.inst:DoTaskInTime(0.2, function()
            -- 检查是否可以处理下一个动作
            if actionManager:CanProcessNextAction() then
                actionManager:ProcessNextAction()
            else
                actionManager:ScheduleNextActionCheck()
            end
        end)
    end
end

function ActionManager:CanProcessNextAction()
    -- 检查actionqueuer是否正在执行
    if self.brain.inst.components.actionqueuer and self.brain.inst.components.actionqueuer.action_thread then
        print("ActionQueuer is busy, cannot process next action")
        return false
    end
    
    -- 检查是否有当前动作在执行
    if self.brain.CurrentAction ~= nil then
        return false
    end
    
    -- 检查是否还有正在进行的bufferedaction
    if self.brain.inst.bufferedaction ~= nil then
        print("BufferedAction is busy, cannot process next action")
        return false
    end
    
    -- 检查最小动作持续时间
    if self.brain.ActionStartTime and (GetTime() - self.brain.ActionStartTime) < self.brain.MinActionDuration then
        print("Action duration too short, cannot process next action")
        return false
    end
    
    return true
end

function ActionManager:IsWorkAction(action)
    return action == "ATTACK" or action == "CHOP" or action == "MINE" or action == "HAMMER" or action == "DIG"
end

function ActionManager:HasToolForAction(action)
    local inst = self.brain.inst
    
    -- 检查手上装备的工具
    local equipped = inst.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
    if equipped and equipped.components.tool and equipped.components.tool:CanDoAction(action) then
        return true
    end

    
    return false
end

function ActionManager:ClearAll()
    self.actionQueue = {}
    self.totalActions = 0
    self.brain.inst.components.actionqueuer:ClearAllThreads()
    print("Action manager cleared")
end

function ActionManager:GetStatus()
    return {
        totalActions = self.totalActions,
        queueLength = #self.actionQueue
    }
end

return ActionManager