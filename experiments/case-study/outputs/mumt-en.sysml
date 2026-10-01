private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// MUM-T attack operation under EW
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

#Performer
part 'Company commander' : Performer;
#Performer
part 'TDSS' : Performer;
#Performer
part 'Recon drone team' : Performer;
#Performer
part 'Drone 1' : Performer;
#Performer
part 'Drone 2' : Performer;
#Performer
part 'Drone 3' : Performer;
#Performer
part 'Platoons' : Performer;
#Performer
part 'Battalion server' : Performer;
#Performer
part 'Enemy' : Performer;
#Performer
part 'Platoon 2' : Performer;

#Function
action 'MUM-T attack operation under EW' {
    #Function
    action 'E1 Preparation under normal comms' {
        #Function
        action 'Run TDSS self-test and check comms';
        #Function
        action 'Launch drones and deploy for surveillance';

        allocate 'Run TDSS self-test and check comms' to 'TDSS';
        allocate 'Launch drones and deploy for surveillance' to 'Recon drone team';

        succession first start then 'Run TDSS self-test and check comms';
        succession first 'Run TDSS self-test and check comms' then 'Launch drones and deploy for surveillance';
        succession first 'Launch drones and deploy for surveillance' then done;
    }
    #Function
    action 'E2 Observation post and FPV threat' {
        #Function
        action 'Detect heat source of enemy OP';
        #Function
        action 'Decide right-flank detour';
        #Function
        action 'Issue FPV threat alert' {
            out item 'FPV threat alert' : ItemOutputEdge;
        }
        #Function
        action 'Order dispersion and air watch';
        #Function
        action 'Evade FPV';

        fork 'New Start Concurrency_1';
        join 'New End Concurrency_1';

        allocate 'Detect heat source of enemy OP' to 'Drone 1';
        allocate 'Decide right-flank detour' to 'Company commander';
        allocate 'Issue FPV threat alert' to 'TDSS';
        allocate 'Order dispersion and air watch' to 'Company commander';
        allocate 'Evade FPV' to 'Platoons';

        succession first start then 'New Start Concurrency_1';
        succession first 'Detect heat source of enemy OP' then 'Decide right-flank detour';
        succession first 'Issue FPV threat alert' then 'Order dispersion and air watch';
        succession first 'Decide right-flank detour' then 'New End Concurrency_1';
        succession first 'Order dispersion and air watch' then 'New End Concurrency_1';
        succession first 'Evade FPV' then 'New End Concurrency_1';
        succession first 'New Start Concurrency_1' then 'Detect heat source of enemy OP';
        succession first 'New Start Concurrency_1' then 'Issue FPV threat alert';
        succession first 'New Start Concurrency_1' then 'Evade FPV';
        succession first 'New End Concurrency_1' then done;
    }
    #Function
    action 'E3 EW jamming and comms degradation' {
        #Function
        action 'Switch drones to edge-AI analysis' {
            in item 'Drone video stream' : ItemInputEdge;
            out item 'Summary track data' : ItemOutputEdge;
        }
        #Function
        action 'Activate local-sensor survival loop';
        #Function
        action 'Transmit drone emergency broadcast' {
            out item 'Emergency broadcast message' : ItemOutputEdge;
        }
        #Function
        action 'Deploy smoke and evade after ATGM alert';

        fork 'New Start Concurrency_2';
        join 'New End Concurrency_2';

        attribute 'while comms remain disconnected' : ScalarValues::Boolean;  // control: loop

        allocate 'Switch drones to edge-AI analysis' to 'Recon drone team';
        allocate 'Activate local-sensor survival loop' to 'TDSS';
        allocate 'Transmit drone emergency broadcast' to 'Recon drone team';
        allocate 'Deploy smoke and evade after ATGM alert' to 'Platoon 2';

        succession first start then 'New Start Concurrency_2';
        succession first 'Activate local-sensor survival loop' if 'while comms remain disconnected' == true then 'Transmit drone emergency broadcast';
        succession first 'Transmit drone emergency broadcast' then 'Deploy smoke and evade after ATGM alert';
        succession first 'Switch drones to edge-AI analysis' then 'New End Concurrency_2';
        succession first 'Deploy smoke and evade after ATGM alert' then 'New End Concurrency_2';
        succession first 'New Start Concurrency_2' then 'Switch drones to edge-AI analysis';
        succession first 'New Start Concurrency_2' then 'Activate local-sensor survival loop';
        succession first 'New End Concurrency_2' then done;
    }
    #Function
    action 'E4 Comms recovery and attack resumption' {
        #Function
        action 'Resynchronize SA' {
            in item 'Summary track data' : ItemInputEdge;
            out item 'Company SA summary' : ItemOutputEdge;
        }
        #Function
        action 'Report disconnection period' {
            out item 'Disconnection-period report' : ItemOutputEdge;
        }
        #Function
        action 'Resume attack maneuver';

        attribute 'limited mode after link is stable' : ScalarValues::Boolean;  // control: guarded_sequence

        allocate 'Resynchronize SA' to 'TDSS';
        allocate 'Report disconnection period' to 'Company commander';
        allocate 'Resume attack maneuver' to 'Platoons';

        succession first start then 'Resynchronize SA';
        succession first 'Resynchronize SA' then 'Report disconnection period';
        succession first 'Report disconnection period' if 'limited mode after link is stable' == true then 'Resume attack maneuver';
        succession first 'Resume attack maneuver' then done;
    }

    item 'Drone video stream';
    item 'Summary track data';
    item 'Company SA summary';
    item 'FPV threat alert';
    item 'Emergency broadcast message';
    item 'Disconnection-period report';

    succession first start then 'E1 Preparation under normal comms';
    succession first 'E1 Preparation under normal comms' then 'E2 Observation post and FPV threat';
    succession first 'E2 Observation post and FPV threat' then 'E3 EW jamming and comms degradation';
    succession first 'E3 EW jamming and comms degradation' then 'E4 Comms recovery and attack resumption';
    succession first 'E4 Comms recovery and attack resumption' then done;

    flow from 'E3 EW jamming and comms degradation'.'Switch drones to edge-AI analysis'.'Summary track data' to 'E4 Comms recovery and attack resumption'.'Resynchronize SA'.'Summary track data';
}
