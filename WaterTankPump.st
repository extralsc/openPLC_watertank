(*
WaterTankPump.st
OpenPLC logic for water tank pump control.
*)

PROGRAM WaterTankPump
VAR
    (* HMI / Modbus-facing inputs *)
    PB_Start      AT %IX0.0 : BOOL;   (* Coil 801 from Modbus: momentary start *)
    PB_Stop       AT %IX0.1 : BOOL;   (* Coil 802 from Modbus: momentary stop  *)
    Tank_Full     AT %IX0.3 : BOOL;   (* Coil 803 / digital input: high-high safety *)

    (* Process input *)
    Tank_Level    AT %IW0 : INT;      (* 0..100 (%) analog/Sim level, also mapped to holding reg 40001 *)

    (* Internal state *)
    Pump_Run      : BOOL := FALSE;    (* Latched run request *)

    (* Output *)
    Pump_Motor    AT %QX0.0 : BOOL;   (* Drives the pump starter; also readable as coil 1 *)
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
