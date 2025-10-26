PROGRAM LatchLogic
VAR
    PB1  AT %QX100.0 : BOOL;   (* Start button  - Modbus coil 801 *)
    PB2  AT %QX100.1 : BOOL;   (* Stop button   - Modbus coil 802 *)
    Tank_Full AT %QX100.2 : BOOL;   (* Tank full sensor - Modbus coil 803 *)
    Tank_Level AT %QW0 : INT;     (* Tank level 0-100% - Modbus holding reg 40001 *)
    PUMP AT %QX0.0   : BOOL;   (* Pump output   - Modbus coil 1   *)
    Pump_Run : BOOL;           (* Internal latch state *)
END_VAR

(* Start/Stop latch with safety:
   - Press PB1 once to start (latches ON) - only if tank not full
   - Press PB2 to stop (unlatch)
   - Tank_Full forces pump off (emergency override) *)

(* Normal start logic - only start if tank not full *)
IF PB1 AND NOT Tank_Full THEN
    Pump_Run := TRUE;
END_IF;

(* Normal stop logic *)
IF PB2 THEN
    Pump_Run := FALSE;
END_IF;

(* Emergency override - tank full safety *)
IF Tank_Full THEN
    Pump_Run := FALSE;
END_IF;

(* Drive pump output *)
PUMP := Pump_Run;
END_PROGRAM

CONFIGURATION Config0
   RESOURCE Res0 ON PLC
      TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
      PROGRAM instance0 WITH task0 : LatchLogic;
   END_RESOURCE
END_CONFIGURATION

