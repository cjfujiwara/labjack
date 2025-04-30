local Ts = 1          -- sampling interval
LJ.IntervalConfig(0, Ts)                   --set interval to 10 for 10ms
local checkInterval=LJ.CheckInterval
local vsense = 0      -- sense voltage
local vff = 0         -- feed forward voltage
local vout = 0        -- PID output

-- PID Settings
local kp = -5        -- proportional coefficient
local ki = -2       -- integral coefficient

local kd = 0          -- derivative coefficient
local err0 = 0        -- error this time step
local err1 = 0        -- error previous time step
local u0 = 0          -- current PID output
local u1 = 0          -- previous PID output

-- RAM Settings
local RAM_SENSE = 46000 -- RAM for storing the sense
local RAM_PID = 46002   -- RAM for storing the PID mode
local RAM_OUT = 46004   -- RAM for storing the output voltage

local DAC_OUT = 1000    -- DAC address
local AIN_FF = 0        -- AIN address for feedforward
local AIN_SENSE = 2     -- AIN address for sense
local DIN_PID_sp = 2000    -- DIO address for PID mode single plane
local DIN_PID_stripe = 2001    -- DIO address for PID mode stripe

local PIDmode = 1

MB.W(48005, 0, 1)     --Ensure analog output is is on
MB.W(43903, 0, 1)     --set AIN_ALL_RESOLUTION_INDEX to 1(fastest, on both T7 and T4)
MB.W(30004,3,-7)
MB.W(DAC_OUT, 3, 2.5)    --Set DAC0 to 2.5V.

vsense = MB.R(AIN_SENSE,3)    -- AIN1 is vsense 
print(vsense)

local n = 0
local Nmax = 2000
local vset_sp = -7.6      -- setpoint for single plane
local vset_stripe = -8    -- setpoint for stripes

while true do
  if checkInterval(0) then
    PIDmode_sp = MB.R(DIN_PID_sp,0)   -- read in PID status DIO (single plane)
    PIDmode_stripe = MB.R(DIN_PID_stripe,0)
    --PIDmode = 1
    vsense = MB.R(AIN_SENSE,3)  -- read in sense voltage
    vff = MB.R(AIN_FF,3)        -- read in feedforward voltage
    vout = 2.5 + vff            -- default output is halfwy plus feedforward
    if PIDmode_sp == 1 and PIDmode_stripe == 0 then -- if doing single plane
      PIDmode = 1
      err0 = vset_sp - vsense -- calculate error
      -- Calculate new output using digital PI values
      u0 = u1 + 0.5*(ki*Ts+2*kp)*err0 + 0.5*(ki*Ts-2*kp)*err1 
      u1 = u0       -- current output becomes previous output      
      err1 = err0   -- current error becomes previous error
    elseif PIDmode_sp == 0 and PIDmode_stripe == 1 then -- if doing stripe
      PIDmode = 2
      err0 = vset_stripe - vsense -- calculate error
      -- Calculate new output using digital PI values
      u0 = u1 + 0.5*(ki*Ts+2*kp)*err0 + 0.5*(ki*Ts-2*kp)*err1 
      u1 = u0       -- current output becomes previous output      
      err1 = err0   -- current error becomes previous error
    else -- if the PID is disabled or both channels are high (bug)
      PIDmode = 0
      u0 = 0        -- Fix the PID output level at 0
      err0 = 0      -- reset the current error
      err1 = 0      -- reset the previous error
    end
    vout = vout + u0 -- total output is sum of feedforward and PID
    -- Do not let the labjack DAC outputs exceed [0V,5V]
    if vout>5 then
      vout = 5
    end
    if vout<0 then
      vout = 0
    end
    -- Write the values to the local RAM which may be read externally
    MB.W(RAM_SENSE,3,vsense)     
    MB.W(RAM_PID,3,PIDmode)      
    MB.W(RAM_OUT,3,vout)
    -- Write the DAC output 
    MB.W(DAC_OUT,3,vout) 
    end
end