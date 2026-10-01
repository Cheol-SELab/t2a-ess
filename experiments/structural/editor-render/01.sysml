private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// MUM-T attack maneuver ground truth (relation closure) scenario
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
#Performer
part '2nd Platoon' : Performer;

#Function
action 'MUM-T-based attack maneuver and electronic warfare response' {
    #Function
    action 'Preparation and normal communication maneuver' {
        #Function
        action 'TDSS self-diagnosis and normal communication confirmation';
        #Function
        action 'Sequential reconnaissance drone launch and surveillance deployment';

        allocate 'TDSS self-diagnosis and normal communication confirmation' to 'TDSS';
        allocate 'Sequential reconnaissance drone launch and surveillance deployment' to 'Three reconnaissance drones';

        succession first start then 'TDSS self-diagnosis and normal communication confirmation';
        succession first 'TDSS self-diagnosis and normal communication confirmation' then 'Sequential reconnaissance drone launch and surveillance deployment';
        succession first 'Sequential reconnaissance drone launch and surveillance deployment' then done;
    }
    #Function
    action 'Enemy observation post and FPV threat detection response' {
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
        action 'FPV evasive maneuver';

        fork 'New Start Concurrency_1';
        join 'New End Concurrency_1';

        allocate 'Detect suspected enemy observation post heat source' to 'Drone 1';
        allocate 'Decide right bypass maneuver' to 'Company commander';
        allocate 'Provide FPV threat alert' to 'TDSS';
        allocate 'Order dispersed maneuver and air-defense watch' to 'Company commander';
        allocate 'FPV evasive maneuver' to 'Subordinate platoons';

        succession first start then 'New Start Concurrency_1';
        succession first 'Detect suspected enemy observation post heat source' then 'Decide right bypass maneuver';
        succession first 'Provide FPV threat alert' then 'Order dispersed maneuver and air-defense watch';
        succession first 'Decide right bypass maneuver' then 'New End Concurrency_1';
        succession first 'Order dispersed maneuver and air-defense watch' then 'New End Concurrency_1';
        succession first 'FPV evasive maneuver' then 'New End Concurrency_1';
        succession first 'New Start Concurrency_1' then 'Detect suspected enemy observation post heat source';
        succession first 'New Start Concurrency_1' then 'Provide FPV threat alert';
        succession first 'New Start Concurrency_1' then 'FPV evasive maneuver';
        succession first 'New End Concurrency_1' then done;
    }
    #Function
    action 'Electronic warfare jamming and communication degradation response' {
        #Function
        action 'Drone switch to Edge AI analysis mode' {
            in item 'Drone video stream' : ItemInputEdge;
            out item 'Summary track data' : ItemOutputEdge;
        }
        #Function
        action 'Activate local sensor-based survival loop';
        #Function
        action 'Transmit drone emergency broadcast' {
            out item 'Drone emergency broadcast message' : ItemOutputEdge;
        }
        #Function
        action 'Smoke screen deployment and evasive maneuver after ATGM alert';

        fork 'New Start Concurrency_2';
        join 'New End Concurrency_2';

        attribute 'While the communication blackout state persists' : ScalarValues::Boolean;  // control: loop

        allocate 'Drone switch to Edge AI analysis mode' to 'Three reconnaissance drones';
        allocate 'Activate local sensor-based survival loop' to 'TDSS';
        allocate 'Transmit drone emergency broadcast' to 'Three reconnaissance drones';
        allocate 'Smoke screen deployment and evasive maneuver after ATGM alert' to '2nd Platoon';

        succession first start then 'New Start Concurrency_2';
        succession first 'Activate local sensor-based survival loop' if 'While the communication blackout state persists' == true then 'Transmit drone emergency broadcast';
        succession first 'Transmit drone emergency broadcast' then 'Smoke screen deployment and evasive maneuver after ATGM alert';
        succession first 'Drone switch to Edge AI analysis mode' then 'New End Concurrency_2';
        succession first 'Smoke screen deployment and evasive maneuver after ATGM alert' then 'New End Concurrency_2';
        succession first 'New Start Concurrency_2' then 'Drone switch to Edge AI analysis mode';
        succession first 'New Start Concurrency_2' then 'Activate local sensor-based survival loop';
        succession first 'New End Concurrency_2' then done;
    }
    #Function
    action 'Communication recovery and attack resumption' {
        #Function
        action 'SA resynchronization' {
            in item 'Summary track data' : ItemInputEdge;
            out item 'Company SA summary information' : ItemOutputEdge;
        }
        #Function
        action 'Comprehensive report on the blackout period' {
            out item 'Comprehensive report on the blackout period' : ItemOutputEdge;
        }
        #Function
        action 'Resume attack maneuver';

        attribute 'Limited mode after link stability confirmation' : ScalarValues::Boolean;  // control: guarded_sequence

        allocate 'SA resynchronization' to 'TDSS';
        allocate 'Comprehensive report on the blackout period' to 'Company commander';
        allocate 'Resume attack maneuver' to 'Subordinate platoons';

        succession first start then 'SA resynchronization';
        succession first 'SA resynchronization' then 'Comprehensive report on the blackout period';
        succession first 'Comprehensive report on the blackout period' if 'Limited mode after link stability confirmation' == true then 'Resume attack maneuver';
        succession first 'Resume attack maneuver' then done;
    }

    item 'Drone video stream';
    item 'Summary track data';
    item 'Company SA summary information';
    item 'FPV threat alert';
    item 'Drone emergency broadcast message';
    item 'Comprehensive report on the blackout period';

    succession first start then 'Preparation and normal communication maneuver';
    succession first 'Preparation and normal communication maneuver' then 'Enemy observation post and FPV threat detection response';
    succession first 'Enemy observation post and FPV threat detection response' then 'Electronic warfare jamming and communication degradation response';
    succession first 'Electronic warfare jamming and communication degradation response' then 'Communication recovery and attack resumption';
    succession first 'Communication recovery and attack resumption' then done;

    flow from 'Electronic warfare jamming and communication degradation response'.'Drone switch to Edge AI analysis mode'.'Summary track data' to 'Communication recovery and attack resumption'.'SA resynchronization'.'Summary track data';
}
