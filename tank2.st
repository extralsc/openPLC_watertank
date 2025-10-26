PROGRAM LatchLogic
VAR
    PB1  AT %QX100.0 : BOOL;   (* Start button  - Modbus coil 801 *)
    PB2  AT %QX100.1 : BOOL;   (* Stop button   - Modbus coil 802 *)
    PUMP AT %QX0.0   : BOOL;   (* Pump output   - Modbus coil 1   *)
END_VAR

(* Start/Stop latch:
   - Press PB1 once to start (latches ON)
   - Press PB2 to stop (unlatch) *)
IF PB1 THEN
    PUMP := TRUE;
END_IF;

IF PB2 THEN
    PUMP := FALSE;
END_IF;
END_PROGRAM

CONFIGURATION Config0
   RESOURCE Res0 ON PLC
      TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
      PROGRAM instance0 WITH task0 : LatchLogic;
   END_RESOURCE
END_CONFIGURATION

