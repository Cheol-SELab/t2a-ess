private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// MUM-T attack maneuver unstructured test text T2A-ESS extraction result
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

#Performer
part 'Company commander' : Performer;
#Performer
part 'TDSS' : Performer;
#Performer
part 'Three reconnaissance drones' : Performer;
#Performer
part 'Drone 1' : Performer;
#Performer
part 'Drone 2' : Performer;
#Performer
part 'Drone 3' : Performer;
#Performer
part 'Subordinate platoons' : Performer;
#Performer
part 'Battalion server' : Performer;
#Performer
part 'Enemy' : Performer;

#Function
action 'MUM-T-based attack maneuver and electronic warfare response' {
    #Function
    action 'TDSS self-diagnosis and normal communication confirmation';
    #Function
    action 'Sequential reconnaissance drone launch and surveillance deployment';
    #Function
    action 'Detect suspected enemy observation post heat source';
    #Function
    action 'Decide right bypass maneuver';
    #Function
    action 'Provide FPV threat alert' {
        out item 'FPV threat alert' : ItemOutputEdge;
    }
    #Function
    action 'Order dispersed maneuver and air-defense watch';
    #Function
    action 'Drone switch to Edge AI analysis mode' {
        out item 'Summary track data' : ItemOutputEdge;
    }
    #Function
    action 'FPV evasive maneuver';
    #Function
    action 'Activate local sensor-based survival loop';
    #Function
    action 'Transmit drone emergency broadcast' {
        out item 'Drone emergency broadcast message' : ItemOutputEdge;
    }
    #Function
    action 'Smoke screen deployment and evasive maneuver after ATGM alert';
    #Function
    action 'SA resynchronization';
    #Function
    action 'Comprehensive report on the blackout period';
    #Function
    action 'Resume attack maneuver';

    fork 'New Start Concurrency_1';
    join 'New End Concurrency_1';

    allocate 'TDSS self-diagnosis and normal communication confirmation' to 'TDSS';
    allocate 'Sequential reconnaissance drone launch and surveillance deployment' to 'Three reconnaissance drones';

    succession first start then 'New Start Concurrency_1';
    succession first 'Provide FPV threat alert' then 'Order dispersed maneuver and air-defense watch';
    succession first 'TDSS self-diagnosis and normal communication confirmation' then 'New End Concurrency_1';
    succession first 'Sequential reconnaissance drone launch and surveillance deployment' then 'New End Concurrency_1';
    succession first 'Detect suspected enemy observation post heat source' then 'New End Concurrency_1';
    succession first 'Decide right bypass maneuver' then 'New End Concurrency_1';
    succession first 'Order dispersed maneuver and air-defense watch' then 'New End Concurrency_1';
    succession first 'Drone switch to Edge AI analysis mode' then 'New End Concurrency_1';
    succession first 'FPV evasive maneuver' then 'New End Concurrency_1';
    succession first 'Activate local sensor-based survival loop' then 'New End Concurrency_1';
    succession first 'Transmit drone emergency broadcast' then 'New End Concurrency_1';
    succession first 'Smoke screen deployment and evasive maneuver after ATGM alert' then 'New End Concurrency_1';
    succession first 'SA resynchronization' then 'New End Concurrency_1';
    succession first 'Comprehensive report on the blackout period' then 'New End Concurrency_1';
    succession first 'Resume attack maneuver' then 'New End Concurrency_1';
    succession first 'New Start Concurrency_1' then 'TDSS self-diagnosis and normal communication confirmation';
    succession first 'New Start Concurrency_1' then 'Sequential reconnaissance drone launch and surveillance deployment';
    succession first 'New Start Concurrency_1' then 'Detect suspected enemy observation post heat source';
    succession first 'New Start Concurrency_1' then 'Decide right bypass maneuver';
    succession first 'New Start Concurrency_1' then 'Provide FPV threat alert';
    succession first 'New Start Concurrency_1' then 'Drone switch to Edge AI analysis mode';
    succession first 'New Start Concurrency_1' then 'FPV evasive maneuver';
    succession first 'New Start Concurrency_1' then 'Activate local sensor-based survival loop';
    succession first 'New Start Concurrency_1' then 'Transmit drone emergency broadcast';
    succession first 'New Start Concurrency_1' then 'Smoke screen deployment and evasive maneuver after ATGM alert';
    succession first 'New Start Concurrency_1' then 'SA resynchronization';
    succession first 'New Start Concurrency_1' then 'Comprehensive report on the blackout period';
    succession first 'New Start Concurrency_1' then 'Resume attack maneuver';
    succession first 'New End Concurrency_1' then done;

    item 'Summary track data';
    item 'FPV threat alert';
    item 'Drone emergency broadcast message';
}
