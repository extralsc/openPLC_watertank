PROGRAM LatchLogic
VAR
    PB1      AT %QX100.0 : BOOL;   (* Start button  - Modbus coil 801 *)
    PB2      AT %QX100.1 : BOOL;   (* Stop button   - Modbus coil 802 *)
    PUMP     AT %QX0.0   : BOOL;   (* Pump output   - Modbus coil 1   *)
    TANK_FULL AT %QX100.2 : BOOL;  (* Tank Full Status - Modbus coil 803 *)
END_VAR

(* Start/Stop latch with Tank Full condition:
   - Press PB1 once to start (latches ON) unless Tank_Full is true
   - Press PB2 to stop (unlatch)
   - If Tank_Full becomes TRUE, the pump must stop immediately
   - The pump cannot start if Tank_Full is TRUE *)

(* Pump Control Logic *)
IF NOT TANK_FULL THEN
    (* Tank is not full, normal start/stop behavior *)
    IF PB1 THEN
        PUMP := TRUE;  (* Start pump *)
    END_IF;

    IF PB2 THEN
        PUMP := FALSE; (* Stop pump *)
    END_IF;
ELSE
    (* Tank is full, stop pump and prevent starting *)
    PUMP := FALSE;  (* Ensure pump is OFF *)
END_IF;

END_PROGRAM

CONFIGURATION Config0
   RESOURCE Res0 ON PLC
      TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
      PROGRAM instance0 WITH task0 : LatchLogic;
   END_RESOURCE
END_CONFIGURATION
