PROGRAM LatchLogic
VAR
    PB1      AT %QX100.0 : BOOL;   (* Start button  - Modbus coil 801 *)
    PB2      AT %QX100.1 : BOOL;   (* Stop button   - Modbus coil 802 *)
    PUMP     AT %QX0.0   : BOOL;   (* Pump output   - Modbus coil 1   *)
    TANK_FULL AT %QX100.2 : BOOL;  (* Tank Full Status - Modbus coil 803 *)
    Tank_Level AT %QW0 : INT;      (* Tank level 0-100% - Modbus holding reg 40001 *)
END_VAR

(* Start/Stop latch with Tank Full condition:
   - Press PB1 once to start (latches ON) unless Tank_Full is true
   - Press PB2 to stop (unlatch)
   - If Tank_Full becomes TRUE, the pump must stop immediately
   - The pump cannot start if Tank_Full is TRUE *)

(* Normal start logic - only start if tank not full *)
IF PB1 AND NOT TANK_FULL THEN
    PUMP := TRUE;
END_IF;

(* Normal stop logic - should always work *)
IF PB2 THEN
    PUMP := FALSE;
END_IF;

(* Emergency override - tank full safety *)
IF TANK_FULL THEN
    PUMP := FALSE;
END_IF;

END_PROGRAM

CONFIGURATION Config0
   RESOURCE Res0 ON PLC
      TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
      PROGRAM instance0 WITH task0 : LatchLogic;
   END_RESOURCE
END_CONFIGURATION