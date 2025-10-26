PROGRAM WaterTankPump
VAR
    PB_Start  AT %QX100.0 : BOOL;   (* Start button - Modbus coil 801 *)
    PB_Stop   AT %QX100.1 : BOOL;   (* Stop button - Modbus coil 802 *)
    Tank_Full AT %QX100.3 : BOOL;   (* Tank full sensor - Modbus coil 803 *)
    Tank_Level AT %QW100 : INT;     (* Tank level - Modbus holding reg 40001 *)
    Pump_Motor AT %QX0.0 : BOOL;    (* Pump output - Modbus coil 1 *)
    Pump_Run : BOOL;                (* Internal latch state *)
END_VAR

(* Normal latch logic: start/stop *)
IF PB_Start AND NOT Tank_Full THEN
    Pump_Run := TRUE;
END_IF;

IF PB_Stop THEN
    Pump_Run := FALSE;
END_IF;

(* Emergency override *)
IF Tank_Full THEN
    Pump_Run := FALSE;
END_IF;

(* Drive motor output *)
Pump_Motor := Pump_Run;

END_PROGRAM

CONFIGURATION Config0
   RESOURCE Res0 ON PLC
      TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
      PROGRAM instance0 WITH task0 : WaterTankPump;
   END_RESOURCE
END_CONFIGURATION